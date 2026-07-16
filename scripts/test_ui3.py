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

        page.on("dialog", lambda d: d.accept())

        # ===== 首页 =====
        await test("1.首页加载", lambda: page.goto(BASE + "/", wait_until="networkidle"))
        await test("2.首页-统计卡片", lambda: page.wait_for_selector(".stat-card", timeout=5000))
        await test("3.首页-日期选择器", lambda: page.wait_for_selector("#datePicker", timeout=5000))
        await test("4.首页-同步按钮", lambda: page.click("#syncBtn") and page.wait_for_timeout(1000))

        # ===== 订单页 =====
        await test("5.订单页加载", lambda: page.goto(BASE + "/orders", wait_until="networkidle"))
        await test("6.订单页-表格", lambda: page.wait_for_selector("#ordersTable tbody tr", timeout=5000))
        await test("7.订单页-同步按钮", lambda: page.click("button >> text=同步订单") and page.wait_for_timeout(1000))
        await test("8.订单页-导出Excel", lambda: page.click("button >> text=导出 Excel") and page.wait_for_timeout(1000))
        await test("9.订单页-状态筛选", lambda: page.select_option("#statusFilter", "已取消") and page.wait_for_timeout(500))
        await test("10.订单页-备注按钮", lambda: page.locator("button >> text=备注").first.scroll_into_view_if_needed() and page.locator("button >> text=备注").first.click(force=True) and page.wait_for_timeout(500))
        await test("11.订单页-备注弹窗", lambda: page.wait_for_selector("#remarkModal", state="visible", timeout=3000))
        await test("12.订单页-关闭弹窗", lambda: page.click("#remarkModal .modal-close"))
        await test("13.订单页-详情按钮", lambda: page.locator("button >> text=详情").first.scroll_into_view_if_needed() and page.locator("button >> text=详情").first.click(force=True) and page.wait_for_timeout(500))
        await test("14.订单页-详情弹窗", lambda: page.wait_for_selector("#orderDetailModal", state="visible", timeout=3000))
        await test("15.订单页-关闭弹窗", lambda: page.click("#orderDetailModal .modal-close"))

        # ===== 售后页 =====
        await test("16.售后页加载", lambda: page.goto(BASE + "/after-sales", wait_until="networkidle"))
        await test("17.售后页-表格", lambda: page.wait_for_selector("#afterSalesTable tbody tr", timeout=5000))
        await test("18.售后页-同步", lambda: page.click("button >> text=同步售后") and page.wait_for_timeout(1000))
        await test("19.售后页-导出", lambda: page.click("button >> text=导出 Excel") and page.wait_for_timeout(1000))
        await test("20.售后页-同意按钮", lambda: page.locator("button >> text=同意").first.scroll_into_view_if_needed() and page.locator("button >> text=同意").first.click(force=True) and page.wait_for_timeout(1000))
        await test("21.售后页-拒绝弹窗", lambda: page.locator("button >> text=拒绝").first.scroll_into_view_if_needed() and page.locator("button >> text=拒绝").first.click(force=True) and page.wait_for_timeout(500))
        await test("22.售后页-关闭弹窗", lambda: page.click("#rejectModal .modal-close"))

        # ===== 同步页 =====
        await test("23.同步页加载", lambda: page.goto(BASE + "/sync", wait_until="networkidle"))
        await test("24.同步页-卡片", lambda: page.wait_for_selector(".sync-card", timeout=5000))
        await test("25.同步页-同步订单", lambda: page.click("button >> text=同步订单") and page.wait_for_timeout(1500))
        await test("26.同步页-状态可见", lambda: page.wait_for_selector("#syncStatus", state="visible", timeout=3000))
        page.on("dialog", lambda d: d.accept())
        await test("27.同步页-同步售后", lambda: page.click("button >> text=同步售后") and page.wait_for_timeout(1500))
        await test("28.同步页-全自动同步", lambda: page.click("button >> text=全自动同步") and page.wait_for_timeout(1500))
        await test("29.同步页-日志表", lambda: page.wait_for_selector(".data-table", timeout=5000))

        # ===== 利润页 =====
        await test("30.利润页加载", lambda: page.goto(BASE + "/profit", wait_until="networkidle"))
        await test("31.利润页-卡片", lambda: page.wait_for_selector("#totalRevenue", timeout=5000))
        await test("32.利润页-日期切换", lambda: page.fill("#datePicker", "2026-07-06") and page.wait_for_timeout(1500))
        await test("33.利润页-图表", lambda: page.wait_for_selector("#profitTrendChart", timeout=5000))
        await test("34.利润页-店铺表", lambda: page.wait_for_selector("#shopTableBody tr", timeout=5000))

        # ===== 供应商页 =====
        await test("35.供应商页加载", lambda: page.goto(BASE + "/suppliers", wait_until="networkidle"))
        await test("36.供应商页-等待", lambda: page.wait_for_timeout(2000))
        await test("37.供应商页-刷新", lambda: page.click("button >> text=刷新数据") and page.wait_for_timeout(1500))
        await test("38.供应商页-同步", lambda: page.click("button >> text=同步供应商") and page.wait_for_timeout(1500))

        # ===== 账号页 =====
        await test("39.账号页加载", lambda: page.goto(BASE + "/accounts", wait_until="networkidle"))
        await test("40.账号页-列表", lambda: page.wait_for_selector(".data-table tbody tr", timeout=5000))

        # ===== 大屏页 =====
        await test("41.大屏页加载", lambda: page.goto(BASE + "/dashboard", wait_until="networkidle"))
        await test("42.大屏页-卡片", lambda: page.wait_for_selector(".stat-box", timeout=5000))

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
