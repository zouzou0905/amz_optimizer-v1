import os
import pandas as pd
import asyncio
import random
from playwright.async_api import async_playwright
import playwright_stealth

# ================= 配置 =================
INPUT_FILE = 'data/categories/Apparel_分析表.xlsx'
OUTPUT_FILE = 'data/categories/Apparel_Stage3_结构化结果.xlsx'
RESTART_CONTEXT_THRESHOLD = 5
TARGET_ZIPCODE = "10115"
STORAGE_FILE = "amazon_de_state.json"

# ================= 深度 UA 指纹池 (20个) =================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
]


# ================= 竞品详情 =================
async def get_detail(context, url, rank, my_asin, keyword):
    page = await context.new_page()
    await page.route("**/*.{png,jpg,jpeg,gif,woff,svg}", lambda route: route.abort())
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        # 模拟滚动以触发懒加载
        await page.mouse.wheel(0, 600)
        await asyncio.sleep(2)

        # 1. 标题
        title_el = await page.query_selector('#productTitle')
        title = (await title_el.inner_text()).strip() if title_el else "N/A"

        # 2. 五点描述 (适配 Apparel 类目)
        bullets = []
        selectors = [
            '#feature-bullets ul li span.a-list-item',
            '#productFactsDesktopExpander ul li span.a-list-item',
            '#featurebullets_feature_div ul li span.a-list-item'
        ]
        for s in selectors:
            els = await page.query_selector_all(s)
            for el in els:
                t = (await el.inner_text()).strip()
                if len(t) > 15: bullets.append(t)
            if bullets: break

        final_bullets_list = list(dict.fromkeys(bullets))

        # 3. 评论抓取
        reviews = []
        rev_els = await page.query_selector_all('span[data-hook="review-body"] span')
        for el in rev_els:
            rev_text = (await el.inner_text()).strip()
            if len(rev_text) > 20:
                reviews.append(rev_text.replace('\n', ' '))

        final_reviews_list = list(dict.fromkeys(reviews))

        print(
            f"   ∟ [验证] ASIN: {url.split('/')[-1]} | 标题: {title[:20]}... | 五点: {len(final_bullets_list)}条 | 评论: {len(final_reviews_list)}条")

        await page.close()
        return {
            "我的ASIN": my_asin,
            "搜索关键词": keyword,
            "竞品排名": rank,
            "竞品ASIN": url.split('/')[-1],
            "竞品标题": title,
            "竞品五点": " | ".join(final_bullets_list),
            "竞品评论": " || ".join(final_reviews_list[:5]),
            "竞品链接": url
        }
    except Exception as e:
        print(f"   ∟ [详情失败] {e}")
        if not page.is_closed(): await page.close()
        return None


# ================= 身份管理 =================
async def ensure_amazon_identity(ctx):
    if os.path.exists(STORAGE_FILE): return
    page = await ctx.new_page()
    print("🟡 请手动确认地址为 10115 Berlin，完成后在终端按回车...")
    await page.goto("https://www.amazon.de/", wait_until="domcontentloaded")
    await asyncio.get_event_loop().run_in_executor(None, input, "设置好后请按回车...")
    await ctx.storage_state(path=STORAGE_FILE)
    print("✅ 身份已保存")
    await page.close()


# ================= 主流程 =================
async def main():
    if not os.path.exists(INPUT_FILE): return
    df_input = pd.read_excel(INPUT_FILE)
    all_data = []
    processed_tasks = set()

    if os.path.exists(OUTPUT_FILE):
        try:
            df_exist = pd.read_excel(OUTPUT_FILE)
            processed_tasks = set(df_exist['我的ASIN'].astype(str) + df_exist['搜索关键词'].astype(str))
            all_data = df_exist.to_dict('records')
        except:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])

        async def create_ctx():
            ctx = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=random.choice(USER_AGENTS),
                locale="de-DE",
                storage_state=STORAGE_FILE if os.path.exists(STORAGE_FILE) else None
            )
            stealth = getattr(playwright_stealth, 'stealth_async', None) or getattr(playwright_stealth, 'stealth', None)
            if stealth: await stealth(ctx)
            return ctx

        context = await create_ctx()
        await ensure_amazon_identity(context)

        product_count = 0
        for _, row in df_input.iterrows():
            product_count += 1
            if product_count > RESTART_CONTEXT_THRESHOLD:
                print(f"🧹 周期性更换环境 (UA: {random.choice(USER_AGENTS)[:30]}...)")
                await context.close()
                context = await create_ctx()
                product_count = 1

            my_asin = str(row['ASIN'])
            keywords = [str(row.get(f'关键词{i}', '')) for i in range(1, 4)]

            for i, kw in enumerate(keywords):
                if kw in ['', 'nan', 'None']: continue
                display_kw = f"[词{i + 1}] {kw}"
                if my_asin + display_kw in processed_tasks: continue

                print(f"🚀 处理: {my_asin} -> {display_kw}")
                search_page = await context.new_page()
                try:
                    search_url = f"https://www.amazon.de/s?k={kw.replace(' ', '+')}"
                    await search_page.goto(search_url, wait_until="domcontentloaded")

                    if "gp/browse" in search_page.url or await search_page.query_selector('.bxc-grid__content'):
                        search_box = await search_page.wait_for_selector('#twotabsearchtextbox')
                        await search_box.fill(kw)
                        await search_box.press("Enter")

                    await search_page.wait_for_selector('div[data-asin]', timeout=15000)
                    items = await search_page.query_selector_all('div[data-asin]')
                    asins = [await item.get_attribute('data-asin') for item in items[:20] if
                             await item.get_attribute('data-asin')]
                    await search_page.close()

                    for rank, asin in enumerate(asins, start=1):
                        res = await get_detail(context, f"https://www.amazon.de/dp/{asin}", rank, my_asin, display_kw)
                        if res:
                            all_data.append(res)
                            pd.DataFrame(all_data).to_excel(OUTPUT_FILE, index=False)
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception as e:
                    print(f"❌ 搜索失败: {e}")
                    if not search_page.is_closed(): await search_page.close()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())