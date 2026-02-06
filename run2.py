"""
Stage 2（真实 AI 版）：从“抓取结果_成品.xlsx”基于标题提取 3 个关键词，生成“关键词表.xlsx”

输入：data/output/抓取结果_成品.xlsx（至少包含列：ASIN、标题）
输出：data/output/关键词表.xlsx（列：ASIN、关键词1、关键词2、关键词3）
"""
import asyncio
import os
import time
from typing import Dict

import pandas as pd
from google import genai
from google.genai import types

from config import GEMINI_API_KEY, OUTPUT_DIR, STAGE2_INPUT_FILE


MODEL_ID = "gemini-2.5-flash"
OUTPUT_FILE = os.path.join(str(OUTPUT_DIR), "关键词表.xlsx")
OUTPUT_FILE_AUTOSAVE = os.path.join(str(OUTPUT_DIR), "关键词表_autosave.xlsx")
LOG_FILE = os.path.join(str(OUTPUT_DIR), "run2.log")
CONCURRENT = 1  # 串行最稳，避免限流导致最后几条失败
RETRY_TIMES = 5
REQUEST_DELAY = 1.5  # 每条请求后等待秒数，降低限流


def _normalize_title(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    if s.lower() == "nan" or s.lower() == "none":
        return ""
    return s


def _make_client() -> genai.Client:
    # 这里使用你项目里的 API Key（config.py 已集中管理）
    return genai.Client(api_key=GEMINI_API_KEY)


async def extract_keywords(client: genai.Client, asin: str, title: str) -> Dict[str, str]:
    """
    从标题提取 3 个关键词（德语为主，尽量贴近 Amazon 搜索词）。
    使用结构化输出，确保永远返回 3 个字段。
    """
    prompt = f"""
你是亚马逊德国站（Amazon.de）listing优化专家。
请根据下面的产品标题提取 3 个“搜索关键词”（德语为主），用于在 Amazon.de 搜索竞品。

要求：
1) 关键词必须是短语/词组（1~3 个词为佳），不要句子
2) 避免品牌词、商标、型号、夸张词（如 best, top, premium）
3) 三个关键词尽量互不重复，覆盖不同角度（品类词/核心属性/使用场景）
4) 只输出结构化 JSON（由 schema 约束），不要多余文本

ASIN: {asin}
标题: {title}
"""

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "keyword1": {"type": "STRING"},
            "keyword2": {"type": "STRING"},
            "keyword3": {"type": "STRING"},
        },
        "required": ["keyword1", "keyword2", "keyword3"],
    }

    try:
        last_err = None
        for attempt in range(1, RETRY_TIMES + 1):
            try:
                resp = await client.aio.models.generate_content(
                    model=MODEL_ID,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        response_schema=response_schema,
                    ),
                )
                data = resp.parsed or {}
                return {
                    "关键词1": str(data.get("keyword1", "")).strip(),
                    "关键词2": str(data.get("keyword2", "")).strip(),
                    "关键词3": str(data.get("keyword3", "")).strip(),
                }
            except Exception as e:
                # 常见原因：429/503 限流、网络抖动；做指数退避重试
                last_err = e
                sleep_s = min(2 ** attempt, 30) + (attempt * 0.2)
                await asyncio.sleep(sleep_s)

        raise last_err  # 走到这里说明多次重试仍失败
    except Exception as e:
        # 失败时不要中断整个流程，填空并记录原因
        return {
            "关键词1": "",
            "关键词2": "",
            "关键词3": "",
            "_error": f"{type(e).__name__}: {str(e)[:200]}",
        }


