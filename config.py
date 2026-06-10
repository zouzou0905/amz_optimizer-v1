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

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")

# 原始输入文件保持原名称，后续产物统一按阶段命名。
DEFAULT_INPUT_FILE = INPUT_DIR / "my-products.xlsx"
STAGE1_OUTPUT_FILE = OUTPUT_DIR / "my-products_stage1.xlsx"
STAGE2_OUTPUT_FILE = OUTPUT_DIR / "my-products_stage2.xlsx"
STAGE3_OUTPUT_FILE = OUTPUT_DIR / "my-products_stage3.xlsx"
STAGE4_OUTPUT_FILE = OUTPUT_DIR / "my-products_stage4.xlsx"

BRAND_NAME = "ALLY-MAGIC"
