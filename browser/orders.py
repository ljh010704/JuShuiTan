"""
聚水潭订单数据抓取模块 - 直接调用API获取所有订单
"""
import asyncio
import json
from datetime import datetime


class OrderScraper:
    def __init__(self, browser_session):
        self.session = browser_session
        self.account_name = getattr(browser_session, 'account_name', '未知账号')

    async def fetch_orders(self, start_date=None, end_date=None):
        """抓取所有订单"""
        page = await self.session.get_page()

        print(f"[{self.account_name}] 开始获取订单...")

        # 获取token
        cookies = await page.context.cookies()
        token = None
        for c in cookies:
            if c['name'] == 'DISTRYBUTION_TOKEN':
                token = c['value']
                break

        if not token:
            print(f"[{self.account_name}] 未获取到token")
            return []

        # 先导航到页面获取coId和uid
        await page.goto(f"{self.session.url}/channel/my/businessDynamics", timeout=30000)
        await page.wait_for_timeout(3000)

        user_info = await page.evaluate("""
            async () => {
                const r = await fetch('/api/drp/buyer/user/info?terminalName=CHANNEL&fromSource=R');
                return await r.json();
            }
        """)

        co_id = None
        uid = None
        if user_info and user_info.get('data'):
            co_id = str(user_info['data'].get('coId', ''))
            uid = str(user_info['data'].get('uid', ''))
        else:
            # 从iframe URL中提取
            await page.goto(f"{self.session.url}/channel/my/printManage/channelTrade/tradePrint", timeout=30000)
            await page.wait_for_timeout(5000)
            for frame in page.frames:
                if 'print.scm121' in frame.url:
                    import re
                    params = dict(re.findall(r'(\w+)=([^&]*)', frame.url))
                    co_id = params.get('coId')
                    uid = params.get('uid')
                    break

        if not co_id or not uid:
            print(f"[{self.account_name}] 无法获取coId和uid")
            return []

        print(f"[{self.account_name}] coId={co_id}, uid={uid}")

        # 分页获取所有订单
        all_orders = []
        seen_ids = set()
        page_num = 1
        page_size = 50
        total = None

        while True:
            result = await page.evaluate("""
                async (args) => {
                    try {
                        const r = await fetch('https://innerapi.scm121.com/api/inner/order/acquireAllSimpleOrders', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'authorization': args.token
                            },
                            body: JSON.stringify(args.body)
                        });
                        return await r.json();
                    } catch(e) {
                        return {error: e.message};
                    }
                }
            """, {
                'token': token,
                'body': {
                    'coId': co_id,
                    'uid': uid,
                    'pageNum': page_num,
                    'pageSize': page_size,
                }
            })

            if result.get('error'):
                print(f"  第{page_num}页错误: {result['error']}")
                break

            if not result.get('success'):
                print(f"  第{page_num}页失败: {result.get('message')}")
                break

            if total is None:
                total = result.get('total', 0)
                print(f"[{self.account_name}] 总订单数: {total}")

            items = result.get('data', [])
            if not items:
                break

            new_count = 0
            for item in items:
                if isinstance(item, dict):
                    oid = str(item.get('oid', ''))
                    if oid and oid not in seen_ids:
                        seen_ids.add(oid)
                        all_orders.append(self._normalize(item))
                        new_count += 1

            print(f"  第{page_num}页: 获取{len(items)}条, 新增{new_count}条")

            if len(all_orders) >= (total or 0):
                break

            page_num += 1
            await asyncio.sleep(0.5)  # 避免请求过快

        print(f"[{self.account_name}] 订单获取完成: 共{len(all_orders)}条")
        return all_orders

    def _normalize(self, raw):
        created = raw.get('orderTime') or raw.get('created') or ''
        status = raw.get('orderStatus') or raw.get('status') or ''
        goods_list = raw.get('disInnerOrderGoodsViewList') or []
        item_count = len(goods_list) if isinstance(goods_list, list) else 0

        return {
            'account_name': self.account_name,
            'order_id': str(raw.get('oid') or raw.get('orderId') or raw.get('id') or ''),
            'external_id': str(raw.get('soId') or raw.get('rawSoId') or ''),
            'shop_id': str(raw.get('shopId') or ''),
            'shop_name': str(raw.get('shopName') or ''),
            'order_type': str(raw.get('orderType') or ''),
            'status': str(status),
            'status_desc': str(raw.get('statusDesc') or raw.get('errorMsg') or ''),
            'item_count': item_count,
            'pay_amount': float(raw.get('payAmount') or raw.get('clientPaidAmt') or 0),
            'freight': float(raw.get('freight') or 0),
            'discount_amount': float(raw.get('discountAmt') or 0),
            'purchase_cost': float(raw.get('purchaseAmt') or 0),
            'profit': float(raw.get('drpAmount') or 0),
            'created_at': str(created),
            'paid_at': str(raw.get('payTime') or ''),
            'shipped_at': str(raw.get('sendTime') or ''),
            'raw_data': json.dumps(raw, ensure_ascii=False),
            'source': 'api',
        }
