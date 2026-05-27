import json
import os
import re
import time

import pandas as pd
from openai import OpenAI

from config import BRAND_NAME, CATEGORIES_DIR, DEEPSEEK_API_KEY, DEEPSEEK_MODEL, STAGE2_OUTPUT_FILE
from core.market import normalize_market


KEYWORD_PROMPTS = {
    "UK": {
        "system": (
            "You are a senior Amazon UK SEO keyword analyst. "
            "You understand English product titles and Amazon UK shopper search behavior. "
            "Return only valid JSON."
        ),
        "user_template": """
Analyze this Amazon product title semantically and extract exactly 3 search keywords for Amazon UK.

Product title:
{title}

Brand to exclude:
{brand_name}

Rules:
1. Output exactly 3 keywords.
2. Each keyword must be in English.
3. Each keyword should be a natural Amazon search phrase, preferably 2-4 words.
4. Focus on buyer search intent: product type, core attribute, use case, material, or compatibility.
5. Do not include brand names, model numbers, sizes, colors, exaggerated marketing words, punctuation, or duplicate meanings.
6. Do not write explanations.

Return this exact JSON shape:
{{"keywords":["keyword 1","keyword 2","keyword 3"]}}
""",
    },
    "DE": {
        "system": (
            "Du bist ein erfahrener Amazon.de SEO Keyword-Analyst. "
            "Du verstehst deutsche und englische Produkttitel und deutsches Suchverhalten auf Amazon.de. "
            "Antworte ausschließlich mit gültigem JSON."
        ),
        "user_template": """
Analysiere diesen Amazon-Produkttitel semantisch und extrahiere genau 3 Suchbegriffe für Amazon.de.

Produkttitel:
{title}

Marke ausschließen:
{brand_name}

Regeln:
1. Gib genau 3 Keywords aus.
2. Jedes Keyword muss auf Deutsch sein.
3. Jedes Keyword soll ein natürlicher Amazon-Suchbegriff sein, idealerweise 2-4 Wörter.
4. Konzentriere dich auf Suchintention: Produkttyp, wichtigste Eigenschaft, Anwendung, Material oder Kompatibilität.
5. Keine Markennamen, Modellnummern, Größen, Farben, übertriebene Werbewörter, Satzzeichen oder doppelte Bedeutungen.
6. Keine Erklärungen schreiben.

Gib exakt dieses JSON-Format zurück:
{{"keywords":["Keyword 1","Keyword 2","Keyword 3"]}}
""",
    },
}


