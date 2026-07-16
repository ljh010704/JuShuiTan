# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:5000"
results = []

async def test(name, fn):
    try:
        await asyncio.wait_for(fn(), timeout=8)
        results.append(("PASS", name))
        print(f"[PASS] {name}")
    except Exception as e:
        results.append(("FAIL", name, str(e)[:60]))
        print(f"[FAIL] {name}: {e}")

async def js_click_and_wait_modal(page, text, modal_id):
    """Click button by text using JS, then wait for modal"""
    clicked = await page.evaluate(f"""() => {{
        const btn = [...document.querySelectorAll('button')].find(el => el.textContent.trim().includes('{text}'));
        if (btn) btn.click();
        return !!btn;
    }}""")
    if not clicked:
        raise Exception(f"Button {text} not found")
    await page.wait_for_selector(modal_id, state="visible", timeout=3000)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        ctx = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        page.set_default_timeout(5000)

        # ===== 首页 =====
        await test("1.首页加载", lambda: page.goto(BASE + "/"))
        await test("2.首页-统计卡片", lambda: page.query_selector(".stat-card"))
        await test("3.首页-同步按钮", lambda: page.evaluate("document.getElementById(\'syncBtn\').click()"))
        await test("4.首页-等待", lambda: page.wait_for_timeout(1000))

        # ===== 订单页 =====
        await test("5.订单页加载", lambda: page.goto(BASE + "/orders"))
        await test("6.订单页-表格", lambda: page.query_selector("#ordersTable tbody tr"))
        await test("7.订单页-同步订单", lambda: page.evaluate("document.querySelector(\'button[class*=primary]\').click()") and page.wait_for_timeout(1000))
        await test("8.订单页-导出Excel", lambda: page.evaluate("[...document.querySelectorAll('button')].find(b=>b.textContent.includes(\'导出\')).click()") and page.wait_for_timeout(1000))
        await test("9.订单页-状态筛选", lambda: page.select_option("#statusFilter", "已取消"))
        await test("10.订单页-备注弹窗", lambda: js_click_and_wait_modal(page, "备注", "#remarkModal"))
        await test("11.订单页-关闭备注", lambda: page.evaluate("closeModal(\'remarkModal\')"))
        await test("12.订单页-详情弹窗", lambda: js_click_and_wait_modal(page, "详情", "#orderDetailModal"))
        await test("13.订单页-详情内容", lambda: page.query_selector("#orderDetailBody div"))
        await test("14.订单页-关闭详情", lambda: page.evaluate("closeModal(\'orderDetailModal\')"))

        # ===== 售后页 =====
        await test("15.售后页加载", lambda: page.goto(BASE + "/after-sales"))
        await test("16.售后页-表格", lambda: page.query_selector("#afterSalesTable tbody tr"))
        await test("17.售后页-同步", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'同步\')).click()") and page.wait_for_timeout(1000))
        await test("18.售后页-导出", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'导出\')).click()") and page.wait_for_timeout(1000))
        await test("19.售后页-同意", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'同意\')).click()") and page.wait_for_timeout(1000))
        await test("20.售后页-拒绝弹窗", lambda: js_click_and_wait_modal(page, "拒绝", "#rejectModal"))
        await test("21.售后页-关闭弹窗", lambda: page.evaluate("closeModal(\'rejectModal\')"))

        # ===== 同步页 =====
        await test("22.同步页加载", lambda: page.goto(BASE + "/sync"))
        await test("23.同步页-卡片", lambda: page.query_selector(".sync-card"))
        await test("24.同步页-同步订单", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'同步订单\')).click()"))
        await test("25.同步页-状态可见", lambda: page.wait_for_selector("#syncStatus", state="visible", timeout=3000))
        await test("26.同步页-等待5s", lambda: page.wait_for_timeout(5000))
        await test("27.同步页-同步售后", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'同步售后\')).click()"))
        await test("28.同步页-等待5s", lambda: page.wait_for_timeout(5000))
        await test("29.同步页-全自动", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'全自动\')).click()"))
        await test("30.同步页-等待5s", lambda: page.wait_for_timeout(5000))
        await test("31.同步页-日志表", lambda: page.query_selector(".data-table tbody tr"))

        # ===== 利润页 =====
        await test("32.利润页加载", lambda: page.goto(BASE + "/profit"))
        await test("33.利润页-卡片", lambda: page.query_selector("#totalRevenue"))
        await test("34.利润页-日期切换", lambda: page.fill("#datePicker", "2026-07-06"))
        await test("35.利润页-加载", lambda: page.wait_for_timeout(1000))
        await test("36.利润页-图表", lambda: page.query_selector("#profitTrendChart"))
        await test("37.利润页-店铺表", lambda: page.query_selector("#shopTableBody tr"))

        # ===== 供应商页 =====
        await test("38.供应商页加载", lambda: page.goto(BASE + "/suppliers"))
        await test("39.供应商页-刷新", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'刷新\')).click()"))
        await test("40.供应商页-等待", lambda: page.wait_for_timeout(1000))
        await test("41.供应商页-同步", lambda: page.evaluate("[...document.querySelectorAll(\'button\')].find(b=>b.textContent.includes(\'同步\')).click()"))
        await test("42.供应商页-等待", lambda: page.wait_for_timeout(1000))

        # ===== 账号页 =====
        await test("43.账号页加载", lambda: page.goto(BASE + "/accounts"))
        await test("44.账号页-列表", lambda: page.query_selector(".data-table tbody tr"))

        # ===== 大屏页 =====
        await test("45.大屏页加载", lambda: page.goto(BASE + "/dashboard"))
        await test("46.大屏页-卡片", lambda: page.query_selector(".stat-box"))

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

asyncio.run(main())
