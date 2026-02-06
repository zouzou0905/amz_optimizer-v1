
import pandas as pd
import openai
import os
import time

# ================= 配置区域 =================
DEEPSEEK_API_KEY = "sk-5582911f1b6b4ca49eacd90160223126"
FILE_PATH = r"D:\Python_project\amazon_optimizer\market\data\2.xlsx"
OUTPUT_PATH = r"D:\Python_project\amazon_optimizer\market\data\2_客观选品报告.xlsx"


# ===========================================

def clean_sales(val):
    v = str(val).strip().upper()
    if '<' in v: return 5
    if 'N/A' in v or 'NAN' in v or v == '': return 0
    try:
        return float(v.replace(',', ''))
    except:
        return 0


def analyze_full_market_objectively():
    print(f"[{time.strftime('%H:%M:%S')}] 🚀 启动客观市场评估程序...")

    if not os.path.exists(FILE_PATH):
        print(f"❌ 找不到文件 {FILE_PATH}")
        return

    try:
        df = pd.read_excel(FILE_PATH, engine='openpyxl')
        df.columns = df.columns.str.strip()

        # 数据清洗与预处理
        df['销量_num'] = df['销量'].apply(clean_sales)
        df['价格_num'] = pd.to_numeric(df['价格'], errors='coerce').fillna(0)
        df['时间_dt'] = pd.to_datetime(df['时间'], errors='coerce')

        # 统计全市场宏观数据 (96条数据)
        total = len(df)
        avg_p = df[df['价格_num'] > 0]['价格_num'].mean()
        low_p_ratio = (len(df[df['价格_num'] < 4.99]) / total) * 100
        new_p_ratio = (len(df[df['时间_dt'] > (pd.Timestamp.now() - pd.Timedelta(days=365))]) / total) * 100

        # 选取高销量采样，并包含完整链接
        top_samples = df.sort_values(by='销量_num', ascending=False).head(50)
        sample_data = top_samples[['产品链接', '销量', '时间', '价格', '评价', '月销趋势']].to_string(index=False)

    except Exception as e:
        print(f"❌ 数据分析中断: {e}")
        return

    # --- 核心 Prompt：强调客观与批判性 ---
    system_prompt = "你是一个极度理性的亚马逊投资顾问。你的任务是拆穿市场的虚假繁荣，给出客观、冷酷的选品建议。"
    user_prompt = f"""
# 德国市场客观画像
- 样本总量：{total} 个记录
- 平均售价：€{avg_p:.2f}
- 低价卷度 (€4.99以下)：{low_p_ratio:.1f}%
- 竞争活力 (一年内新品)：{new_p_ratio:.1f}%

# 必须执行的逻辑（客观评价标准）：
1. **生死判定**：
   - **红海判定**：如果“低价卷度” > 35% 且新品占比 < 10%，直接判定为【不好做】。
   - **垄断判定**：如果采样数据中销量前 5 的产品评价均 > 1500 条，判定为【不好做，大卖家墙垒】。
   - **时机判定**：重点看 3-6 月销量。如果 3-6 月销量相对于 1-2 月有 **30% - 50% 的稳健增长**，且新卖家（1年内）能在前 50 名占有一席之地，判定为【能做，有时机】。
   - **爆发判定**：如果 3-6 月销量出现 **100% 以上** 的激增，判定为【能做，季节性极强，需快进快出】。

2. **类目过滤**：严格剔除带电、液体、婴儿、服装、墨水、需认证书的产品。

3. **客观评价**：不需要修辞，直接说该市场的优劣势。

# 输出要求：
1. 结论开头：【能做】或【不好做】。
2. 分析原因：列出 3 条硬性数据理由。
3. 爆款推荐：若【能做】，推荐 10 个以内原样输出的链接（注明当季/过季）；若【不好做】，减少推荐，仅列出极个别差异化链接。

# 采样数据：
{sample_data}
"""

    print(f"[{time.strftime('%H:%M:%S')}] 🧠 AI 正在进行批判性评估...")
    client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        ai_result = response.choices[0].message.content

        # 写回 Excel
        df_final = df.drop(columns=['销量_num', '价格_num', '时间_dt'])
        df_final['AI客观评价报告'] = ""
        df_final.at[0, 'AI客观评价报告'] = ai_result

        df_final.to_excel(OUTPUT_PATH, index=False, engine='openpyxl')
        print(f"[{time.strftime('%H:%M:%S')}] ✅ 报告已生成！请查看: {OUTPUT_PATH}")
        print("\n--- AI 核心结论预览 ---")
        print(ai_result[:500] + "...")  # 终端预览前500字

    except Exception as e:
        print(f"❌ 运行失败: {e}")


if __name__ == "__main__":
    analyze_full_market_objectively()