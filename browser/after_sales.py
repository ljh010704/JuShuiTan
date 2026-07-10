"""
聚水潭售后数据抓取模块 - 拦截页面自然 API 响应
"""
import json
from datetime import datetime


class AfterSalesScraper:
    def __init__(self, browser_session):
        self.session = browser_session

    async def fetch_after_sales(self, date=None):
        """导航到售后页面，拦截 API 响应"""
        page = await self.session.get_page()
        captured = []

        async def on_response(response):
            url = response.url
            if response.status != 200:
                return
            try:
                ct = response.headers.get('content-type', '')
                if 'json' not in ct:
                    return
                body = await response.json()
                if not isinstance(body, dict):
                    return
                if any(kw in url for kw in ['aftersale', 'afterSale', 'after-sale']):
                    captured.append({'url': url, 'body': body})
            except Exception:
                pass

        page.on('response', on_response)

        try:
            await page.goto(
                f"{self.session.url}/channel/my/sales/tower/afterSales",
                timeout=30000
            )
            await page.wait_for_timeout(12000)

            # 关闭弹窗
            await page.evaluate("""
                () => {
                    document.querySelectorAll('.ant-modal-wrap, .ant-modal-mask').forEach(el => el.remove());
                    document.body.style.overflow = 'auto';
                }
            """)

            # 解析拦截到的数据 - 同一URL取数据最多的那次
            results = {
                'list': [],
                'list_total': 0,
                'statistics': [],
                'pending': [],
                'actions': [],
                'auto_stats': None,
                'refund_amounts': [],
            }

            # 按URL分组，每组取数据最多的响应
            url_best = {}
            for item in captured:
                url = item['url'].split('?')[0]
                body = item['body']
                data = body.get('data', [])
                data_count = len(data) if isinstance(data, list) else 0
                if url not in url_best or data_count > url_best[url]['count']:
                    url_best[url] = {'body': body, 'count': data_count}

            for url, info in url_best.items():
                body = info['body']
                if not body.get('success'):
                    continue

                if 'after-sale/page/list' in url:
                    items = body.get('data', [])
                    if isinstance(items, list):
                        results['list'] = items
                    results['list_total'] = body.get('total', 0)

                elif 'countStatistic' in url:
                    stats = body.get('data', {}).get('statistics', [])
                    if isinstance(stats, list):
                        results['statistics'] = stats

                elif 'pendingSubmission' in url:
                    pending = body.get('data', {}).get('statistics', [])
                    if isinstance(pending, list):
                        results['pending'] = pending

                elif 'afterSaleStatisticsAction' in url:
                    actions = body.get('data', [])
                    if isinstance(actions, list):
                        results['actions'] = actions

                elif 'statistics/auto' in url:
                    results['auto_stats'] = body.get('data')

                elif 'drpRefundAmount' in url:
                    amounts = body.get('data', [])
                    if isinstance(amounts, list):
                        results['refund_amounts'] = amounts

            print(f"[OK] 售后列表: {results['list_total']} 条")
            print(f"  实际获取: {len(results['list'])} 条")
            print(f"  统计: {len(results['statistics'])} 项")
            print(f"  待处理: {len(results['pending'])} 项")
            print(f"  退款金额: {len(results['refund_amounts'])} 条")

            return results

        except Exception as e:
            print(f"[ERROR] 售后数据抓取失败: {e}")
            return {}
        finally:
            page.remove_listener('response', on_response)

    def _normalize(self, raw):
        after_sale_id = str(raw.get('afterSaleOrderNo') or raw.get('asId') or raw.get('afterSaleId') or '')
        order_id = str(raw.get('orderNo') or raw.get('orderId') or '')
        after_type = str(raw.get('afterType') or raw.get('type') or '')
        amount = float(raw.get('refundAmount') or raw.get('amount') or 0)
        goods = raw.get('afterSaleOrderGoodsVO') or {}
        quantity = int(goods.get('refundTotalCount') or raw.get('quantity') or 0)
        # 申请时间优先用 applicationTime
        created = str(raw.get('applicationTime') or raw.get('created') or '')
        # 状态优先用 orderStatus
        status = str(raw.get('orderStatus') or raw.get('drpProcessStatus') or raw.get('status') or '')

        return {
            'after_sale_id': after_sale_id,
            'order_id': order_id,
            'external_id': str(raw.get('soId') or raw.get('outerAsId') or ''),
            'shop_id': str(raw.get('shopId') or ''),
            'shop_name': str(raw.get('shopName') or ''),
            'type': after_type,
            'status': status,
            'reason': str(raw.get('reason') or ''),
            'amount': amount,
            'quantity': quantity,
            'created_at': created,
            'processed_at': str(raw.get('dealTime') or ''),
            'raw_data': json.dumps(raw, ensure_ascii=False),
            'source': 'api',
        }
