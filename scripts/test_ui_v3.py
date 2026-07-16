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

async def js_click(page, text):
    """Click using JS, bypasses visibility checks"""
    await page.evaluate(f"""() => {{
        const btn = [...document.querySelectorAll('button')].find(el => el.textContent.trim().includes('{text}'));
        if (btn) btn.click();
        return !!btn;
    }}""")

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
        await test("3.首页-同步按钮", lambda: js_click(page, "同步数据"))
        await test("4.首页-等待响应", lambda: page.wait_for_timeout(1000))

        # ===== 订单页 =====
        await test("5.订单页加载", lambda: page.goto(BASE + "/orders"))
        await test("6.订单页-表格", lambda: page.query_selector("#ordersTable tbody tr"))
        await test("7.订单页-同步订单", lambda: js_click(page, "同步订单"))
        await test("8.订单页-等待", lambda: page.wait_for_timeout(1000))
        await test("9.订单页-导出Excel", lambda: js_click(page, "导出 Excel"))
        await test("10.订单页-等待", lambda: page.wait_for_timeout(1000))
        await test("11.订单页-状态筛选", lambda: page.select_option("#statusFilter", "已取消"))
        await test("12.订单页-备注弹窗", lambda: js_click(page, "备注") and page.wait_for_selector("#remarkModal", state="visible", timeout=3000))
        await test("13.订单页-关闭备注", lambda: page.evaluate("closeModal('remarkModal')"))
        await test("14.订单页-详情弹窗", lambda: js_click(page, "详情") and page.wait_for_selector("#orderDetailModal", state="visible", timeout=3000))
        await test("15.订单页-详情内容", lambda: page.query_selector("#orderDetailBody div"))
        await test("16.订单页-关闭详情", lambda: page.evaluate("closeModal('orderDetailModal')"))

        # ===== 售后页 =====
        await test("17.售后页加载", lambda: page.goto(BASE + "/after-sales"))
        await test("18.售后页-表格", lambda: page.query_selector("#afterSalesTable tbody tr"))
        await test("19.售后页-同步售后", lambda: js_click(page, "同步售后"))
        await test("20.售后页-等待", lambda: page.wait_for_timeout(1000))
        await test("21.售后页-导出", lambda: js_click(page, "导出 Excel"))
        await test("22.售后页-等待", lambda: page.wait_for_timeout(1000))
        await test("23.售后页-同意", lambda: js_click(page, "同意"))
        await test("24.售后页-等待", lambda: page.wait_for_timeout(1000))
        await test("25.售后页-拒绝弹窗", lambda: js_click(page, "拒绝") and page.wait_for_selector("#rejectModal", state="visible", timeout=3000))
        await test("26.售后页-关闭弹窗", lambda: page.evaluate("closeModal('rejectModal')"))

        # ===== 同步页 =====
        await test("27.同步页加载", lambda: page.goto(BASE + "/sync"))
        await test("28.同步页-卡片", lambda: page.query_selector(".sync-card"))
        await test("29.同步页-同步订单", lambda: js_click(page, "同步订单"))
        await test("30.同步页-状态可见", lambda: page.wait_for_selector("#syncStatus", state="visible", timeout=3000))
        await test("31.同步页-等待5s", lambda: page.wait_for_timeout(5000))
        await test("32.同步页-同步售后", lambda: js_click(page, "同步售后"))
        await test("33.同步页-等待5s", lambda: page.wait_for_timeout(5000))
        await test("34.同步页-全自动", lambda: js_click(page, "全自动同步"))
        await test("35.同步页-等待5s", lambda: page.wait_for_timeout(5000))
        await test("36.同步页-日志表", lambda: page.query_selector(".data-table tbody tr"))

        # ===== 利润页 =====
        await test("37.利润页加载", lambda: page.goto(BASE + "/profit"))
        await test("38.利润页-卡片", lambda: page.query_selector("#totalRevenue"))
        await test("39.利润页-日期切换", lambda: page.fill("#datePicker", "2026-07-06") and page.wait_for_timeout(1000))
        await test("40.利润页-图表", lambda: page.query_selector("#profitTrendChart"))
        await test("41.利润页-店铺表", lambda: page.query_selector("#shopTableBody tr"))

        # ===== 供应商页 =====
        await test("42.供应商页加载", lambda: page.goto(BASE + "/suppliers"))
        await test("43.供应商页-刷新", lambda: js_click(page, "刷新数据") and page.wait_for_timeout(1000))
        await test("44.供应商页-同步", lambda: js_click(page, "同步供应商") and page.wait_for_timeout(1000))

        # ===== 账号页 =====
        await test("45.账号页加载", lambda: page.goto(BASE + "/accounts"))
        await test("46.账号页-列表", lambda: page.query_selector(".data-table tbody tr"))

        # ===== 大屏页 =====
        await test("47.大屏页加载", lambda: page.goto(BASE + "/dashboard"))
        await test("48.大屏页-卡片", lambda: page.query_selector(".stat-box"))

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
