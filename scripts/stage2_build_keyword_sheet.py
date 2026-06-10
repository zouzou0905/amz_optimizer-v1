try:
    from scripts import _bootstrap  # noqa: F401
except ImportError:
    import _bootstrap  # noqa: F401

from config import STAGE1_OUTPUT_FILE, STAGE2_OUTPUT_FILE
from core.organizer import CategoryOrganizer


def run(input_file=STAGE1_OUTPUT_FILE, output_file=STAGE2_OUTPUT_FILE, market="UK", use_ai=True):
    organizer = CategoryOrganizer(
        input_path=str(input_file),
        output_path=str(output_file),
        market=market,
        use_ai=use_ai,
    )
    organizer.organize()


def start_categorization():
    run()


if __name__ == "__main__":
    start_categorization()
