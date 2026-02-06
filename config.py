"""
集中配置 - 支持环境变量和 .env 文件
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 未安装 python-dotenv 时跳过

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent

# 数据目录
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
CATEGORIES_DIR = DATA_DIR / "categories"

# Gemini 配置（旧流程仍在用）
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    # 临时备用（建议创建 .env 并设置 GEMINI_API_KEY 以提升安全性）
    GEMINI_API_KEY = "AIzaSyDbMqXTjjwqkUoXGWHrVbh4Bm4xLYpsAvo"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# DeepSeek 配置（用于关键词竞品分析）
DEEPSEEK_API_KEY = "sk-5582911f1b6b4ca49eacd90160223126"
DEEPSEEK_MODEL = "deepseek-chat"

# 文件路径（可被 main/各脚本覆盖）
DEFAULT_INPUT_FILE = INPUT_DIR / "测试.xlsx"
DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "抓取结果_成品.xlsx"
STAGE2_INPUT_FILE = OUTPUT_DIR / "抓取结果_成品.xlsx"
AI_ANALYZER_INPUT = CATEGORIES_DIR / "Apparel_Stage3_结构化结果.xlsx"
AI_ANALYZER_OUTPUT = OUTPUT_DIR / "Apparel_Final_Optimization.xlsx"

# 品牌词（organizer 使用）
BRAND_NAME = "ALLY-MAGIC"


def get_api_key():
    """获取 API 密钥，未设置时抛出清晰错误"""
    key = GEMINI_API_KEY
    if not key:
        raise ValueError(
            "未找到 GEMINI_API_KEY。请在项目根目录创建 .env 文件，"
            "添加 GEMINI_API_KEY=你的密钥，或参考 .env.example"
        )
    return key
