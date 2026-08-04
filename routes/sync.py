"""
数据同步路由 - 后台同步 & 操作接口
"""
import asyncio
import json
import logging
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
logger = logging.getLogger(__name__)

# 浏览器会话（仅用于操作类接口，同步完成后不保留）
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
    try:
        from config import JUSHUITAN_URL, BROWSER
    except ImportError:
        raise RuntimeError('缺少 config.py 配置文件，请参照 config.example.py 创建')

    account_name = account.get('name', account['username'])
    logger.info(f"\n{'=' * 50}")
    logger.info(f"开始同步账号: {account_name}")
    logger.info(f"{'=' * 50}")

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
            errors.append(f"{account_name}: 登录失败")
            return 0, errors

        set_browser_session(login)

        if sync_type in ('orders', 'full'):
            scraper = OrderScraper(login)
            last_sync = SyncStateModel.get_last_sync(account_name, 'orders')
            if last_sync:
                start_date = last_sync[:10]
                logger.info(f"[{account_name}] 增量同步订单: {start_date} ~ 今天")
            else:
                start_date = '2026-06-01'
                logger.info(f"[{account_name}] 首次同步订单: {start_date} ~ 今天")

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

        logger.info(f"[{account_name}] 同步完成: {count} 条记录")
        return count, errors
    except Exception as e:
        errors.append(f"{account_name}: {str(e)}")
        logger.error(f"[{account_name}] 同步异常: {e}")
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
    """异步执行同步 - 单次调用"""
    try:
        from config import ACCOUNTS, MEMORY
    except ImportError:
        raise RuntimeError('缺少 config.py 配置文件，请参照 config.example.py 创建')

    # 低内存模式检查
    if MEMORY.get('low_memory_mode', True):
        try:
            import psutil
            mem = psutil.virtual_memory()
            avail_mb = mem.available / 1024 / 1024
            if avail_mb < 300:
                return {'success': False, 'message': f'内存不足 (剩余 {int(avail_mb)}MB)，请释放内存后重试'}
        except ImportError:
            pass

    # 限制并发数，避免内存溢出
    semaphore = asyncio.Semaphore(MEMORY.get('max_concurrent_accounts', 1))

    async def _limited_sync(account):
        async with semaphore:
            return await _sync_account_once(account, sync_type)

    log_id = SyncLogModel.create(sync_type)
    total_count = 0
    all_errors = []

    try:
        tasks = [_limited_sync(acc) for acc in ACCOUNTS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                all_errors.append(str(result))
            elif isinstance(result, tuple):
                total_count += result[0]
                all_errors.extend(result[1])

        if all_errors:
            SyncLogModel.update(log_id, 'partial', records_count=total_count, error_message='; '.join(all_errors[:5]))
            msg = f'同步完成 {len(ACCOUNTS)} 个账号，共 {total_count} 条，{len(all_errors)} 个错误'
            return {'success': True, 'message': msg, 'count': total_count, 'errors': all_errors}
        else:
            SyncLogModel.update(log_id, 'success', records_count=total_count, error_message='')
            msg = f'同步完成 {len(ACCOUNTS)} 个账号，共 {total_count} 条'
            return {'success': True, 'message': msg, 'count': total_count}

    except Exception as e:
        SyncLogModel.update(log_id, 'failed', error_message=str(e))
        return {'success': False, 'message': f'同步失败: {str(e)}'}


def run_sync_async(sync_type, config):
    """在独立事件循环中运行同步"""
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

    try:
        from config import ACCOUNTS, JUSHUITAN_URL, BROWSER
    except ImportError:
        return jsonify({'success': False, 'message': '缺少 config.py 配置文件，请参照 config.example.py 创建'})
    if not ACCOUNTS:
        return jsonify({'success': False, 'message': '未配置账号，请先添加聚水潭账号'})

    if _sync_thread and _sync_thread.is_alive():
        return jsonify({'success': False, 'message': '同步任务正在运行中，请稍后再试'})

    def _background_sync():
        run_sync_async(sync_type, {'accounts': ACCOUNTS, 'url': JUSHUITAN_URL, 'browser': BROWSER})

    _sync_thread = threading.Thread(target=_background_sync, daemon=True)
    _sync_thread.start()
    return jsonify({'success': True, 'message': '同步任务已启动，请在日志中查看进度'})


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


# ---- 操作类 API ----

def _run_browser_action(action_coro):
    """在独立事件循环中运行浏览器操作"""
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
        return jsonify({'success': False, 'message': '请提供售后单号'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '浏览器未登录，请先执行同步'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.approve_after_sale(after_sale_id, remark))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '操作返回异常'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {e}'})


@sync_bp.route('/api/action/reject-after-sale', methods=['POST'])
def api_reject_after_sale():
    data = request.get_json() or {}
    after_sale_id = data.get('after_sale_id', '')
    reason = data.get('reason', '')

    if not after_sale_id:
        return jsonify({'success': False, 'message': '请提供售后单号'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '浏览器未登录，请先执行同步'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.reject_after_sale(after_sale_id, reason))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '操作返回异常'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {e}'})


@sync_bp.route('/api/action/update-remark', methods=['POST'])
def api_update_remark():
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    remark = data.get('remark', '')

    if not order_id:
        return jsonify({'success': False, 'message': '请提供订单号'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '浏览器未登录，请先执行同步'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.update_order_remark(order_id, remark))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '操作返回异常'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {e}'})


@sync_bp.route('/api/action/ship-order', methods=['POST'])
def api_ship_order():
    data = request.get_json() or {}
    order_id = data.get('order_id', '')
    logistics = data.get('logistics_company', '')
    tracking = data.get('tracking_number', '')

    if not order_id or not logistics or not tracking:
        return jsonify({'success': False, 'message': '请填写完整的发货信息'})

    session = get_browser_session()
    if not session:
        return jsonify({'success': False, 'message': '浏览器未登录，请先执行同步'})

    sync = JushuitanSync(session)
    try:
        result = _run_browser_action(sync.ship_order(order_id, logistics, tracking))
        if not isinstance(result, dict):
            result = {'success': False, 'message': '操作返回异常'}
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': f'操作失败: {e}'})