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
        results.append(("FAIL", name, str(e)[:80]))
        print(f"[FAIL] {name}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        ctx = await browser.new_context(accept_downloads=True)
        page = await ctx.new_page()

        # ===== 首页 =====
        await test("首页加载", lambda: page.goto(BASE + "/", wait_until="networkidle"))
        await test("首页-统计卡片", lambda: page.wait_for_selector(".stat-card", timeout=5000))
        await test("首页-日期选择器存在", lambda: page.wait_for_selector("#datePicker", timeout=5000))
        await test("首页-同步按钮可点击", lambda: page.click("#syncBtn", timeout=5000) and page.wait_for_timeout(2000))

        # ===== 订单页 =====
        await test("订单页加载", lambda: page.goto(BASE + "/orders", wait_until="networkidle"))
        await test("订单页-表格", lambda: page.wait_for_selector("#ordersTable", timeout=5000))
        await test("订单页-同步按钮", lambda: page.click("button:has-text('同步订单')", timeout=5000) and page.wait_for_timeout(2000))
        await test("订单页-导出Excel", lambda: page.click("button:has-text('导出 Excel')", timeout=5000) and page.wait_for_timeout(2000))
        await test("订单页-状态筛选", lambda: page.select_option("#statusFilter", "已取消") if page.query_selector("#statusFilter") else None)
        await test("订单页-备注按钮", lambda: page.click("button:has-text('备注')", timeout=5000) if page.query_selector("button:has-text('备注')") else None)
        await test("订单页-弹窗关闭", lambda: page.click("#remarkModal .modal-close", timeout=3000) if page.is_visible("#remarkModal") else None)

        # ===== 售后页 =====
        await test("售后页加载", lambda: page.goto(BASE + "/after-sales", wait_until="networkidle"))
        await test("售后页-表格", lambda: page.wait_for_selector("#afterSalesTable", timeout=5000))
        await test("售后页-同步按钮", lambda: page.click("button:has-text('同步售后')", timeout=5000) and page.wait_for_timeout(2000))
        await test("售后页-导出Excel", lambda: page.click("button:has-text('导出 Excel')", timeout=5000) and page.wait_for_timeout(2000))

        # Handle dialogs for approve/reject
        page.on("dialog", lambda dialog: dialog.accept())
        await test("售后页-同意按钮", lambda: page.click("button:has-text('同意')", timeout=5000) if page.query_selector("button:has-text('同意')") else None)
        await test("售后页-拒绝按钮弹窗", lambda: page.click("button:has-text('拒绝')", timeout=5000) if page.query_selector("button:has-text('拒绝')") else None)
        await test("售后页-弹窗关闭", lambda: page.click("#rejectModal .modal-close", timeout=3000) if page.is_visible("#rejectModal") else None)

        # ===== 同步页 =====
        await test("同步页加载", lambda: page.goto(BASE + "/sync", wait_until="networkidle"))
        await test("同步页-同步卡片", lambda: page.wait_for_selector(".sync-card", timeout=5000))
        await test("同步页-同步订单", lambda: page.click("button:has-text('同步订单')", timeout=5000) and page.wait_for_timeout(2000))
        await test("同步页-同步售后", lambda: page.click("button:has-text('同步售后')", timeout=5000) and page.wait_for_timeout(2000))
        await test("同步页-全自动同步", lambda: page.click("button:has-text('全自动同步')", timeout=5000) and page.wait_for_timeout(2000))
        await test("同步页-同步日志表", lambda: page.wait_for_selector(".data-table", timeout=5000))

        # ===== 利润页 =====
        await test("利润页加载", lambda: page.goto(BASE + "/profit", wait_until="networkidle"))
        await test("利润页-统计卡片", lambda: page.wait_for_selector("#totalRevenue", timeout=5000))
        await test("利润页-日期切换", lambda: page.fill("#datePicker", "2026-07-06") and page.wait_for_timeout(1500))
        await test("利润页-图表渲染", lambda: page.wait_for_selector("#profitTrendChart", timeout=5000))

        # ===== 供应商页 =====
        await test("供应商页加载", lambda: page.goto(BASE + "/suppliers", wait_until="networkidle"))
        await test("供应商页-表格", lambda: page.wait_for_selector("#supplierTable", timeout=5000))
        await test("供应商页-刷新按钮", lambda: page.click("button:has-text('刷新数据')", timeout=5000) and page.wait_for_timeout(1500))
        await test("供应商页-同步供应商", lambda: page.click("button:has-text('同步供应商')", timeout=5000) and page.wait_for_timeout(2000))

        # ===== 账号页 =====
        await test("账号页加载", lambda: page.goto(BASE + "/accounts", wait_until="networkidle"))
        await test("账号页-表格", lambda: page.wait_for_selector(".data-table", timeout=5000))

        # ===== 大屏页 =====
        await test("大屏页加载", lambda: page.goto(BASE + "/dashboard", wait_until="networkidle"))
        await test("大屏页-统计卡片", lambda: page.wait_for_selector(".stat-box", timeout=5000))

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
