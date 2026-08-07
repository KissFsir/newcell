"""普通脚本入口：python -m newcell.engine.run_worker [--interval 5]"""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newcell.settings")
django.setup()


def main():
    interval = None
    if "--interval" in sys.argv:
        idx = sys.argv.index("--interval")
        interval = float(sys.argv[idx + 1])
    from newcell.engine.camera_worker import main as worker_main
    worker_main(interval=interval)


if __name__ == "__main__":
    main()
