import argparse
import asyncio

from core.logging_utils import stage_log
from scripts import stage1_scrape_products
from scripts import stage2_build_keyword_sheet
from scripts import stage3_collect_competitors
from scripts import stage4_ai_optimize_listing


STAGES = ("stage1", "stage2", "stage3", "stage4", "all")


def parse_args():
    parser = argparse.ArgumentParser(description="Amazon Optimizer 统一运行入口")
    parser.add_argument("stage", choices=STAGES, help="要运行的阶段")
    parser.add_argument("--market", choices=["UK", "DE"], default="UK", help="目标市场，默认 UK")
    parser.add_argument("--headless", action="store_true", help="浏览器无头模式")
    return parser.parse_args()


def run_stage(stage, market="UK", headless=False):
    with stage_log(stage):
        if stage == "stage1":
            stage1_scrape_products.run(headless=headless)
        elif stage == "stage2":
            stage2_build_keyword_sheet.run(market=market)
        elif stage == "stage3":
            asyncio.run(stage3_collect_competitors.run(market=market, headless=headless))
        elif stage == "stage4":
            asyncio.run(stage4_ai_optimize_listing.run(market=market))
        else:
            raise ValueError(f"未知阶段: {stage}")


def main():
    args = parse_args()

    if args.stage == "all":
        for stage in ("stage1", "stage2", "stage3", "stage4"):
            print(f"\n========== Running {stage} ==========")
            run_stage(stage, market=args.market, headless=args.headless)
    else:
        run_stage(args.stage, market=args.market, headless=args.headless)


if __name__ == "__main__":
    main()