async def main():
    input_path = str(STAGE2_INPUT_FILE)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到输入文件: {input_path}")

    os.makedirs(str(OUTPUT_DIR), exist_ok=True)

    df = pd.read_excel(input_path)
    if "ASIN" not in df.columns:
        raise ValueError("输入表缺少列：ASIN")
    if "标题" not in df.columns:
        raise ValueError("输入表缺少列：标题（请先运行 Stage1 抓取标题）")

    # 输出表：只保留关键词相关字段
    out = pd.DataFrame({"ASIN": df["ASIN"].astype(str)})
    for c in ["关键词1", "关键词2", "关键词3"]:
        if c not in out.columns:
            out[c] = ""
    if "_error" not in out.columns:
        out["_error"] = ""

    # 断点续跑：如果输出文件已存在，则合并已有结果
    if os.path.exists(OUTPUT_FILE):
        try:
            existing = pd.read_excel(OUTPUT_FILE)
            if "ASIN" in existing.columns:
                existing = existing.astype({"ASIN": str})
                out = out.merge(
                    existing[["ASIN", "关键词1", "关键词2", "关键词3"]],
                    on="ASIN",
                    how="left",
                    suffixes=("", "_old"),
                )
                for c in ["关键词1", "关键词2", "关键词3"]:
                    if f"{c}_old" in out.columns:
                        left_val = out[c].astype(str).str.strip()
                        right_val = out[f"{c}_old"].fillna("").astype(str).str.strip()
                        out[c] = left_val.where((left_val != "") & (left_val != "nan"), right_val)
                        out.drop(columns=[f"{c}_old"], inplace=True)
        except Exception:
            pass

    # 统计待处理数量
    todo_mask = pd.Series([True] * len(out))
    for c in ["关键词1", "关键词2", "关键词3"]:
        v = out[c].astype(str).str.strip()
        todo_mask &= (v == "") | (v == "nan")
    todo_mask &= df["标题"].apply(_normalize_title).str.len() > 0
    todo_indices = df.index[todo_mask].tolist()
    todo_count = len(todo_indices)
    skip_count = len(df) - todo_count

    if todo_count == 0:
        print("✨ 所有行已有关键词，无需处理。")
        return

    print(f"📋 总行数: {len(df)}，已跳过: {skip_count}，待处理: {todo_count}")

    client = _make_client()
    sem = asyncio.Semaphore(CONCURRENT)
    write_lock = asyncio.Lock()
    progress_lock = asyncio.Lock()
    done = 0
    fail_count = 0

    async def safe_save():
        """
        避免并发写同一个 xlsx 造成中断：
        - 用 asyncio.Lock 串行写入
        - 若文件被 Excel 占用导致 PermissionError，则写入 autosave 文件
        """
        async with write_lock:
            try:
                out.to_excel(OUTPUT_FILE, index=False)
            except PermissionError:
                out.to_excel(OUTPUT_FILE_AUTOSAVE, index=False)
            except Exception:
                # 有些环境缺少 openpyxl 或遇到写入异常，至少落到 csv 以避免全丢
                out.to_csv(os.path.join(str(OUTPUT_DIR), "关键词表_fallback.csv"), index=False, encoding="utf-8-sig")

    def _log(msg: str):
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            pass

    async def run_one(i: int):
        nonlocal done, fail_count
        try:
            asin = str(df.loc[i, "ASIN"])
            title = _normalize_title(df.loc[i, "标题"])

            if all(str(out.loc[i, c]).strip() not in ("", "nan") for c in ["关键词1", "关键词2", "关键词3"]):
                return
            if not title:
                return

            async with sem:
                res = await extract_keywords(client, asin, title)
                await asyncio.sleep(REQUEST_DELAY)

            for c in ["关键词1", "关键词2", "关键词3"]:
                out.loc[i, c] = res.get(c, "")
            if "_error" in res and res["_error"]:
                out.loc[i, "_error"] = res["_error"]
                fail_count += 1
                err_msg = f"[{time.strftime('%H:%M:%S')}] 失败 行{i+1} ASIN={asin}: {res['_error'][:100]}"
                print(err_msg, flush=True)
                _log(err_msg)
            else:
                out.loc[i, "_error"] = ""

            await safe_save()

            async with progress_lock:
                done += 1
                msg = f"[{time.strftime('%H:%M:%S')}] 进度: {done}/{todo_count}"
                if done == 1 or done % 5 == 0 or done == todo_count:
                    print(msg, flush=True)
                _log(msg)
        except Exception as e:
            try:
                out.loc[i, "_error"] = f"{type(e).__name__}: {str(e)[:200]}"
                fail_count += 1
                err_msg = f"[{time.strftime('%H:%M:%S')}] 异常 行{i+1}: {type(e).__name__}: {str(e)[:150]}"
                print(err_msg, flush=True)
                _log(err_msg)
            except Exception:
                pass

    tasks = [run_one(i) for i in todo_indices]
    await asyncio.gather(*tasks, return_exceptions=True)

    await safe_save()
    ok = todo_count - fail_count
    print(f"✅ 完成！成功: {ok}，失败: {fail_count}，输出: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())

