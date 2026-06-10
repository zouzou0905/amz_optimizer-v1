import asyncio
import random
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

try:
    import playwright_stealth

    STEALTH_AVAILABLE = True
except ImportError:
    playwright_stealth = None
    STEALTH_AVAILABLE = False

try:
    from scripts import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

from config import STAGE2_OUTPUT_FILE, STAGE3_OUTPUT_FILE
from core.market import get_market_config, normalize_market


RESTART_CONTEXT_THRESHOLD = 5
FAILURE_THRESHOLD = 3
MAX_COMPETITORS_PER_KEYWORD = 20

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]


async def ensure_amazon_identity(context, market_config, market):
    state_file = Path(market_config["state_file"])
    if state_file.exists():
        return

    page = await context.new_page()
    try:
        print(
            f"首次初始化 {market} 市场，请在浏览器中将 {market_config['domain']} "
            f"配送地址设置为 {market_config['zip']}。"
        )
        await page.goto(f"https://{market_config['domain']}/", wait_until="domcontentloaded")
        await asyncio.get_event_loop().run_in_executor(None, input, "地址设置完成后按回车继续...")
        await context.storage_state(path=str(state_file))
        print(f"{market} 市场状态已保存: {state_file}")
    finally:
        await page.close()


async def get_detail(context, url, rank, my_asin, keyword):
    page = await context.new_page()
    await page.route("**/*.{png,jpg,jpeg,gif,woff,woff2,svg}", lambda route: route.abort())

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.mouse.wheel(0, random.randint(400, 900))
        await asyncio.sleep(random.uniform(2, 4))

        title = await read_first_text(page, ["#productTitle"])
        bullets = await read_many_text(
            page,
            [
                "#feature-bullets ul li span.a-list-item",
                "#productFactsDesktopExpander ul li span.a-list-item",
                "#featurebullets_feature_div ul li span.a-list-item",
            ],
            min_length=15,
        )
        reviews = await read_many_text(page, ["span[data-hook='review-body'] span"], min_length=20)

        print(
            f"竞品 {rank}: {url.split('/dp/')[-1]} | 标题: {title[:20]} | "
            f"五点: {len(bullets)} | 评论: {len(reviews)}"
        )

        return {
            "data": {
                "我的ASIN": my_asin,
                "搜索关键词": keyword,
                "竞品排名": rank,
                "竞品ASIN": url.split("/dp/")[-1].split("/")[0],
                "竞品标题": title,
                "竞品五点": " | ".join(bullets),
                "竞品评论": " || ".join(reviews[:5]),
                "竞品链接": url,
            },
            "is_restricted": not bullets and not reviews,
        }
    except Exception as exc:
        print(f"详情页采集失败: {url} | {exc}")
        return None
    finally:
        if not page.is_closed():
            await page.close()


async def read_first_text(page, selectors):
    for selector in selectors:
        element = await page.query_selector(selector)
        if element:
            text = (await element.inner_text()).strip()
            if text:
                return text
    return "N/A"


async def read_many_text(page, selectors, min_length=0):
    results = []
    for selector in selectors:
        elements = await page.query_selector_all(selector)
        for element in elements:
            text = (await element.inner_text()).strip().replace("\n", " ")
            if len(text) >= min_length:
                results.append(text)
        if results:
            break
    return list(dict.fromkeys(results))


async def run(market="UK", input_file=STAGE2_OUTPUT_FILE, output_file=STAGE3_OUTPUT_FILE, headless=False):
    market = normalize_market(market)
    market_config = get_market_config(market)
    input_file = Path(input_file)
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not input_file.exists():
        raise FileNotFoundError(f"找不到 Stage 3 输入文件: {input_file}")

    df_input = pd.read_excel(input_file)
    all_data = []
    processed_tasks = set()

    if output_file.exists():
        existing = pd.read_excel(output_file)
        if not existing.empty and {"我的ASIN", "搜索关键词"}.issubset(existing.columns):
            processed_tasks = set(existing["我的ASIN"].astype(str) + existing["搜索关键词"].astype(str))
            all_data = existing.to_dict("records")
            print(f"检测到历史数据，跳过 {len(processed_tasks)} 个已完成任务。")

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        async def create_context():
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                locale=market_config["locale"],
                storage_state=market_config["state_file"] if Path(market_config["state_file"]).exists() else None,
            )
            if STEALTH_AVAILABLE:
                stealth_fn = getattr(playwright_stealth, "stealth_async", None) or getattr(playwright_stealth, "stealth", None)
                if stealth_fn:
                    await stealth_fn(context)
            return context

        context = await create_context()
        await ensure_amazon_identity(context, market_config, market)

        product_count = 0
        consecutive_empty = 0

        for _, row in df_input.iterrows():
            my_asin = str(row["ASIN"])
            keywords = [str(row.get(f"关键词{i}", "")).strip() for i in range(1, 4)]

            for keyword_index, keyword in enumerate(keywords, start=1):
                if keyword in ("", "nan", "None"):
                    continue

                display_keyword = f"[词{keyword_index}] {keyword}"
                if my_asin + display_keyword in processed_tasks:
                    continue

                product_count += 1
                if product_count > RESTART_CONTEXT_THRESHOLD:
                    await context.close()
                    await asyncio.sleep(10)
                    context = await create_context()
                    product_count = 1

                print(f"处理: {my_asin} -> {display_keyword}")
                competitor_asins = await search_competitors(context, market_config["domain"], keyword)

                for rank, asin in enumerate(competitor_asins, start=1):
                    detail_url = f"https://{market_config['domain']}/dp/{asin}"
                    detail = await get_detail(context, detail_url, rank, my_asin, display_keyword)
                    if not detail:
                        continue

                    consecutive_empty = consecutive_empty + 1 if detail["is_restricted"] else 0
                    all_data.append(detail["data"])
                    pd.DataFrame(all_data).to_excel(output_file, index=False)

                    if consecutive_empty >= FAILURE_THRESHOLD:
                        await context.close()
                        await asyncio.sleep(30)
                        context = await create_context()
                        consecutive_empty = 0
                        product_count = 1

                    await asyncio.sleep(random.uniform(4.0, 7.0))

        await browser.close()
    print(f"Stage 3 完成，输出文件: {output_file}")


async def search_competitors(context, domain, keyword):
    page = await context.new_page()
    try:
        search_url = f"https://{domain}/s?k={keyword.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(random.uniform(2, 4))

        if "gp/browse" in page.url or await page.query_selector(".bxc-grid__content"):
            search_box = await page.wait_for_selector("#twotabsearchtextbox")
            await search_box.fill(keyword)
            await search_box.press("Enter")
            await asyncio.sleep(3)

        await page.wait_for_selector(".s-result-item[data-asin]", timeout=15000)
        items = await page.query_selector_all(".s-result-item[data-asin]")

        asins = []
        for item in items:
            asin = await item.get_attribute("data-asin")
            if asin and len(asin) == 10:
                asins.append(asin)

        unique_asins = list(dict.fromkeys(asins))[:MAX_COMPETITORS_PER_KEYWORD]
        print(f"关键词 {keyword} 提取到 {len(unique_asins)} 个竞品 ASIN。")
        return unique_asins
    except Exception as exc:
        print(f"搜索失败: {keyword} | {exc}")
        return []
    finally:
        if not page.is_closed():
            await page.close()


async def main():
    await run()


if __name__ == "__main__":
    asyncio.run(main())