class CategoryOrganizer:
    def __init__(
        self,
        input_path,
        output_path=None,
        brand_name=BRAND_NAME,
        market="UK",
        use_ai=True,
    ):
        self.input_path = input_path
        self.output_path = output_path or STAGE2_OUTPUT_FILE
        self.brand_name = brand_name
        self.market = normalize_market(market)
        self.use_ai = use_ai
        self.client = self._make_client() if use_ai and DEEPSEEK_API_KEY else None
        os.makedirs(CATEGORIES_DIR, exist_ok=True)

    def _make_client(self):
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    def _extract_keywords_by_rules(self, title):
        title_str = str(title)
        clean_title = re.sub(rf"{re.escape(self.brand_name)}", "", title_str, flags=re.IGNORECASE)
        clean_title = re.sub(r"[\[\]()/|:;，。！？、]", ",", clean_title)
        clean_title = clean_title.strip().strip(",")
        parts = [part.strip(" -_") for part in clean_title.split(",") if part.strip()]

        while len(parts) < 3:
            parts.append("")
        return parts[:3]

    def _extract_keywords_by_ai(self, title):
        if not self.client:
            return None

        prompt_config = KEYWORD_PROMPTS[self.market]
        user_prompt = prompt_config["user_template"].format(
            title=str(title),
            brand_name=self.brand_name,
        )

        for attempt in range(1, 4):
            try:
                response = self.client.chat.completions.create(
                    model=DEEPSEEK_MODEL,
                    messages=[
                        {"role": "system", "content": prompt_config["system"]},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content.strip()
                data = json.loads(content)
                keywords = data.get("keywords", [])
                keywords = [str(item).strip() for item in keywords if str(item).strip()]
                if len(keywords) >= 3:
                    return keywords[:3]
            except Exception as exc:
                wait_seconds = attempt * 3
                print(f"AI 提词失败，第 {attempt} 次重试: {exc}")
                time.sleep(wait_seconds)
        return None

    def _extract_keywords(self, title):
        if not self.use_ai:
            return self._extract_keywords_by_rules(title), "规则切割"

        ai_keywords = self._extract_keywords_by_ai(title)
        if ai_keywords:
            return ai_keywords, "AI"

        fallback_reason = "AI不可用" if not self.client else "AI失败后兜底"
        return self._extract_keywords_by_rules(title), fallback_reason

    def organize(self):
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(f"找不到输入文件: {self.input_path}")

        if self.use_ai and not DEEPSEEK_API_KEY:
            print("未设置 DEEPSEEK_API_KEY，Stage 2 将使用规则切割兜底。")
        elif self.use_ai:
            print(f"Stage 2 使用 DeepSeek 语义提词，市场: {self.market}")
        else:
            print("Stage 2 使用本地规则切割。")

        df = pd.read_excel(self.input_path)
        if "标题" not in df.columns:
            raise ValueError("输入文件缺少必要列: 标题")

        df = self._load_checkpoint(df)
        self._ensure_output_columns(df)

        processed_count = 0
        skipped_count = 0
        for index, row in df.iterrows():
            if self._has_keywords(row):
                skipped_count += 1
                print(
                    f"Stage 2 第 {index + 1}/{len(df)} 行 [跳过已有]: "
                    f"{row['关键词1']} | {row['关键词2']} | {row['关键词3']}"
                )
                continue

            keywords, source = self._extract_keywords(row["标题"])
            df.loc[index, "关键词1"] = keywords[0]
            df.loc[index, "关键词2"] = keywords[1]
            df.loc[index, "关键词3"] = keywords[2]
            df.loc[index, "_error"] = "" if source == "AI" else source
            processed_count += 1

            print(
                f"Stage 2 第 {index + 1}/{len(df)} 行 [{source}]: "
                f"{keywords[0]} | {keywords[1]} | {keywords[2]}"
            )
            self._save(df)

        df["类目"] = "Processed_Task"
        self._save(df)
        print(
            f"Stage 2 完成。新增处理: {processed_count} 行，"
            f"跳过已有: {skipped_count} 行。"
        )
        print(f"关键词分析表已生成: {self.output_path}")

    def _load_checkpoint(self, df):
        if not os.path.exists(self.output_path):
            return df

        try:
            existing = pd.read_excel(self.output_path)
        except Exception as exc:
            print(f"读取历史结果失败，将重新处理: {exc}")
            return df

        if "ASIN" not in existing.columns or "ASIN" not in df.columns:
            print("历史结果缺少 ASIN 列，无法断点续跑，将重新处理。")
            return df

        merge_columns = ["ASIN", "关键词1", "关键词2", "关键词3", "_error"]
        for column in merge_columns:
            if column not in existing.columns:
                existing[column] = ""

        merged = df.merge(
            existing[merge_columns],
            on="ASIN",
            how="left",
            suffixes=("", "_checkpoint"),
        )

        for column in ["关键词1", "关键词2", "关键词3", "_error"]:
            checkpoint_col = f"{column}_checkpoint"
            if checkpoint_col in merged.columns:
                if column not in merged.columns:
                    merged[column] = ""
                merged[column] = merged[column].where(
                    self._series_has_value(merged[column]),
                    merged[checkpoint_col],
                )
                merged.drop(columns=[checkpoint_col], inplace=True)

        restored = sum(1 for _, row in merged.iterrows() if self._has_keywords(row))
        print(f"检测到历史 Stage 2 输出，已恢复 {restored} 行关键词。")
        return merged

    def _ensure_output_columns(self, df):
        final_columns = ["标题", "ASIN", "产品链接", "图片链接", "类目", "关键词1", "关键词2", "关键词3"]
        for column in final_columns + ["_error"]:
            if column not in df.columns:
                df[column] = ""

    def _save(self, df):
        self._ensure_output_columns(df)
        final_columns = [
            "标题",
            "ASIN",
            "产品链接",
            "图片链接",
            "类目",
            "关键词1",
            "关键词2",
            "关键词3",
            "_error",
        ]
        df[final_columns].to_excel(self.output_path, index=False)

    @staticmethod
    def _has_keywords(row):
        return all(str(row.get(column, "")).strip() not in ("", "nan", "None") for column in ["关键词1", "关键词2", "关键词3"])

    @staticmethod
    def _series_has_value(series):
        return ~series.fillna("").astype(str).str.strip().isin(["", "nan", "None"])
