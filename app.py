import os

from core.data_handler import DataHandler
from core.scraper import AmazonSpider


TITLE_COLUMN = "标题"
IMAGE_COLUMN = "图片链接"
URL_COLUMN = "产品链接"
FAIL_VALUE = "抓取失败"


class AmazonApp:
    def __init__(self, config):
        self.config = config
        self.input_path = config["input_file"]
        self.output_path = config["output_file"]
        self.max_retries = config.get("max_retries", 3)
        self.headless = config.get("headless", False)
        self.locale = config.get("locale", "de-DE")

        if os.path.exists(self.output_path):
            self.current_working_file = self.output_path
            print(f"检测到进度文件，将继续处理: {self.output_path}")
        else:
            self.current_working_file = self.input_path
            print(f"未发现进度文件，将从输入文件开始: {self.input_path}")

        self.handler = DataHandler(self.current_working_file, self.output_path)
        self.spider = None

    def _get_todo_indices(self, df):
        mask = (
            df[TITLE_COLUMN].isna()
            | (df[TITLE_COLUMN] == "")
            | (df[TITLE_COLUMN] == FAIL_VALUE)
        )
        return df[mask].index.tolist()

    def _restart_spider(self):
        if self.spider:
            self.spider.close()
        self.spider = AmazonSpider(headless=self.headless, locale=self.locale)

    def _scrape_batch(self, indices):
        df = self.handler.df
        failed = []

        for offset, index in enumerate(indices, start=1):
            url = df.loc[index, URL_COLUMN]
            res = self.spider.fetch_product_data(url)

            self.handler.save_step(index, TITLE_COLUMN, res["title"])
            self.handler.save_step(index, IMAGE_COLUMN, res["image_url"])

            if res["title"] == FAIL_VALUE:
                failed.append(index)
                print(f"第 {index + 1} 行抓取失败 ({offset}/{len(indices)})")
            else:
                preview = res["title"][:40]
                print(f"第 {index + 1} 行抓取成功: {preview}... ({offset}/{len(indices)})")

        return failed

    def run(self):
        try:
            df = self.handler.load_data()
            self._ensure_columns(df)

            todo_indices = self._get_todo_indices(df)
            if not todo_indices:
                print("所有数据已抓取，无需处理。")
                return

            print(f"准备抓取 {len(todo_indices)} 条商品数据。")
            self._restart_spider()
            failed_indices = self._scrape_batch(todo_indices)

            retry_round = 1
            while failed_indices and retry_round < self.max_retries:
                retry_round += 1
                print(f"第 {retry_round} 轮重试，剩余 {len(failed_indices)} 条。")
                self._restart_spider()
                failed_indices = self._scrape_batch(failed_indices)

            if failed_indices:
                print(f"仍有 {len(failed_indices)} 条抓取失败:")
                for idx in failed_indices:
                    print(f"第 {idx + 1} 行: {df.loc[idx, URL_COLUMN]}")
            else:
                print("全部商品数据抓取完成。")
        finally:
            if self.spider:
                self.spider.close()

    @staticmethod
    def _ensure_columns(df):
        for column in (TITLE_COLUMN, IMAGE_COLUMN):
            if column not in df.columns:
                df[column] = None

        if URL_COLUMN not in df.columns:
            raise ValueError(f"输入文件缺少必要列: {URL_COLUMN}")
