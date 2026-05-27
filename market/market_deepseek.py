import os
import re
import time
from pathlib import Path

import openai
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
FILE_PATH = PROJECT_ROOT / "market" / "data" / "1.xlsx"
OUTPUT_PATH = PROJECT_ROOT / "market" / "data" / "1_market_report.xlsx"


def _pick_column(df, candidates):
    for name in candidates:
        if name in df.columns:
            return name
    raise KeyError(f"Missing required column. Tried: {', '.join(candidates)}")


def get_first_month(trend_str):
    match = re.search(r"'\d{4}-\d{1,2}'", str(trend_str))
    return match.group().replace("'", "") if match else "Unknown"


def get_last_sales(trend_str):
    nums = re.findall(r"'([\d,]+)'\]$", str(trend_str).strip())
    if nums:
        return float(nums[-1].replace(",", ""))
    return 0


def analyze_full_market_objectively():
    print(f"[{time.strftime('%H:%M:%S')}] Starting market analysis...")

    if not FILE_PATH.exists():
        print(f"Input file not found: {FILE_PATH}")
        return
    if not DEEPSEEK_API_KEY:
        print("DEEPSEEK_API_KEY is not set. Create .env from .env.example first.")
        return

    try:
        df = pd.read_excel(FILE_PATH, engine="openpyxl")
        df.columns = df.columns.str.strip()

        link_col = _pick_column(df, ["产品链接", "商品链接", "链接", "url", "URL"])
        price_col = _pick_column(df, ["价格", "price", "Price"])
        rating_col = _pick_column(df, ["评分", "rating", "Rating"])
        trend_col = _pick_column(df, ["销量趋势", "销售趋势", "trend", "Trend"])

        temp_df = df.copy()
        temp_df["sort_sales"] = temp_df[trend_col].apply(get_last_sales)
        temp_df["start_date"] = temp_df[trend_col].apply(get_first_month)
        temp_df["price_val"] = pd.to_numeric(temp_df[price_col], errors="coerce").fillna(0)
        temp_df["date_dt"] = pd.to_datetime(temp_df["start_date"], errors="coerce")

        total = len(temp_df)
        avg_price = temp_df[temp_df["price_val"] > 0]["price_val"].mean()
        low_price_ratio = (len(temp_df[temp_df["price_val"] < 4.99]) / total) * 100
        new_product_ratio = (
            len(temp_df[temp_df["date_dt"] > (pd.Timestamp.now() - pd.Timedelta(days=365))])
            / total
        ) * 100

        top_samples = temp_df.sort_values(by="sort_sales", ascending=False).head(50)
        sample_list = []
        for _, row in top_samples.iterrows():
            sample_list.append(
                f"Link: {row[link_col]}, Price: {row[price_col]}, Rating: {row[rating_col]}, "
                f"Estimated launch month: {row['start_date']}, Trend: {row[trend_col]}"
            )
        sample_data = "\n".join(sample_list)
    except Exception as exc:
        print(f"Data analysis failed: {exc}")
        return

    system_prompt = (
        "You are a rational Amazon investment analyst. "
        "Your job is to evaluate whether this market is objectively worth entering."
    )
    user_prompt = f"""
# Germany Market Snapshot
- Sample size: {total}
- Average price: EUR {avg_price:.2f}
- Low-price ratio under EUR 4.99: {low_price_ratio:.1f}%
- New product ratio within one year: {new_product_ratio:.1f}%

# Evaluation rules
1. Only mark the market as difficult if low-price competition is severe and there are few new products.
2. Treat recent 3-6 month growth as a positive signal, especially when low-review products enter the top 50.
3. Exclude unsuitable categories such as electronics, liquid products, baby products, apparel, ink, or certification-heavy products.
4. Give an objective recommendation and identify promising links even if the market is difficult overall.

# Output
Start with either "[Can enter]" or "[Difficult]".
Then provide three data-backed reasons.
Finally list up to ten promising product links from the sample.

# Sample data
{sample_data}
"""

    print(f"[{time.strftime('%H:%M:%S')}] Calling DeepSeek...")
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    try:
        response = client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        ai_result = response.choices[0].message.content

        df_final = df.copy()
        df_final["AI_market_report"] = ""
        df_final.at[0, "AI_market_report"] = ai_result
        df_final.to_excel(OUTPUT_PATH, index=False, engine="openpyxl")

        print(f"[{time.strftime('%H:%M:%S')}] Report generated: {OUTPUT_PATH}")
        print(ai_result[:500] + "...")
    except Exception as exc:
        print(f"Run failed: {exc}")


if __name__ == "__main__":
    analyze_full_market_objectively()
