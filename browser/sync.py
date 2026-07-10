"""
聚水潭数据同步模块
将本地处理后的数据同步回聚水潭网站
"""
import json
import asyncio
from datetime import datetime


def _merge_result(base, fallback_message):
    if isinstance(base, dict):
        base.setdefault('success', False)
        base.setdefault('message', fallback_message)
        return base
    return {'success': False, 'message': fallback_message}


class JushuitanSync:
    def __init__(self, browser_session):
        self.session = browser_session

    async def approve_after_sale(self, after_sale_id, remark=''):
        """审核同意售后申请"""
        page = await self.session.get_page()
        try:
            await page.goto(
                f"{self.session.url}/channel/my/sales/tower/afterSales",
                timeout=30000
            )
            await page.wait_for_timeout(3000)

            # 搜索目标售后单
            search_input = await page.query_selector(
                'input[placeholder*="搜索"], input[placeholder*="售后单号"], input[placeholder*="订单号"]'
            )
            if search_input:
                await search_input.fill(after_sale_id)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)

            # 找到对应行的操作按钮
            row = await page.query_selector(f'tr:has-text("{after_sale_id}")')
            if row:
                approve_btn = await row.query_selector(
                    'button:has-text("同意"), button:has-text("审核"), a:has-text("同意")'
                )
                if approve_btn:
                    await approve_btn.click()
                    await page.wait_for_timeout(1000)

                    # 如果有备注输入框
                    if remark:
                        remark_input = await page.query_selector(
                            'textarea[placeholder*="备注"], input[placeholder*="备注"]'
                        )
                        if remark_input:
                            await remark_input.fill(remark)

                    # 确认操作
                    confirm_btn = await page.query_selector(
                        '.ant-modal-confirm-btns button.ant-btn-primary, button:has-text("确定")'
                    )
                    if confirm_btn:
                        await confirm_btn.click()
                        await page.wait_for_timeout(2000)
                        return {'success': True, 'message': '售后审核通过'}

            return {'success': False, 'message': '未找到目标售后单或操作按钮'}

        except Exception as e:
            return {'success': False, 'message': f'操作异常: {str(e)}'}

    async def reject_after_sale(self, after_sale_id, reason=''):
        """拒绝售后申请"""
        page = await self.session.get_page()
        try:
            await page.goto(
                f"{self.session.url}/channel/my/sales/tower/afterSales",
                timeout=30000
            )
            await page.wait_for_timeout(3000)

            search_input = await page.query_selector(
                'input[placeholder*="搜索"], input[placeholder*="售后单号"]'
            )
            if search_input:
                await search_input.fill(after_sale_id)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)

            row = await page.query_selector(f'tr:has-text("{after_sale_id}")')
            if row:
                reject_btn = await row.query_selector(
                    'button:has-text("拒绝"), button:has-text("不同意"), a:has-text("拒绝")'
                )
                if reject_btn:
                    await reject_btn.click()
                    await page.wait_for_timeout(1000)

                    if reason:
                        reason_input = await page.query_selector(
                            'textarea[placeholder*="原因"], input[placeholder*="原因"]'
                        )
                        if reason_input:
                            await reason_input.fill(reason)

                    confirm_btn = await page.query_selector(
                        '.ant-modal-confirm-btns button.ant-btn-primary, button:has-text("确定")'
                    )
                    if confirm_btn:
                        await confirm_btn.click()
                        await page.wait_for_timeout(2000)
                        return {'success': True, 'message': '已拒绝售后申请'}

            return {'success': False, 'message': '未找到目标售后单或操作按钮'}

        except Exception as e:
            return {'success': False, 'message': f'操作异常: {str(e)}'}

    async def update_order_remark(self, order_id, remark):
        """更新订单备注"""
        page = await self.session.get_page()
        try:
            await page.goto(
                f"{self.session.url}/channel/my/printManage/channelTrade/tradePrint",
                timeout=30000
            )
            await page.wait_for_timeout(3000)

            # 搜索订单
            search_input = await page.query_selector(
                'input[placeholder*="搜索"], input[placeholder*="订单号"]'
            )
            if search_input:
                await search_input.fill(order_id)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)

            # 找到编辑/备注按钮
            row = await page.query_selector(f'tr:has-text("{order_id}")')
            if row:
                edit_btn = await row.query_selector(
                    'button:has-text("编辑"), button:has-text("备注"), a:has-text("备注")'
                )
                if edit_btn:
                    await edit_btn.click()
                    await page.wait_for_timeout(1000)

                    remark_input = await page.query_selector(
                        'textarea, input[placeholder*="备注"]'
                    )
                    if remark_input:
                        await remark_input.fill(remark)

                    save_btn = await page.query_selector(
                        'button:has-text("保存"), button:has-text("确定")'
                    )
                    if save_btn:
                        await save_btn.click()
                        await page.wait_for_timeout(2000)
                        return {'success': True, 'message': '备注已更新'}

            return {'success': False, 'message': '未找到目标订单'}

        except Exception as e:
            return {'success': False, 'message': f'操作异常: {str(e)}'}

    async def ship_order(self, order_id, logistics_company, tracking_number):
        """订单发货"""
        page = await self.session.get_page()
        try:
            await page.goto(
                f"{self.session.url}/channel/my/printManage/channelTrade/tradePrint",
                timeout=30000
            )
            await page.wait_for_timeout(3000)

            search_input = await page.query_selector(
                'input[placeholder*="搜索"], input[placeholder*="订单号"]'
            )
            if search_input:
                await search_input.fill(order_id)
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)

            row = await page.query_selector(f'tr:has-text("{order_id}")')
            if row:
                ship_btn = await row.query_selector(
                    'button:has-text("发货"), a:has-text("发货")'
                )
                if ship_btn:
                    await ship_btn.click()
                    await page.wait_for_timeout(1000)

                    # 选择快递公司
                    logistics_select = await page.query_selector(
                        'select[placeholder*="快递"], .ant-select:has-text("快递")'
                    )
                    if logistics_select:
                        await logistics_select.click()
                        await page.wait_for_timeout(500)
                        option = await page.query_selector(f'li:has-text("{logistics_company}")')
                        if option:
                            await option.click()

                    # 输入物流单号
                    tracking_input = await page.query_selector(
                        'input[placeholder*="快递单号"], input[placeholder*="物流单号"]'
                    )
                    if tracking_input:
                        await tracking_input.fill(tracking_number)

                    confirm_btn = await page.query_selector(
                        'button:has-text("确定"), button:has-text("确认发货")'
                    )
                    if confirm_btn:
                        await confirm_btn.click()
                        await page.wait_for_timeout(2000)
                        return {'success': True, 'message': '发货成功'}

            return {'success': False, 'message': '未找到目标订单'}

        except Exception as e:
            return {'success': False, 'message': f'操作异常: {str(e)}'}
