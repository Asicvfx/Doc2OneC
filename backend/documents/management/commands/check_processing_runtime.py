import json

from django.core.management.base import BaseCommand

from documents.services.processing_runtime import get_processing_runtime_status


class Command(BaseCommand):
    help = "Print the current document processing runtime status for smoke checks."

    def handle(self, *args, **options):
        status = get_processing_runtime_status()
        self.stdout.write(json.dumps(status.as_dict(), indent=2))