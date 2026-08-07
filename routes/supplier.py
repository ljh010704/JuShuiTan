"""
供应商分析路由
"""
import asyncio
import json
import logging
from flask import Blueprint, render_template, jsonify, request
from models.database import get_connection

supplier_bp = Blueprint('supplier', __name__)
logger = logging.getLogger(__name__)


@supplier_bp.route('/suppliers')
def suppliers_page():
    return render_template('suppliers.html')


@supplier_bp.route('/api/suppliers')
def api_suppliers():
    """供应商出单统计 + 热销商品（分销订单口径）"""
    conn = get_connection()
    try:
        dist_filter = """order_type LIKE '%分销Plus%'
              AND order_type NOT LIKE '%供销%'
              AND order_type NOT LIKE '%自发%'
              AND status IN ('Sent', 'WaitOuterSent')"""

        rows = conn.execute(f"""
            SELECT
                supplier_name,
                MAX(supplier_co_id) as co_id,
                COUNT(*) as order_count,
                COALESCE(SUM(pay_amount), 0) as total_amount,
                COALESCE(SUM(purchase_cost), 0) as total_cost,
                COALESCE(SUM(pay_amount - purchase_cost), 0) as total_profit,
                MIN(created_at) as first_order,
                MAX(created_at) as last_order
            FROM orders
            WHERE supplier_name != '' AND {dist_filter}
            GROUP BY supplier_name
            ORDER BY order_count DESC
        """).fetchall()

        # 每个供应商的售后数（按 order_id 关联）
        after_rows = conn.execute("""
            SELECT o.supplier_name, COUNT(*) as cnt
            FROM after_sales a
            JOIN orders o ON a.order_id = o.order_id
            WHERE o.supplier_name != ''
            GROUP BY o.supplier_name
        """).fetchall()
        after_map = {r['supplier_name']: r['cnt'] for r in after_rows}

        # 每个供应商的热销商品（解析 raw_data 里的商品列表）
        goods_rows = conn.execute(f"""
            SELECT supplier_name, raw_data FROM orders
            WHERE supplier_name != '' AND {dist_filter}
              AND raw_data IS NOT NULL AND raw_data != ''
        """).fetchall()

        goods_map = {}
        for r in goods_rows:
            sname = r['supplier_name']
            try:
                raw = json.loads(r['raw_data'])
            except (json.JSONDecodeError, TypeError):
                continue
            for g in (raw.get('disInnerOrderGoodsViewList') or []):
                if not isinstance(g, dict):
                    continue
                gname = str(g.get('itemName') or '').strip()
                if not gname:
                    continue
                entry = goods_map.setdefault(sname, {}).setdefault(
                    gname, {'count': 0, 'qty': 0, 'amount': 0.0, 'profit': 0.0})
                qty = int(g.get('itemCount') or 0)
                total = float(g.get('totalPrice') or 0)
                entry['count'] += 1
                entry['qty'] += qty
                entry['amount'] += total
                entry['profit'] += total - float(g.get('drpPrice') or 0) * qty

        suppliers = []
        for r in rows:
            name = r['supplier_name']
            amount = r['total_amount'] or 0
            profit = r['total_profit'] or 0
            after_cnt = after_map.get(name, 0)
            goods = sorted(goods_map.get(name, {}).items(),
                           key=lambda kv: kv[1]['count'], reverse=True)[:5]
            suppliers.append({
                'name': name,
                'co_id': r['co_id'] or '',
                'order_count': r['order_count'],
                'total_amount': round(amount, 2),
                'total_cost': round(r['total_cost'] or 0, 2),
                'total_profit': round(profit, 2),
                'profit_rate': round(profit / amount * 100, 1) if amount > 0 else 0,
                'after_count': after_cnt,
                'after_rate': round(after_cnt / r['order_count'] * 100, 1) if r['order_count'] > 0 else 0,
                'first_order': (r['first_order'] or '')[:10] or '-',
                'last_order': (r['last_order'] or '')[:10] or '-',
                'has_goods': True,
                'top_goods': [
                    {'name': gname, 'count': g['count'], 'qty': g['qty'],
                     'amount': round(g['amount'], 2), 'profit': round(g['profit'], 2)}
                    for gname, g in goods
                ],
            })

        return jsonify({'data': suppliers, 'total': len(suppliers)})
    finally:
        conn.close()


