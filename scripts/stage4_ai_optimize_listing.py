import asyncio
import json
import os
import re
from pathlib import Path

import pandas as pd
from openai import OpenAI

try:
    from scripts import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

from config import AI_ANALYZER_INPUT, AI_ANALYZER_OUTPUT, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from core.market import get_market_config, normalize_market


async def get_ai_response(client, market_config, prompt, asin):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            def call_api():
                return client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"You are a {market_config['expert_role']}. "
                                "Return only valid JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

            response = await asyncio.to_thread(call_api)
            content = response.choices[0].message.content.strip()
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            return json.loads(json_match.group() if json_match else content)
        except Exception as exc:
            wait_time = (attempt + 1) * 5
            print(f"ASIN {asin} 第 {attempt + 1} 次分析失败: {exc}，{wait_time}s 后重试。")
            await asyncio.sleep(wait_time)
    return None


async def run(market="UK", input_file=AI_ANALYZER_INPUT, output_file=AI_ANALYZER_OUTPUT):
    market = normalize_market(market)
    market_config = get_market_config(market)
    input_file = Path(input_file)
    output_file = Path(output_file)

    if not DEEPSEEK_API_KEY:
        raise ValueError("未设置 DEEPSEEK_API_KEY，请先创建 .env。")
    if not input_file.exists():
        raise FileNotFoundError(f"找不到 Stage 4 输入文件: {input_file}")

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    df = pd.read_excel(input_file)

    if "我的ASIN" not in df.columns:
        raise ValueError("Stage 4 输入文件缺少必要列: 我的ASIN")

    insight_results = []
    processed_asins = set()

    if output_file.exists():
        existing = pd.read_excel(output_file)
        if not existing.empty and "我的ASIN" in existing.columns:
            insight_results = existing.to_dict("records")
            processed_asins = set(existing["我的ASIN"].astype(str).unique())
            print(f"检测到历史结果，跳过 {len(processed_asins)} 个已完成 ASIN。")

    for asin in df["我的ASIN"].dropna().astype(str).unique():
        if asin in processed_asins:
            continue

        group = df[df["我的ASIN"].astype(str) == asin]
        prompt = build_prompt(market_config, asin, group)
        print(f"正在分析 {market} 市场 ASIN: {asin}")
        report = await get_ai_response(client, market_config, prompt, asin)

        result = build_result_row(market_config, asin, report)
        insight_results.append(result)

        insight_df = pd.DataFrame(insight_results)
        insight_df.to_excel(output_file, index=False)

        debug_output = str(output_file).replace(".xlsx", "_DEBUG_FULL.xlsx")
        pd.merge(df, insight_df, on="我的ASIN", how="left").to_excel(debug_output, index=False)

        await asyncio.sleep(2)

    print(f"Stage 4 完成，输出文件: {output_file}")


def build_prompt(market_config, asin, group):
    titles_pool = "\n".join(
        f"{index + 1}. {title}"
        for index, title in enumerate(group["竞品标题"].dropna().unique().tolist()[:60])
    )
    bullets_pool = "\n".join(
        f"- {bullet}"
        for bullet in group["竞品五点"].dropna().unique().tolist()[:40]
    )
    reviews_pool = " || ".join(
        str(review)[:200]
        for review in group["竞品评论"].dropna().unique().tolist()[:40]
    )

    instructions = market_config["instructions"]
    return f"""
Analyze the competitive landscape for ASIN: {asin}.

MARKET:
- Domain: {market_config['domain']}
- Target language: {market_config['lang_name']}

DATA:
- Titles:
{titles_pool}

- Bullet points:
{bullets_pool}

- Reviews:
{reviews_pool}

ANALYSIS STEPS:
1. {instructions['step1']}
2. {instructions['step2']}
3. {instructions['step3']}

Return JSON only. JSON requirements: {instructions['json_req']}

JSON schema:
{{
  "core_keywords": "Top keyword phrases",
  "niche_gems": "Specific niche and long-tail phrases",
  "selling_points": "Strongest selling points",
  "pain_points": "客户痛点总结，中文",
  "optimized_title": "Optimized title"
}}
"""


def build_result_row(market_config, asin, report):
    suffix = market_config["suffix"]
    base = {
        "我的ASIN": asin,
        "产品链接": f"https://{market_config['domain']}/dp/{asin}",
    }

    if not report:
        base[f"AI优化标题{suffix}"] = "分析失败"
        return base

    base.update(
        {
            f"聚合核心词组{suffix}": report.get("core_keywords", "N/A"),
            f"高价值利基词/长尾词{suffix}": report.get("niche_gems", "N/A"),
            f"核心卖点聚合{suffix}": report.get("selling_points", "N/A"),
            "深度痛点挖掘(中文)": report.get("pain_points", "N/A"),
            f"AI优化标题{suffix}": report.get("optimized_title", "分析失败"),
        }
    )
    return base


async def main():
    await run()


if __name__ == "__main__":
    asyncio.run(main())
