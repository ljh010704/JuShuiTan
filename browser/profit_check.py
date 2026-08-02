# -*- coding: utf-8 -*-
"""
聚水潭 - 分销店铺商品利润检测 + 批量下架
URL: /channel/my/myGoods/distributionGoodsLink
"""
import asyncio
import json
from datetime import datetime


class ProfitCheckScraper:
    def __init__(self, browser_session):
        self.session = browser_session
        self.account_name = getattr(browser_session, 'account_name', '未知账号')
        self.url = browser_session.url

    async def fetch_profit_check(self):
        """
        导航到分销店铺商品页面，执行利润检测
        返回: {
            'supplier_removed': [...],   # 供应商已下架商品
            'banned_platform': [...],     # 禁售平台商品
            'supplier_removed_count': int,
            'banned_platform_count': int,
            'checked_at': str
        }
        """
        page = await self.session.get_page()
        result = {
            'supplier_removed': [],
            'banned_platform': [],
            'supplier_removed_count': 0,
            'banned_platform_count': 0,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            print(f"[{self.account_name}] 导航到分销店铺商品...")
            await page.goto(
                f"{self.url}/channel/my/myGoods/distributionGoodsLink",
                timeout=30000
            )
            await page.wait_for_timeout(3000)

            # 方法1: 尝试直接调用内部API
            api_result = await self._try_api_approach(page)
            if api_result:
                return api_result

            # 方法2: 通过页面按钮点击
            ui_result = await self._try_ui_approach(page)
            if ui_result:
                return ui_result

            print(f"[{self.account_name}] 无法获取利润检测数据")
            return result

        except Exception as e:
            print(f"[{self.account_name}] 利润检测异常: {e}")
            return result

    async def batch_remove_products(self, remove_type='all'):
        """
        执行批量下架操作
        remove_type: 'supplier' | 'banned' | 'all'
        返回: {'success': bool, 'message': str, 'removed_count': int}
        """
        page = await self.session.get_page()
        removed_count = 0
        errors = []

        try:
            # 确保在正确页面
            if '/myGoods/distributionGoodsLink' not in page.url:
                await page.goto(
                    f"{self.url}/channel/my/myGoods/distributionGoodsLink",
                    timeout=30000
                )
                await page.wait_for_timeout(3000)

            # 根据下架类型选择不同操作
            if remove_type in ('supplier', 'all'):
                count = await self._click_batch_remove(page, '供应商已下架')
                removed_count += count
                if count > 0:
                    print(f"[{self.account_name}] 供应商已下架: {count} 件")

            if remove_type in ('banned', 'all'):
                count = await self._click_batch_remove(page, '禁售平台')
                removed_count += count
                if count > 0:
                    print(f"[{self.account_name}] 禁售平台: {count} 件")

            # 确认下架 - 点确认弹窗
            confirm_result = await self._confirm_remove(page)
            
            return {
                'success': True,
                'message': f'成功下架 {removed_count} 件商品',
                'removed_count': removed_count,
                'confirm_status': confirm_result
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'批量下架异常: {str(e)}',
                'removed_count': removed_count
            }

    async def _click_batch_remove(self, page, keyword):
        """点击指定类型的批量下架按钮"""
        count = 0
        try:
            # 找到包含关键词的区域
            btn_found = await page.evaluate(f"""() => {{
                const buttons = [...document.querySelectorAll('button, a, span, div')];
                const btn = buttons.find(b => {{
                    const text = b.textContent.trim();
                    return text.includes('批量下架') && 
                           b.closest('div, tr, section')?.textContent.includes('{keyword}');
                }});
                if (!btn) {{
                    // 更宽泛的匹配
                    const allBtns = buttons.filter(b => b.textContent.trim().includes('批量下架'));
                    return allBtns.length > 0 ? 'found_generic' : 'not_found';
                }}
                btn.click();
                return 'clicked';
            }}""")

            if btn_found == 'clicked' or btn_found == 'found_generic':
                count = 1  # 至少执行了一个
                await page.wait_for_timeout(2000)
                
                # 如果找到了通用按钮，尝试点击
                if btn_found == 'found_generic':
                    await page.evaluate("""() => {
                        const btn = [...document.querySelectorAll('button, a, span, div')]
                            .find(b => b.textContent.trim().includes('批量下架'));
                        if (btn) btn.click();
                    }""")
                    await page.wait_for_timeout(1000)
            else:
                # 尝试API方式
                api_result = await page.evaluate(f"""
                    async () => {{
                        const endpoints = [
                            '/api/drp/goods/batchRemove',
                            '/api/drp/distribution/goods/batchRemove',
                            '/api/inner/goods/batchOffline',
                        ];
                        for (const ep of endpoints) {{
                            try {{
                                const r = await fetch(ep, {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    body: JSON.stringify({{type: '{keyword}'}})
                                }});
                                const d = await r.json();
                                if (d && d.data) return d;
                            }} catch(e) {{}}
                        }}
                        return null;
                    }}
                """)
                if api_result:
                    count = 1
                    
        except Exception as e:
            print(f"批量下架 {keyword} 异常: {e}")
        
        return count

    async def _confirm_remove(self, page):
        """确认下架操作"""
        try:
            # 常见的确认按钮
            confirm_selectors = [
                '.ant-btn-primary:has-text("确定")',
                '.ant-modal-confirm-btns button.ant-btn-primary',
                'button:has-text("确定")',
                'button:has-text("确认")',
                '.ant-btn-dangerous',
                'span.ant-btn-primary',
            ]
            
            for sel in confirm_selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await page.wait_for_timeout(2000)
                        return 'confirmed'
                except:
                    continue
            
            # 通用方式
            result = await page.evaluate("""() => {
                const btns = [...document.querySelectorAll('button')];
                const confirm = btns.find(b => {
                    const t = b.textContent.trim();
                    return (t === '确定' || t === '确认') && b.offsetParent !== null;
                });
                if (confirm) { confirm.click(); return 'confirmed'; }
                return 'no_confirm_needed';
            }""")
            
            return result or 'no_confirm_found'
            
        except Exception as e:
            return f'confirm_error: {e}'

    async def _try_api_approach(self, page):
        """尝试通过页面内 API 获取数据"""
        try:
            api_data = await page.evaluate("""
                async () => {
                    const endpoints = [
                        '/api/drp/goods/profitCheck',
                        '/api/drp/goods/distribution/profitCheck',
                        '/api/inner/goods/profitCheck',
                        '/api/drp/distribution/goods/check',
                    ];
                    const results = {};
                    for (const ep of endpoints) {
                        try {
                            const r = await fetch(ep, {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({})
                            });
                            const d = await r.json();
                            if (d && d.data) results[ep] = d;
                        } catch(e) {}
                    }
                    return results;
                }
            """)
            if api_data and not api_data.get('error'):
                for ep, data in api_data.items():
                    if data:
                        return self._parse_api_response(data)
        except Exception as e:
            print(f"[{self.account_name}] API方式失败: {e}")
        return None

    async def _try_ui_approach(self, page):
        """通过页面按钮点击获取数据"""
        try:
            btn_selectors = [
                'button:has-text("利润检测")',
                'button:has-text("利润检查")',
                'a:has-text("利润检测")',
                '.profit-check-btn',
                '[class*="profit"]',
                'span:has-text("利润检测")',
                'div:has-text("利润检测")',
            ]
            
            btn = None
            for sel in btn_selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        break
                except:
                    continue
            
            if not btn:
                page_text = await page.content()
                if 'profitCheck' in page_text or 'profit' in page_text.lower():
                    try:
                        btn = await page.evaluate_handle("""() => {
                            const all = [...document.querySelectorAll('button, a, span, div')];
                            return all.find(el => {
                                const t = el.textContent.trim();
                                return (t.includes('利润') && t.includes('检测')) && el.offsetParent !== null;
                            });
                        }""")
                        if not btn.as_element():
                            btn = None
                    except:
                        pass
            
            if not btn:
                print(f"[{self.account_name}] 未找到利润检测按钮")
                return None

            print(f"[{self.account_name}] 点击利润检测...")
            await btn.click()
            await page.wait_for_timeout(3000)
            return await self._extract_check_results(page)

        except Exception as e:
            print(f"[{self.account_name}] UI方式失败: {e}")
            return None

    async def _extract_check_results(self, page):
        """提取检测结果"""
        result = {
            'supplier_removed': [],
            'banned_platform': [],
            'supplier_removed_count': 0,
            'banned_platform_count': 0,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            content = await page.content()
            supplier_info = await page.evaluate("""() => {
                const text = document.body.innerText;
                const result = {};
                const removedMatch = text.match(/供应商已下架[\\s\\S]*?(\\d+)/);
                if (removedMatch) result.supplier_removed_count = parseInt(removedMatch[1]);
                const bannedMatch = text.match(/禁售平台[\\s\\S]*?(\\d+)/);
                if (bannedMatch) result.banned_platform_count = parseInt(bannedMatch[1]);
                const lines = text.split('\\n').filter(l => l.trim());
                result.lines = lines.filter(l => /\\d+/.test(l)).slice(0, 30);
                return result;
            }""")
            
            if supplier_info:
                result['supplier_removed_count'] = supplier_info.get('supplier_removed_count', 0)
                result['banned_platform_count'] = supplier_info.get('banned_platform_count', 0)
                result['_page_lines'] = supplier_info.get('lines', [])

            table_data = await page.evaluate("""() => {
                const tables = document.querySelectorAll('table, .ant-table');
                const data = [];
                tables.forEach((t, idx) => {
                    const rows = t.querySelectorAll('tr, .ant-table-row');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td, .ant-table-cell');
                        if (cells.length > 0) {
                            data.push(Array.from(cells).map(c => c.textContent.trim()));
                        }
                    });
                });
                return data.slice(0, 50);
            }""")
            
            if table_data:
                for row in table_data:
                    row_text = ' '.join(row)
                    entry = {'data': row, 'raw': row_text}
                    if '下架' in row_text or '禁售' in row_text:
                        if '下架' in row_text:
                            result['supplier_removed'].append(entry)
                        if '禁售' in row_text:
                            result['banned_platform'].append(entry)
                if not result['supplier_removed'] and not result['banned_platform']:
                    result['_table_data'] = table_data

            return result

        except Exception as e:
            print(f"[{self.account_name}] 提取结果异常: {e}")
            return result

    def _parse_api_response(self, data):
        """解析API响应"""
        result = {
            'supplier_removed': [],
            'banned_platform': [],
            'supplier_removed_count': 0,
            'banned_platform_count': 0,
            'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            d = data.get('data', data)
            result['supplier_removed_count'] = d.get('supplierRemovedCount') or d.get('supplierRemoved') or d.get('offShelfCount') or d.get('downCount') or 0
            result['banned_platform_count'] = d.get('bannedPlatformCount') or d.get('bannedCount') or d.get('forbiddenCount') or 0
            result['supplier_removed'] = d.get('supplierRemovedList') or d.get('offShelfList') or []
            result['banned_platform'] = d.get('bannedPlatformList') or d.get('forbiddenList') or []
        except Exception as e:
            print(f"解析API响应异常: {e}")
        return result

    async def run_check_and_save(self, db_model=None):
        """执行检测并保存结果到数据库"""
        result = await self.fetch_profit_check()
        if db_model:
            db_model.save(result)
        return result
