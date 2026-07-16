"""
?????? - ???????? & ????
"""
import asyncio
import json
import threading
import time
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime

_sync_thread = None
from models.database import (
    OrderModel, AfterSalesModel, DailyStatsModel,
    SyncLogModel, SyncStateModel, get_connection
)
from browser.login import JushuitanLogin
from browser.orders import OrderScraper
from browser.after_sales import AfterSalesScraper
from browser.sync import JushuitanSync

sync_bp = Blueprint('sync', __name__)

# ??????
_session = None
_session_lock = threading.Lock()


def get_browser_session():
    global _session
    with _session_lock:
        return _session


def set_browser_session(session):
    global _session
    with _session_lock:
        _session = session


def _run_with_retries(func, retries=1, backoff=2):
    """Run a synchronous callable with bounded retries and backoff."""
    last_exc = None
    for attempt in range(1 + max(retries, 0)):
        try:
            return func()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (attempt + 1))
    raise last_exc


async def _sync_account_once(account, sync_type):
    """Sync one account once and return (count, errors)."""
    from config import JUSHUITAN_URL, BROWSER

    account_name = account.get('name', account['username'])
    print("\n" + "=" * 50)
    print(f"????: {account_name}")
    print("=" * 50)

    login = None
    count = 0
    errors = []

    try:
        login = JushuitanLogin({
            'url': JUSHUITAN_URL,
            'username': account['username'],
            'password': account['password'],
            'name': account_name,
        })
        await login.start(
            headless=BROWSER.get('headless', True),
            slow_mo=BROWSER.get('slow_mo', 100),
        )

        logged_in = await login.is_logged_in()
        if not logged_in:
            logged_in = await login.login()

        if not logged_in:
            errors.append(f"{account_name}: ????")
            return 0, errors

        set_browser_session(login)

        if sync_type in ('orders', 'full'):
            scraper = OrderScraper(login)
            last_sync = SyncStateModel.get_last_sync(account_name, 'orders')
            if last_sync:
                start_date = last_sync[:10]
                print(f"[{account_name}] ??????: {start_date} ~ ??")
            else:
                start_date = '2026-06-01'
                print(f"[{account_name}] ??????: {start_date} ~ ??")

            orders = await scraper.fetch_orders(
                start_date=start_date,
                end_date=datetime.now().strftime('%Y-%m-%d')
            )
            for order in orders:
                oid = order.get('order_id') or order.get('external_id', '')
                if oid:
                    order['order_id'] = oid
                    OrderModel.upsert(order)
                    count += 1
            SyncStateModel.update_sync(account_name, 'orders', count)

        if sync_type in ('after_sales', 'full'):
            scraper = AfterSalesScraper(login)
            as_data = await scraper.fetch_after_sales()
            if isinstance(as_data, dict):
                as_list = as_data.get('list', [])
                for item in as_list:
                    if isinstance(item, dict):
                        aid = str(item.get('afterSaleOrderNo') or item.get('asId') or item.get('id') or '')
                        if aid:
                            goods = item.get('afterSaleOrderGoodsVO') or {}
                            normalized = {
                                'after_sale_id': aid,
                                'order_id': str(item.get('orderNo') or item.get('orderId') or ''),
                                'external_id': str(item.get('soId') or item.get('outerAsId') or ''),
                                'shop_id': str(item.get('shopId') or ''),
                                'shop_name': str(item.get('shopName') or ''),
                                'type': str(item.get('afterType') or item.get('type') or ''),
                                'status': str(item.get('orderStatus') or item.get('drpProcessStatus') or item.get('status') or ''),
                                'reason': str(item.get('reason') or ''),
                                'amount': float(item.get('refundAmount') or item.get('amount') or 0),
                                'quantity': int(goods.get('refundTotalCount') or item.get('quantity') or 0),
                                'created_at': str(item.get('applicationTime') or item.get('created') or ''),
                                'processed_at': str(item.get('dealTime') or ''),
                                'raw_data': json.dumps(item, ensure_ascii=False),
                                'synced_at': datetime.now().isoformat(),
                            }
                            AfterSalesModel.upsert(normalized)
                            count += 1
            SyncStateModel.update_sync(account_name, 'after_sales', count)

        print(f"[{account_name}] ????: {count} ???")
        return count, errors
    except Exception as e:
        errors.append(f"{account_name}: {str(e)}")
        print(f"[{account_name}] ????: {e}")
        return count, errors
    finally:
        try:
            if login is not None:
                await login.close()
                import gc
                gc.collect()
        except Exception:
            pass


