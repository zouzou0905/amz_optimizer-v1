import os
import pandas as pd
from core.scraper import AmazonSpider
from core.data_handler import DataHandler


class AmazonApp:
    def __init__(self, config):
        self.config = config
        self.input_path = config['input_file']
        self.output_path = config['output_file']

        # 核心逻辑：如果 output 已经有文件了，说明我们要“续写”它
        if os.path.exists(self.output_path):
            self.current_working_file = self.output_path
            print(f"📊 检测到已存在进度文件，将在其基础上继续...")
        else:
            self.current_working_file = self.input_path
            print(f"📄 未发现结果文件，将从原始输入文件开始...")

        self.handler = DataHandler(self.current_working_file, self.output_path)
        self.spider = None

    def run(self):
        try:
            df = self.handler.load_data()

            # 确保列都存在，不存在则新建
            if '标题' not in df.columns: df['标题'] = None
            if '图片链接' not in df.columns: df['图片链接'] = None

            # 筛选出还没抓过的行
            mask = df['标题'].isna() | (df['标题'] == '') | (df['标题'] == '抓取失败')
            todo_indices = df[mask].index.tolist()

            if not todo_indices:
                print("✨ 所有数据已抓取。")
                return

            print(f"🚀 准备补全 {len(todo_indices)} 条数据及图片...")
            self.spider = AmazonSpider(headless=self.config['headless'])

            for index in todo_indices:
                url = df.loc[index, '产品链接']
                res = self.spider.fetch_product_data(url)

                # 分两次保存：一次标题，一次图片链接
                self.handler.save_step(index, '标题', res['title'])
                self.handler.save_step(index, '图片链接', res['image_url'])

                print(f"✅ 已保存第 {index + 1} 行 | 标题预览: {res['title'][:10]}...")

        except Exception as e:
            print(f"❌ 运行异常: {e}")
        finally:
            if self.spider:
                self.spider.close()