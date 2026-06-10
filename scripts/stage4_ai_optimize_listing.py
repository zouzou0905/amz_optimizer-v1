import asyncio
import json
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


MAX_RETRIES = 3
REQUIRED_RESPONSE_FIELDS = {
    "core_keywords",
    "niche_gems",
    "selling_points",
    "pain_points",
    "optimized_title",
}


async def get_ai_response(client, market_config, prompt, asin):
    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):
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
            report = json.loads(json_match.group() if json_match else content)

            missing_fields = REQUIRED_RESPONSE_FIELDS - set(report)
            if missing_fields:
                raise ValueError(f"AI 返回缺少字段: {', '.join(sorted(missing_fields))}")

            return report, "", attempt
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            print(f"ASIN {asin} 第 {attempt}/{MAX_RETRIES} 次分析失败: {last_error}")

            if attempt < MAX_RETRIES:
                wait_time = attempt * 5
                print(f"{wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)

    return None, last_error, MAX_RETRIES


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

    results_by_asin = load_existing_results(output_file)
    successful_asins = {
        asin
        for asin, row in results_by_asin.items()
        if row.get("分析状态") == "成功"
    }

    if successful_asins:
        print(f"检测到 {len(successful_asins)} 个成功结果，将直接跳过。")

    failed_history = {
        asin
        for asin, row in results_by_asin.items()
        if row.get("分析状态") == "失败"
    }
    if failed_history:
        print(f"检测到 {len(failed_history)} 个历史失败结果，本次将重新分析。")

    for asin in df["我的ASIN"].dropna().astype(str).unique():
        if asin in successful_asins:
            print(f"ASIN {asin} [跳过成功记录]")
            continue

        group = df[df["我的ASIN"].astype(str) == asin]
        prompt = build_prompt(market_config, asin, group)
        print(f"正在分析 {market} 市场 ASIN: {asin}")

        report, error_message, attempts = await get_ai_response(
            client,
            market_config,
            prompt,
            asin,
        )

        results_by_asin[asin] = build_result_row(
            market_config=market_config,
            asin=asin,
            report=report,
            error_message=error_message,
            attempts=attempts,
        )
        save_results(df, results_by_asin, output_file)

        if report:
            print(f"ASIN {asin} [分析成功]，尝试次数: {attempts}")
        else:
            print(f"ASIN {asin} [分析失败]，错误已记录，下次运行会继续重试。")

        await asyncio.sleep(2)

    print(f"Stage 4 完成，输出文件: {output_file}")


def load_existing_results(output_file):
    if not output_file.exists():
        return {}

    try:
        existing = pd.read_excel(output_file)
    except Exception as exc:
        print(f"读取历史 Stage 4 结果失败，将重新开始: {exc}")
        return {}

    if existing.empty or "我的ASIN" not in existing.columns:
        return {}

    if "分析状态" not in existing.columns:
        existing["分析状态"] = existing.apply(infer_legacy_status, axis=1)

    return {
        str(row["我的ASIN"]): row.to_dict()
        for _, row in existing.iterrows()
    }


def infer_legacy_status(row):
    title_columns = [
        column
        for column in row.index
        if str(column).startswith("AI优化标题")
    ]
    if not title_columns:
        return "失败"

    value = str(row.get(title_columns[0], "")).strip()
    return "成功" if value not in ("", "nan", "分析失败") else "失败"


def save_results(source_df, results_by_asin, output_file):
    result_df = pd.DataFrame(results_by_asin.values())
    result_df.to_excel(output_file, index=False)

    debug_output = output_file.with_name(f"{output_file.stem}_DEBUG_FULL.xlsx")
    source_copy = source_df.copy()
    source_copy["我的ASIN"] = source_copy["我的ASIN"].astype(str)
    result_df["我的ASIN"] = result_df["我的ASIN"].astype(str)
    pd.merge(source_copy, result_df, on="我的ASIN", how="left").to_excel(
        debug_output,
        index=False,
    )


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


def build_result_row(market_config, asin, report, error_message, attempts):
    suffix = market_config["suffix"]
    result = {
        "我的ASIN": asin,
        "产品链接": f"https://{market_config['domain']}/dp/{asin}",
        "分析状态": "成功" if report else "失败",
        "尝试次数": attempts,
        "错误信息": error_message,
    }

    if not report:
        result[f"AI优化标题{suffix}"] = "分析失败"
        return result

    result.update(
        {
            f"聚合核心词组{suffix}": report["core_keywords"],
            f"高价值利基词/长尾词{suffix}": report["niche_gems"],
            f"核心卖点聚合{suffix}": report["selling_points"],
            "深度痛点挖掘(中文)": report["pain_points"],
            f"AI优化标题{suffix}": report["optimized_title"],
        }
    )
    return result


async def main():
    await run()


if __name__ == "__main__":
    asyncio.run(main())
