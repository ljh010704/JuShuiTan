# -*- coding: utf-8 -*-
import os

BASE = r'F:/JuShuiTan'

# ============================================================
# 1. browser/login.py - 优化 Chromium 启动参数
# ============================================================
path = os.path.join(BASE, 'browser', 'login.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_launch = '''    async def start(self, headless=True, slow_mo=100, timeout=30000):
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
        return self'''

new_launch = '''    async def start(self, headless=True, slow_mo=100, timeout=30000):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--no-first-run',
                '--no-zygote',
                '--disable-setuid-sandbox',
                '--disable-software-rasterizer',
                '--disable-dev-profile',
                '--js-flags=--max-old-space-size=128',
            ]
        )
        return self'''

content = content.replace(old_launch, new_launch)

# 缩小 viewport
content = content.replace(
    "viewport={'width': 1920, 'height': 1080},",
    "viewport={'width': 1280, 'height': 720},"
)

# 优化 close 方法，强制垃圾回收
old_close = '''    async def close(self):
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
            pass'''

new_close = '''    async def close(self):
        try:
            if self._page and not self._page.is_closed():
                await self._page.close()
            self._page = None
        except Exception:
            pass
        try:
            if self._context:
                await self._context.close()
            self._context = None
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
            self._browser = None
        except Exception:
            pass
        try:
            if self._playwright:
                await self._playwright.stop()
            self._playwright = None
        except Exception:
            pass'''

content = content.replace(old_close, new_close)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('login.py: memory optimized')

# ============================================================
# 2. config.py - 修改默认 slow_mo 和 timeout
# ============================================================
path = os.path.join(BASE, 'config.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '"slow_mo": int(os.getenv("BROWSER_SLOW_MO", "100")),',
    '"slow_mo": int(os.getenv("BROWSER_SLOW_MO", "50")),'
)
content = content.replace(
    '"timeout": int(os.getenv("BROWSER_TIMEOUT", "30000")),',
    '"timeout": int(os.getenv("BROWSER_TIMEOUT", "20000")),'
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('config.py: defaults lowered')

# ============================================================
# 3. routes/sync.py - 确保账号间强制释放内存
# ============================================================
path = os.path.join(BASE, 'routes', 'sync.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 login.close() 后面加 gc.collect()
old_cleanup = '''            finally:
                await login.close()'''
new_cleanup = '''            finally:
                await login.close()
                import gc
                gc.collect()'''

content = content.replace(old_cleanup, new_cleanup)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('sync.py: gc after each account')

print('All memory optimizations done!')
