"""
聚水潭网站 Playwright 登录模块 - 支持多账号
"""
import os
import json
import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def get_auth_state_file(account_name):
    """获取指定账号的状态文件路径"""
    safe_name = account_name.replace(' ', '_').replace('/', '_')
    return os.path.join(BASE_DIR, f'auth_state_{safe_name}.json')


class JushuitanLogin:
    def __init__(self, config):
        self.config = config
        self.url = config.get('url', 'https://gyl.scm121.com')
        self.username = config['username']
        self.password = config['password']
        self.account_name = config.get('name', self.username)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def start(self, headless=True, slow_mo=100, timeout=30000):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        return self

    async def get_context(self) -> BrowserContext:
        if self._context:
            return self._context
        state_file = get_auth_state_file(self.account_name)
        if os.path.exists(state_file):
            try:
                self._context = await self._browser.new_context(
                    storage_state=state_file,
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                )
                # 注入反检测脚本
                await self._context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    window.chrome = {runtime: {}};
                """)
                return self._context
            except Exception:
                pass
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        )
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
            window.chrome = {runtime: {}};
        """)
        return self._context

    async def get_page(self) -> Page:
        if self._page and not self._page.is_closed():
            return self._page
        context = await self.get_context()
        self._page = await context.new_page()
        return self._page

    async def is_logged_in(self) -> bool:
        try:
            page = await self.get_page()
            await page.goto(f"{self.url}/channel/my/businessDynamics", timeout=15000)
            await page.wait_for_timeout(3000)
            current_url = page.url
            if '/user/login' in current_url:
                return False
            token = await page.evaluate("document.cookie")
            return 'DISTRYBUTION_TOKEN' in token or 'channel' in current_url
        except Exception:
            return False

    async def login(self) -> bool:
        try:
            page = await self.get_page()
            login_url = f"{self.url}/user/login"
            await page.goto(login_url, timeout=30000)
            await page.wait_for_timeout(2000)

            # 填写用户名
            username_input = await page.query_selector('input[placeholder*="聚水潭账号"]')
            if not username_input:
                username_input = await page.query_selector('input[type="text"]')
            if username_input:
                await username_input.fill(self.username)

            # 填写密码
            password_input = await page.query_selector('input[type="password"]')
            if password_input:
                await password_input.fill(self.password)

            # 勾选用户协议
            try:
                checkbox = await page.query_selector('input[type="checkbox"]')
                if checkbox:
                    is_checked = await checkbox.is_checked()
                    if not is_checked:
                        await checkbox.click()
                        await page.wait_for_timeout(300)
            except Exception:
                pass

            # 点击登录
            submit_btn = await page.query_selector('button:has-text("立即登录")')
            if submit_btn:
                await submit_btn.click()
            else:
                await page.keyboard.press('Enter')

            # 等待登录完成
            try:
                await page.wait_for_url("**/channel/**", timeout=15000)
            except Exception:
                if '/user/login' in page.url:
                    print(f"[{self.account_name}] 登录失败")
                    return False

            # 保存登录状态
            await self._save_state()
            print(f"[{self.account_name}] 登录成功")
            return True

        except Exception as e:
            print(f"[{self.account_name}] 登录异常: {e}")
            return False

    async def _save_state(self):
        try:
            context = await self.get_context()
            state_file = get_auth_state_file(self.account_name)
            await context.storage_state(path=state_file)
        except Exception as e:
            print(f"[{self.account_name}] 保存状态失败: {e}")

    async def close(self):
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception:
            pass
