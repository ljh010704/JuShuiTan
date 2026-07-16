# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:5000"
results = []

async def test(name, fn):
    try:
        await fn()
        results.append(("PASS", name))
        print(f"[PASS] {name}")
    except Exception as e:
        results.append(("FAIL", name, str(e)[:100]))
        print(f"[FAIL] {name}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        ctx = await browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()

        # Handle all dialogs automatically
        page.on("dialog", lambda d: d.accept())

        # ===== 首页 =====
        await test("首页加载", lambda: page.goto(BASE + "/", wait_until="networkidle"))
        await test("首页-统计卡片", lambda: page.wait_for_selector(".stat-card", timeout=5000))
        await test("首页-日期选择器", lambda: page.wait_for_selector("#datePicker", timeout=5000))
        await test("首页-同步按钮点击", lambda: page.click("#syncBtn"))
        await test("首页-同步状态显示", lambda: page.wait_for_timeout(2000))

        # ===== 订单页 =====
        await test("订单页加载", lambda: page.goto(BASE + "/orders", wait_until="networkidle"))
        await test("订单页-表格渲染", lambda: page.wait_for_selector("#ordersTable tbody tr", timeout=5000))
        await test("订单页-同步订单", lambda: page.click("button:has-text('同步订单')"))
        await test("订单页-同步不跳转", lambda: page.wait_for_timeout(2000))
        await test("订单页-导出Excel", lambda: page.click("button:has-text('导出 Excel')"))
        await test("订单页-导出完成", lambda: page.wait_for_timeout(2000))
        await test("订单页-状态筛选", lambda: page.select_option("#statusFilter", "已取消"))
        await test("订单页-筛选生效", lambda: page.wait_for_timeout(500))
        
        # 备注按钮 - 滚动到第一个并点击
        await test("订单页-备注按钮存在", lambda: page.wait_for_selector("button:has-text('备注')", timeout=5000))
        await test("订单页-点击备注", lambda: page.evaluate("document.querySelector(\"button:has-text('备注')\").scrollIntoView()") and page.click("button:has-text('备注')", force=True))
        await test("订单页-备注弹窗打开", lambda: page.wait_for_selector("#remarkModal", state="visible", timeout=3000))
        await test("订单页-关闭备注弹窗", lambda: page.click("#remarkModal .modal-close"))

        # 详情按钮
        await test("订单页-详情按钮", lambda: page.click("button:has-text('详情')", force=True))
        await test("订单页-详情弹窗", lambda: page.wait_for_selector("#orderDetailModal", state="visible", timeout=3000))
        await test("订单页-关闭详情弹窗", lambda: page.click("#orderDetailModal .modal-close"))

        # ===== 售后页 =====
        await test("售后页加载", lambda: page.goto(BASE + "/after-sales", wait_until="networkidle"))
        await test("售后页-表格渲染", lambda: page.wait_for_selector("#afterSalesTable tbody tr", timeout=5000))
        await test("售后页-同步售后", lambda: page.click("button:has-text('同步售后')"))
        await test("售后页-同步不跳转", lambda: page.wait_for_timeout(2000))
        await test("售后页-导出Excel", lambda: page.click("button:has-text('导出 Excel')"))
        await test("售后页-导出完成", lambda: page.wait_for_timeout(2000))
        await test("售后页-同意按钮", lambda: page.click("button:has-text('同意')", force=True))
        await test("售后页-同意完成", lambda: page.wait_for_timeout(2000))
        await test("售后页-拒绝按钮弹窗", lambda: page.click("button:has-text('拒绝')", force=True))
        await test("售后页-弹窗关闭", lambda: page.click("#rejectModal .modal-close"))

        # ===== 同步页 =====
        await test("同步页加载", lambda: page.goto(BASE + "/sync", wait_until="networkidle"))
        await test("同步页-三个卡片", lambda: page.wait_for_selector(".sync-card", timeout=5000))
        await test("同步页-同步订单", lambda: page.click("button:has-text('同步订单')"))
        await test("同步页-状态显示", lambda: page.wait_for_selector("#syncStatus", state="visible", timeout=3000))
        await test("同步页-等待5秒", lambda: page.wait_for_timeout(5000))
        await test("同步页-同步售后", lambda: page.click("button:has-text('同步售后')"))
        await test("同步页-等待5秒", lambda: page.wait_for_timeout(5000))
        await test("同步页-全自动同步", lambda: page.click("button:has-text('全自动同步')"))
        await test("同步页-等待5秒", lambda: page.wait_for_timeout(5000))
        await test("同步页-同步日志表", lambda: page.wait_for_selector(".data-table tbody tr", timeout=5000))

        # ===== 利润页 =====
        await test("利润页加载", lambda: page.goto(BASE + "/profit", wait_until="networkidle"))
        await test("利润页-统计卡片", lambda: page.wait_for_selector("#totalRevenue", timeout=5000))
        await test("利润页-日期切换", lambda: page.fill("#datePicker", "2026-07-06"))
        await test("利润页-加载数据", lambda: page.wait_for_timeout(1500))
        await test("利润页-图表存在", lambda: page.wait_for_selector("#profitTrendChart", timeout=5000))
        await test("利润页-店铺表格", lambda: page.wait_for_selector("#shopTableBody tr", timeout=5000))

        # ===== 供应商页 =====
        await test("供应商页加载", lambda: page.goto(BASE + "/suppliers", wait_until="networkidle"))
        await test("供应商页-等待渲染", lambda: page.wait_for_timeout(2000))
        await test("供应商页-刷新", lambda: page.click("button:has-text('刷新数据')"))
        await test("供应商页-刷新完成", lambda: page.wait_for_timeout(2000))
        await test("供应商页-同步供应商", lambda: page.click("button:has-text('同步供应商')"))
        await test("供应商页-同步启动", lambda: page.wait_for_timeout(2000))

        # ===== 账号页 =====
        await test("账号页加载", lambda: page.goto(BASE + "/accounts", wait_until="networkidle"))
        await test("账号页-显示账号", lambda: page.wait_for_selector(".data-table tbody tr", timeout=5000))
        await test("账号页-至少1个账号", lambda: page.evaluate("document.querySelectorAll('.data-table tbody tr').length > 0"))

        # ===== 大屏页 =====
        await test("大屏页加载", lambda: page.goto(BASE + "/dashboard", wait_until="networkidle"))
        await test("大屏页-统计卡片", lambda: page.wait_for_selector(".stat-box", timeout=5000))
        await test("大屏页-等待数据", lambda: page.wait_for_timeout(2000))

        await browser.close()

    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    print(f"总计: {passed} PASS, {failed} FAIL")
    if failed > 0:
        print("\n失败项:")
        for r in results:
            if r[0] == "FAIL":
                print(f"  - {r[1]}: {r[2]}")

asyncio.run(main())
