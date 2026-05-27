"""
集中配置 - 支持环境变量和 .env 文件。
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
CATEGORIES_DIR = DATA_DIR / "categories"

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

DEFAULT_INPUT_FILE = INPUT_DIR / "my-products.xlsx"
DEFAULT_OUTPUT_FILE = OUTPUT_DIR / "my-products全部.xlsx"
STAGE2_INPUT_FILE = DEFAULT_OUTPUT_FILE
STAGE2_OUTPUT_FILE = CATEGORIES_DIR / "my-products全部_分析表.xlsx"
STAGE3_OUTPUT_FILE = CATEGORIES_DIR / "my-products全部_Stage3_结构化结果.xlsx"
AI_ANALYZER_INPUT = STAGE3_OUTPUT_FILE
AI_ANALYZER_OUTPUT = OUTPUT_DIR / "my-products全部_Final_Optimization.xlsx"

BRAND_NAME = "ALLY-MAGIC"
