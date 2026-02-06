
import os
import pandas as pd
import re


class CategoryOrganizer:
    def __init__(self, api_key, input_path):
        self.input_path = input_path
        self.output_dir = 'data/categories'
        # 设定要排除的品牌词
        self.brand_name = "ALLY-MAGIC"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _extract_keywords(self, title):
        """
        核心逻辑：
        1. 彻底剔除品牌词。
        2. 按逗号分割，取前三个。
        """
        title_str = str(title)

        # 1. 强力剔除：不分大小写，同时处理前后可能的空格
        # 使用正则表达式，确保即便品牌词后面连着逗号也能被识别
        clean_title = re.sub(rf'{self.brand_name}', '', title_str, flags=re.IGNORECASE).strip()

        # 2. 清理首尾可能残留的逗号或多余空格
        clean_title = clean_title.strip(',').strip()

        # 3. 按逗号分割
        parts = [p.strip() for p in clean_title.split(',') if p.strip()]

        # 4. 补齐 3 个占位符
        while len(parts) < 3:
            parts.append("")

        return parts[:3]

    def _get_local_category(self, title):
        """本地分类词库"""
        taxonomy = {
            'Hardware_Metal': ['schraub', 'mutter', 'nagel', 'bolzen', 'stahl', 'metall', 'platte', 'blech', 'eisen'],
            'Home_Garden': ['küche', 'tisch', 'matte', 'garten', 'deko', 'zaun', 'regal'],
            'Tools_Industrial': ['werkzeug', 'zange', 'bohrer', 'adapter', 'halter', 'schiene'],
            'Apparel': ['socken', 'strumpf', 'bekleidung', 'hose', 'shirt']
        }
        t_low = str(title).lower()
        for cat, keywords in taxonomy.items():
            if any(k in t_low for k in keywords):
                return cat
        return "Other_Unclassified"

    def organize(self):
        if not os.path.exists(self.input_path):
            print(f"❌ 找不到文件: {self.input_path}")
            return

        # 读取数据
        df = pd.read_excel(self.input_path)
        print(f"🚀 正在清洗品牌词并提取关键词...")

        # 1. 分类
        df['类目'] = df['标题'].apply(self._get_local_category)

        # 2. 提取关键词列 (修正了 AttributeError)
        kw_res = df['标题'].apply(self._extract_keywords)
        df['关键词1'] = kw_res.apply(lambda x: x[0])
        df['关键词2'] = kw_res.apply(lambda x: x[1])
        df['关键词3'] = kw_res.apply(lambda x: x[2])

        # 3. 按类目生成表格
        for cat, group in df.groupby('类目'):
            safe_cat = "".join([c for c in cat if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
            file_path = os.path.join(self.output_dir, f"{safe_cat}_分析表.xlsx")

            # --- 修改部分：加入 [产品链接] 并调整顺序 ---
            # 顺序为：标题 -> ASIN -> 产品链接 -> 类目 -> 关键词123
            final_columns = ['标题', 'ASIN', '产品链接', '图片链接', '类目', '关键词1', '关键词2', '关键词3']

            # 确保列都存在
            for col in final_columns:
                if col not in group.columns:
                    group[col] = ""

            # 只写入需要的列
            group[final_columns].to_excel(file_path, index=False)
            print(f"📂 已生成: {file_path}")

        print("\n✨ 处理完成！请检查分类文件夹。")