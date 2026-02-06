import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random


class AmazonSpider:
    def __init__(self, headless=False):
        options = uc.ChromeOptions()
        if headless:
            options.add_argument('--headless')
        options.add_argument('--lang=de-DE')

        # --- 强制指定版本为 144，解决驱动版本过高的问题 ---
        print("🔧 正在启动 Chrome 144 兼容模式...")
        try:
            self.driver = uc.Chrome(options=options, version_main=144)
        except Exception as e:
            print(f"⚠️ 强制版本启动失败，尝试自动启动: {e}")
            self.driver = uc.Chrome(options=options)

    def fetch_product_data(self, url):
        """同时抓取标题和图片链接"""
        try:
            self.driver.get(url)
            time.sleep(random.uniform(2, 4))
            wait = WebDriverWait(self.driver, 15)

            # 1. 抓取标题
            title_el = wait.until(EC.presence_of_element_located((By.ID, "productTitle")))
            title = title_el.text.strip()

            # 2. 抓取图片链接 (新增逻辑)
            image_url = "无图片"
            try:
                # 尝试 Amazon 常用的主图 ID
                img_el = self.driver.find_element(By.ID, "landingImage") or \
                         self.driver.find_element(By.ID, "imgBlkFront")
                image_url = img_el.get_attribute("src")
            except:
                pass

            return {"title": title, "image_url": image_url}

        except Exception as e:
            print(f"❌ 抓取异常: {e}")
            return {"title": "抓取失败", "image_url": "抓取失败"}

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass