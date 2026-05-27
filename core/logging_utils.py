from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sys
import traceback


LOG_DIR = Path("logs")


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)


@contextmanager
def stage_log(stage_name):
    LOG_DIR.mkdir(exist_ok=True)
    log_path = LOG_DIR / f"{stage_name}.log"

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    with log_path.open("a", encoding="utf-8") as log_file:
        header = (
            "\n"
            f"========== {stage_name} started at {datetime.now():%Y-%m-%d %H:%M:%S} ==========\n"
        )
        log_file.write(header)
        log_file.flush()
        original_stdout.write(f"日志文件: {log_path}\n")
        original_stdout.flush()

        sys.stdout = TeeStream(original_stdout, log_file)
        sys.stderr = TeeStream(original_stderr, log_file)

        try:
            yield log_path
        except Exception:
            traceback.print_exc()
            raise
        finally:
            footer = f"========== {stage_name} ended at {datetime.now():%Y-%m-%d %H:%M:%S} ==========\n"
            print(footer)
            sys.stdout = original_stdout
            sys.stderr = original_stderr
