import os
import asyncio
import json
import re
import pandas as pd
from openai import OpenAI

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    AI_ANALYZER_INPUT,
    AI_ANALYZER_OUTPUT,
)

# 1. 初始化客户端，彻底去除 Key 前后的不可见字符
client = OpenAI(api_key=DEEPSEEK_API_KEY.strip(), base_url="https://api.deepseek.com")


async def get_ai_response(prompt, asin):
    """
    带重试和指数退避逻辑的 API 调用函数
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            def _call():
                return client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": "Du bist ein Amazon SEO Experte. Antworte NUR im JSON-Format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    # 如果报错，请尝试将下面这行注释掉
                    response_format={"type": "json_object"}
                )

            resp = await asyncio.to_thread(_call)
            content = resp.choices[0].message.content.strip()

            # 增强型 JSON 提取逻辑
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(content)

        except Exception as e:
            if "Authentication" in str(e):
                print(f"🔑 ASIN {asin}: API Key 验证失败，请检查 config.py")
                break

            wait_time = (attempt + 1) * 5  # 失败后多等一会儿，避开流量控制
            print(f"⚠️ ASIN {asin} 尝试 {attempt + 1} 失败: {e}. {wait_time}s 后重试...")
            await asyncio.sleep(wait_time)

    return None


async def main():
    if not os.path.exists(AI_ANALYZER_INPUT):
        print(f"❌ 找不到输入文件: {AI_ANALYZER_INPUT}")
        return

    print(f"📊 正在加载类目数据表...")
    df = pd.read_excel(AI_ANALYZER_INPUT)
    unique_asins = df['我的ASIN'].unique()

    insight_results = []

    # --- 阶段 A：生成素材库并聚合 ---
    print(f"🤖 共有 {len(unique_asins)} 个产品待分析，共计约 {len(df)} 条竞品素材。")

    for asin in unique_asins:
        print(f"🔍 正在为 ASIN {asin} 聚合 60 个竞品的深度数据...")
        group = df[df['我的ASIN'] == asin]

        # 聚合数据
        titles_pool = " | ".join(group['竞品标题'].dropna().unique().tolist()[:15])
        comment_col = next((col for col in group.columns if '评论' in col), None)
        reviews_pool = ""
        if comment_col:
            reviews_pool = " || ".join([str(x)[:200] for x in group[comment_col].dropna().unique().tolist()[:25]])

        # --- 深度优化后的 Prompt ---
        prompt = f"""
            Du bist ein Senior Amazon Strategist für den deutschen Markt. Analysiere das Wettbewerbsumfeld für ASIN: {asin}.

            DATENBASIS:
            - Wettbewerber-Titel (Markttrends & SEO-Fokus): {titles_pool}
            - Kundenrezensionen (Echte Pain Points & Erwartungen): {reviews_pool}

            AUFGABE:
            Führe eine tiefgreifende Analyse durch und gib ein JSON-Objekt mit folgenden Feldern zurück:

            1. core_keywords: Identifiziere nicht nur einfache Begriffe, sondern die "High-Conversion-Keywords", die alle Top-Wettbewerber gemeinsam haben.
            2. pain_points: Analysiere die Rezensionen tiefgreifend. Was sind die emotionalen oder funktionalen Enttäuschungen der Kunden? (z.B. Materialqualität, Passform-Lügen, irreführende Bilder).
            3. bad_keyword_diag: Welche Begriffe in aktuellen Titeln sind "Füllwörter" ohne Ranking-Kraft? Welche Nischen-Keywords werden ignoriert?
            4. optimized_title: Erstelle einen verkaufsstarken Titel (max. 150 Zeichen). Er muss das Haupt-Keyword, ein emotionales Benefit und ein technisches Alleinstellungsmerkmal enthalten.
            5. product_improvement_suggestions: (NEU) Basierend auf den Schwächen der Konkurrenz, welche konkreten Änderungen am Produkt oder am Set-Inhalt würden uns einen unfairen Vorteil verschaffen? (z.B. Verstärkte Naht, umweltfreundliche Verpackung, Beigabe eines E-Books/Zubehörs).
            """

        # --- 阶段 B：调用 AI 引擎 ---
        report = await get_ai_response(prompt, asin)

        if report:
            report['我的ASIN'] = asin
            # 确保新增列在字典中存在，防止 AI 返回字段缺失
            if 'product_improvement_suggestions' not in report:
                report['product_improvement_suggestions'] = "Keine spezifischen Vorschläge verfügbar."
            insight_results.append(report)
        else:
            insight_results.append({
                "我的ASIN": asin,
                "optimized_title": "分析失败",
                "product_improvement_suggestions": "N/A"
            })

        await asyncio.sleep(2)  # 强制间隔，确保不被 Governor 踢掉

    # --- 阶段 C：保存“人机交互表”与“素材备份” ---
    insight_df = pd.DataFrame(insight_results)

    # 交互表：结论
    insight_df.to_excel(AI_ANALYZER_OUTPUT, index=False)

    # 全量表：明细 + 对应结论
    full_output = str(AI_ANALYZER_OUTPUT).replace(".xlsx", "_DEBUG_FULL.xlsx")
    full_df = pd.merge(df, insight_df, on="我的ASIN", how="left")
    full_df.to_excel(full_output, index=False)

    print(f"✅ 处理完成！")
    print(f"📂 策略结论已保存（建议阅读）: {AI_ANALYZER_OUTPUT}")
    print(f"📂 原始明细已备份（供查证据）: {full_output}")


if __name__ == "__main__":
    asyncio.run(main())