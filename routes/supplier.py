"""
供应商分析路由
"""
import asyncio
from flask import Blueprint, render_template, jsonify, request
from models.database import get_connection
import json

supplier_bp = Blueprint('supplier', __name__)


@supplier_bp.route('/suppliers')
def suppliers_page():
    return render_template('suppliers.html')


@supplier_bp.route('/api/suppliers')
def api_suppliers():
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT
                json_extract(raw_data, '$.supplierName') as supplier_name,
                json_extract(raw_data, '$.supplierCoId') as supplier_co_id,
                COUNT(*) as order_count,
                SUM(pay_amount) as total_amount,
                SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN profit ELSE 0 END) as total_profit,
                SUM(CASE WHEN order_type LIKE '%分销Plus%' THEN purchase_cost ELSE 0 END) as total_cost,
                MIN(created_at) as first_order,
                MAX(created_at) as last_order
            FROM orders
            WHERE json_extract(raw_data, '$.supplierName') IS NOT NULL
            GROUP BY supplier_co_id
            ORDER BY order_count DESC
        """).fetchall()

        suppliers = []
        for r in rows:
            name = r[0] if r[0] else '未知'
            amount = r[3] or 0
            profit = r[4] or 0
            rate = (profit / amount * 100) if amount > 0 else 0

            suppliers.append({
                'name': name,
                'co_id': r[1],
                'order_count': r[2],
                'total_amount': round(amount, 2),
                'total_profit': round(profit, 2),
                'total_cost': round(r[5] or 0, 2),
                'profit_rate': round(rate, 1),
                'first_order': r[6][:10] if r[6] else '-',
                'last_order': r[7][:10] if r[7] else '-',
                'has_goods': r[2] > 0,
            })

        return jsonify({'data': suppliers, 'total': len(suppliers)})
    finally:
        conn.close()


@supplier_bp.route('/api/suppliers/dissolve', methods=['POST'])
def api_dissolve_suppliers():
    """解除供应商合作关系"""
    from config import ACCOUNTS, JUSHUITAN_URL, BROWSER
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
        return jsonify({
            'success': True,
            'message': f'处理完成，成功 {success_count} 个',
            'details': results
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'})
    finally:
        loop.close()
