# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

BASE = "http://127.0.0.1:5000"
results = []

async def test(name, fn):
    try:
        await asyncio.wait_for(fn(), timeout=8)
        results.append(("PASS", name))
        print(f"[PASS] {name}")
    except Exception as e:
        results.append(("FAIL", name, str(e)[:80]))
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        ctx = await browser.new_context(accept_downloads=True, viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        default_timeout = 5000
        page.set_default_timeout(default_timeout)

        # 首页
        await test("首页加载", lambda: page.goto(BASE + "/"))
        await test("首页-统计卡片", lambda: page.query_selector(".stat-card"))
        await test("首页-日期选择器", lambda: page.query_selector("#datePicker"))
        await test("首页-同步按钮", lambda: page.query_selector("#syncBtn"))
        await test("首页-数据大屏链接", lambda: page.query_selector('a[href=\"/dashboard\"]'))

        # 订单页
        await test("订单页加载", lambda: page.goto(BASE + "/orders"))
        await test("订单页-表格行", lambda: page.query_selector("#ordersTable tbody tr"))
        await test("订单页-同步按钮", lambda: page.query_selector("button >> text=同步订单"))
        await test("订单页-导出按钮", lambda: page.query_selector("button >> text=导出 Excel"))
        await test("订单页-状态筛选", lambda: page.select_option("#statusFilter", "已取消"))
        await test("订单页-备注弹窗打开", lambda: open_and_test_modal(page, "button >> text=备注", "#remarkModal"))
        await test("订单页-备注弹窗关闭", lambda: close_modal(page, "#remarkModal"))
        await test("订单页-详情弹窗打开", lambda: open_and_test_modal(page, "button >> text=详情", "#orderDetailModal"))
        await test("订单页-详情弹窗关闭", lambda: close_modal(page, "#orderDetailModal"))

        # 售后页
        await test("售后页加载", lambda: page.goto(BASE + "/after-sales"))
        await test("售后页-表格行", lambda: page.query_selector("#afterSalesTable tbody tr"))
        await test("售后页-同步按钮", lambda: page.query_selector("button >> text=同步售后"))
        await test("售后页-导出按钮", lambda: page.query_selector("button >> text=导出 Excel"))
        await test("售后页-同意按钮", lambda: page.locator("button >> text=同意").first.click(force=True))
        await test("售后页-拒绝弹窗打开", lambda: open_and_test_modal(page, "button >> text=拒绝", "#rejectModal"))
        await test("售后页-拒绝弹窗关闭", lambda: close_modal(page, "#rejectModal"))

        # 同步页
        await test("同步页加载", lambda: page.goto(BASE + "/sync"))
        await test("同步页-卡片", lambda: page.query_selector(".sync-card"))
        await test("同步页-同步订单按钮", lambda: page.query_selector("button >> text=同步订单"))
        await test("同步页-同步售后按钮", lambda: page.query_selector("button >> text=同步售后"))
        await test("同步页-全自动按钮", lambda: page.query_selector("button >> text=全自动同步"))
        await test("同步页-日志表", lambda: page.query_selector(".data-table"))

        # 利润页
        await test("利润页加载", lambda: page.goto(BASE + "/profit"))
        await test("利润页-卡片", lambda: page.query_selector("#totalRevenue"))
        await test("利润页-日期切换", lambda: page.fill("#datePicker", "2026-07-06"))
        await test("利润页-图表", lambda: page.query_selector("#profitTrendChart"))
        await test("利润页-店铺表", lambda: page.query_selector("#shopTableBody tr"))

        # 供应商页
        await test("供应商页加载", lambda: page.goto(BASE + "/suppliers"))
        await test("供应商页-刷新按钮", lambda: page.query_selector("button >> text=刷新数据"))
        await test("供应商页-同步按钮", lambda: page.query_selector("button >> text=同步供应商"))
        await test("供应商页-全选框", lambda: page.query_selector("#selectAll"))

        # 账号页
        await test("账号页加载", lambda: page.goto(BASE + "/accounts"))
        await test("账号页-列表行", lambda: page.query_selector(".data-table tbody tr"))

        # 大屏页
        await test("大屏页加载", lambda: page.goto(BASE + "/dashboard"))
        await test("大屏页-卡片", lambda: page.query_selector(".stat-box"))

        await browser.close()

    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    print(f"总计: {len(results)} 项: {passed} PASS, {failed} FAIL")
    if failed > 0:
        print("\n失败项:")
        for r in results:
            if r[0] == "FAIL":
                print(f"  - {r[1]}: {r[2]}")

async def open_and_test_modal(page, btn_selector, modal_selector):
    btn = page.locator(btn_selector).first
    await btn.scroll_into_view_if_needed()
    await btn.click(force=True)
    await page.wait_for_selector(modal_selector, state="visible", timeout=3000)

async def close_modal(page, modal_selector):
    close_btn = page.locator(modal_selector + " .modal-close")
    if await close_btn.count() > 0:
        await close_btn.click()

asyncio.run(main())
