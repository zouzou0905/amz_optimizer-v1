from core.organizer import CategoryOrganizer

# --- 配置区 ---
YOUR_GEMINI_KEY = "AIzaSyDbMqXTjjwqkUoXGWHrVbh4Bm4xLYpsA"
# 指向你已经抓好标题的那个 Excel
INPUT_RESULT_FILE = "data/output/抓取结果_成品.xlsx"


def start_categorization():
    organizer = CategoryOrganizer(YOUR_GEMINI_KEY, INPUT_RESULT_FILE)
    organizer.organize()


if __name__ == "__main__":
    start_categorization()