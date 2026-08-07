import logging
import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the camera capture/inference worker in a separate process."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=None, help="inference interval seconds")

    def handle(self, *args, **options):
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newcell.settings")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            stream=sys.stdout,
        )
        from newcell.engine.camera_worker import main
        self.stdout.write("Starting camera worker...")
        main(interval=options.get("interval"))