@supplier_bp.route('/api/suppliers/dissolve', methods=['POST'])
def api_dissolve_suppliers():
    """解除供应商合作关系"""
    try:
        from config import ACCOUNTS, JUSHUITAN_URL, BROWSER
    except ImportError:
        return jsonify({'success': False, 'message': '缺少 config.py 配置文件，请参照 config.example.py 创建'})
    from browser.login import JushuitanLogin

    data = request.get_json() or {}
    co_ids = data.get('co_ids', [])

    if not co_ids:
        return jsonify({'success': False, 'message': '请选择要解除的供应商'})

    async def do_dissolve():
        results = []
        for account in ACCOUNTS:
            login = JushuitanLogin({
                'url': JUSHUITAN_URL,
                'username': account['username'],
                'password': account['password'],
                'name': account['name'],
            })
            try:
                await login.start(headless=True, slow_mo=200)
                page = await login.get_page()
                await page.goto(JUSHUITAN_URL + '/channel/my/businessDynamics', timeout=30000)
                await page.wait_for_timeout(3000)

                logged_in = await login.is_logged_in()
                if not logged_in:
                    logged_in = await login.login()
                if not logged_in:
                    results.append(f'{account["name"]}: 登录失败')
                    continue

                # 导航到供应商页面
                await page.goto(JUSHUITAN_URL + '/channel/my/supplier', timeout=30000)
                await page.wait_for_timeout(5000)

                for co_id in co_ids:
                    try:
                        # 在页面中找到该供应商并点击解除合作按钮
                        result = await page.evaluate("""
                            (coId) => {
                                // 找到包含该供应商ID的元素
                                const rows = document.querySelectorAll('tr, [class*="item"], [class*="card"]');
                                for (const row of rows) {
                                    if (row.textContent.includes(coId)) {
                                        // 找到"解除合作"或"取消合作"按钮
                                        const btns = row.querySelectorAll('button, a, span');
                                        for (const btn of btns) {
                                            const text = btn.textContent.trim();
                                            if (text.includes('解除') || text.includes('取消合作') || text.includes('删除')) {
                                                btn.click();
                                                return 'clicked: ' + text;
                                            }
                                        }
                                        return 'no button found';
                                    }
                                }
                                return 'supplier not found';
                            }
                        """, co_id)
                        results.append(f'{account["name"]} - {co_id}: {result}')

                        # 如果点击了按钮，等待确认弹窗
                        if 'clicked' in result:
                            await page.wait_for_timeout(1000)
                            # 点击确认按钮
                            await page.evaluate("""
                                () => {
                                    const btns = document.querySelectorAll('.ant-modal-confirm-btns button, .ant-btn-primary, button');
                                    for (const btn of btns) {
                                        const text = btn.textContent.trim();
                                        if (text === '确定' || text === '确认' || text === '是') {
                                            btn.click();
                                            return 'confirmed';
                                        }
                                    }
                                    return 'no confirm button';
                                }
                            """)
                            await page.wait_for_timeout(1000)

                    except Exception as e:
                        results.append(f'{account["name"]} - {co_id}: 错误 - {str(e)}')

            except Exception as e:
                results.append(f'{account["name"]}: 异常 - {str(e)}')
            finally:
                await login.close()

        return results

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(do_dissolve())
        success_count = len([r for r in results if 'clicked' in r])
        logger.info(f"解除供应商: 成功 {success_count} 个")
        return jsonify({
            'success': True,
            'message': f'处理完成，成功 {success_count} 个',
            'details': results
        })
    except Exception as e:
        logger.error(f"解除供应商失败: {e}")
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'})
    finally:
        loop.close()