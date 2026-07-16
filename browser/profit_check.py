"""
聚水潭 - 分销店铺商品利润检测
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
            # 导航到分销店铺商品页面
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

    async def _try_api_approach(self, page):
        """尝试通过页面内 API 获取数据"""
        try:
            # 监听网络请求，抓取利润检测相关API
            api_data = await page.evaluate("""
                async () => {
                    try {
                        // 尝试已知的聚水潭API模式
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
                                if (d && d.data) {
                                    results[ep] = d;
                                }
                            } catch(e) {}
                        }
                        return results;
                    } catch(e) {
                        return {error: e.message};
                    }
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
            # 找利润检测按钮 - 多种可能的选择器
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
                # 尝试通过页面内容推断
                page_text = await page.content()
                if 'profitCheck' in page_text or 'profit' in page_text.lower():
                    # 尝试找包含利润相关文字的可点击元素
                    btn = await page.evaluate_handle("""() => {
                        const all = [...document.querySelectorAll('button, a, span, div')];
                        return all.find(el => {
                            const t = el.textContent.trim();
                            return (t.includes('利润') || t.includes('检测')) && el.offsetParent !== null;
                        });
                    }""")
                    if not btn.as_element():
                        btn = None
            
            if not btn:
                print(f"[{self.account_name}] 未找到利润检测按钮")
                return None

            # 点击利润检测
            print(f"[{self.account_name}] 点击利润检测...")
            await btn.click()
            await page.wait_for_timeout(3000)

            # 获取检测结果
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
            # 获取页面文字内容分析
            content = await page.content()
            
            # 尝试提取"供应商已下架"相关数据
            supplier_info = await page.evaluate("""() => {
                const text = document.body.innerText;
                const result = {};
                
                // 查找"已下架"相关数字
                const removedMatch = text.match(/供应商已下架[\\s\\S]*?(\\d+)/);
                if (removedMatch) result.supplier_removed_count = parseInt(removedMatch[1]);
                
                // 查找"禁售"相关数字
                const bannedMatch = text.match(/禁售平台[\\s\\S]*?(\\d+)/);
                if (bannedMatch) result.banned_platform_count = parseInt(bannedMatch[1]);
                
                // 通用匹配：查找含数字的行
                const lines = text.split('\\n').filter(l => l.trim());
                result.lines = lines.filter(l => /\\d+/.test(l)).slice(0, 30);
                
                return result;
            }""")
            
            if supplier_info:
                result['supplier_removed_count'] = supplier_info.get('supplier_removed_count', 0)
                result['banned_platform_count'] = supplier_info.get('banned_platform_count', 0)
                result['_page_lines'] = supplier_info.get('lines', [])

            # 尝试提取表格数据
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
                # 分析表格数据，分类供应商已下架和禁售平台商品
                for row in table_data:
                    row_text = ' '.join(row)
                    entry = {
                        'data': row,
                        'raw': row_text
                    }
                    if '下架' in row_text or '禁售' in row_text:
                        if '下架' in row_text:
                            result['supplier_removed'].append(entry)
                        if '禁售' in row_text:
                            result['banned_platform'].append(entry)
                
                # 如果没精确匹配，把所有数据放进去
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
            
            # 尝试各种可能的字段名
            result['supplier_removed_count'] = (
                d.get('supplierRemovedCount') or 
                d.get('supplierRemoved') or 
                d.get('offShelfCount') or 
                d.get('downCount') or 0
            )
            result['banned_platform_count'] = (
                d.get('bannedPlatformCount') or 
                d.get('bannedCount') or 
                d.get('forbiddenCount') or 0
            )
            
            # 列表数据
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
