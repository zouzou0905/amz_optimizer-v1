import os
from app import AmazonApp
from config import INPUT_DIR, OUTPUT_DIR, DEFAULT_INPUT_FILE, DEFAULT_OUTPUT_FILE


def main():
    # 自动创建必要的目录，无需手动操作
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    config = {
        'input_file': str(DEFAULT_INPUT_FILE),
        'output_file': str(DEFAULT_OUTPUT_FILE),
        'headless': False
    }

    # 启动应用
    app = AmazonApp(config)
    app.run()


if __name__ == "__main__":
    main()