async def _run_sync(sync_type, config):
    """???????? - ?????"""
    from config import ACCOUNTS, MEMORY

    # ????
    if MEMORY.get('low_memory_mode', True):
        try:
            import psutil
            avail_mb = psutil.virtual_memory().available / 1024 / 1024
            if avail_mb < 300:
                return {'success': False, 'message': f'???? (?? {int(avail_mb)}MB)??????'}
        except ImportError:
            pass

    log_id = SyncLogModel.create(sync_type)
    total_count = 0
    errors = []

    try:
        for i, account in enumerate(ACCOUNTS):
            # ???? 5 ???????????????
            if i > 0:
                await asyncio.sleep(5)
                if MEMORY.get('auto_gc', True):
                    import gc
                    gc.collect()
            account_name = account.get('name', account['username'])
            try:
                count, account_errors = await _sync_account_once(account, sync_type)
                total_count += count
                errors.extend(account_errors)
            except Exception as e:
                errors.append(f"{account_name}: {str(e)}")
                print(f"[{account_name}] ????: {e}")

        # ??????
        try:
            conn = get_connection()
            try:
                today = datetime.now().strftime('%Y-%m-%d')
                row = conn.execute("""
                    SELECT
                        COUNT(*) as total_orders,
                        COALESCE(SUM(pay_amount), 0) as total_amount,
                        COALESCE(SUM(purchase_cost), 0) as total_cost,
                        COALESCE(SUM(profit), 0) as total_profit,
                        COUNT(CASE WHEN status = 'WaitCheck' THEN 1 END) as new_orders,
                        COUNT(CASE WHEN status IN ('Shipped', 'Sent') THEN 1 END) as shipped_orders,
                        COUNT(CASE WHEN status IN ('Finished', 'Completed') THEN 1 END) as completed_orders,
                        COUNT(CASE WHEN status = 'Cancelled' THEN 1 END) as cancelled_orders
                    FROM orders WHERE created_at LIKE ?
                """, (f"{today}%",)).fetchone()
                stats = dict(row)
            finally:
                conn.close()

            as_stats = AfterSalesModel.get_stats_for_date(today)
            DailyStatsModel.upsert(today, {
                'total_orders': stats.get('total_orders', 0),
                'total_amount': stats.get('total_amount', 0),
                'total_cost': stats.get('total_cost', 0),
                'total_profit': stats.get('total_profit', 0),
                'new_orders': stats.get('new_orders', 0),
                'shipped_orders': stats.get('shipped_orders', 0),
                'completed_orders': stats.get('completed_orders', 0),
                'cancelled_orders': stats.get('cancelled_orders', 0),
                'total_after_sales': 0,
                'refund_amount': 0,
            })

        except Exception as e:
            errors.append(f"??????: {str(e)}")

        error_msg = '; '.join(errors) if errors else ''
        if errors:
            SyncLogModel.update(log_id, 'partial', records_count=total_count, error_message=error_msg)
            msg = f'?????? {len(ACCOUNTS)} ????{total_count} ????{len(errors)} ?????'
            return {'success': False, 'message': msg, 'count': total_count}
        else:
            SyncLogModel.update(log_id, 'success', records_count=total_count, error_message='')
            msg = f'?????? {len(ACCOUNTS)} ????{total_count} ???'
            return {'success': True, 'message': msg, 'count': total_count}

    except Exception as e:
        SyncLogModel.update(log_id, 'failed', error_message=str(e))
        return {'success': False, 'message': f'????: {str(e)}'}


