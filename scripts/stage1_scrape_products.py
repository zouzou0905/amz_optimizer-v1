import os

from app import AmazonApp
from config import DEFAULT_INPUT_FILE, INPUT_DIR, OUTPUT_DIR, STAGE1_OUTPUT_FILE


def run(headless=False):
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    app = AmazonApp(
        {
            "input_file": str(DEFAULT_INPUT_FILE),
            "output_file": str(STAGE1_OUTPUT_FILE),
            "headless": headless,
            "max_retries": 3,
        }
    )
    app.run()


def main():
    run()


if __name__ == "__main__":
    main()