def run_sync_async(sync_type, config):
    """?????????????"""
    def _call():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run_sync(sync_type, config))
        finally:
            loop.close()
    return _run_with_retries(_call, retries=1, backoff=2)


@sync_bp.route('/sync')
def sync_page():
    logs = SyncLogModel.get_recent(20)
    sync_states = SyncStateModel.get_all()
    return render_template('sync.html', logs=logs, sync_states=sync_states)


@sync_bp.route('/api/sync', methods=['POST'])
def api_sync():
    global _sync_thread
    data = request.get_json() or {}
    sync_type = data.get('type', 'full')

    from config import ACCOUNTS, JUSHUITAN_URL, BROWSER
    if not ACCOUNTS:
        return jsonify({'success': False, 'message': '?????????????'})

    if _sync_thread and _sync_thread.is_alive():
        return jsonify({'success': False, 'message': '??????????????'})

    def _background_sync():
        run_sync_async(sync_type, {'accounts': ACCOUNTS, 'url': JUSHUITAN_URL, 'browser': BROWSER})

    _sync_thread = threading.Thread(target=_background_sync, daemon=True)
    _sync_thread.start()
    return jsonify({'success': True, 'message': '???????????????????'})


@sync_bp.route('/api/sync/logs')
def api_sync_logs():
    logs = SyncLogModel.get_recent(20)
    return jsonify({'data': logs})


@sync_bp.route('/api/sync/status')
def api_sync_status():
    global _sync_thread
    session = get_browser_session()
    running = _sync_thread is not None and _sync_thread.is_alive()
    from models.database import SyncStateModel
    states = SyncStateModel.get_all()
    last_sync = None
    for s in (states or []):
        lo = s.get('last_order_sync') or ''
        la = s.get('last_after_sale_sync') or ''
        if lo and (not last_sync or lo > last_sync):
            last_sync = lo
    return jsonify({
        'active': session is not None,
        'running': running,
        'last_sync': last_sync[:16] if last_sync else None,
    })


# ---- ???? API ----

def _run_browser_action(action_coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(action_coro)
    finally:
        loop.close()


@sync_bp.route('/api/action/approve-after-sale', methods=['POST'])
def api_approve_after_sale():
    data = request.get_json() or {}
    after_sale_id = data.get('after_sale_id', '')
    remark = data.get('remark', '')

    if not after_sale_id:
        return jsonify({'success': False, 'message': '??????'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '??????????'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.approve_after_sale(after_sale_id, remark))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '??????'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'????: {e}'})


@sync_bp.route('/api/action/reject-after-sale', methods=['POST'])
def api_reject_after_sale():
    data = request.get_json() or {}
    after_sale_id = data.get('after_sale_id', '')
    reason = data.get('reason', '')

    if not after_sale_id:
        return jsonify({'success': False, 'message': '??????'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '??????????'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.reject_after_sale(after_sale_id, reason))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '??????'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'????: {e}'})


@sync_bp.route('/api/action/update-remark', methods=['POST'])
def api_update_remark():
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    remark = data.get('remark', '')

    if not order_id:
        return jsonify({'success': False, 'message': '?????'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '??????????'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.update_order_remark(order_id, remark))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '??????'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'????: {e}'})


@sync_bp.route('/api/action/ship-order', methods=['POST'])
def api_ship_order():
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    logistics = data.get('logistics_company', '')
    tracking = data.get('tracking_number', '')

    if not order_id or not logistics or not tracking:
        return jsonify({'success': False, 'message': '??????'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '??????????'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.ship_order(order_id, logistics, tracking))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '??????'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'????: {e}'})
