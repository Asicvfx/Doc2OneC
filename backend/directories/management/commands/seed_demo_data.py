from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from directories.models import Employee, WorkObject, WorkType


class Command(BaseCommand):
    help = "Seed demo directory data and sample files"

    def handle(self, *args, **options):
        employees = [
            "Ivanov Ivan",
            "Petrov Sergey",
            "Sidorov Aleksei",
        ]
        work_objects = [
            "Object No. 1",
            "Object No. 2",
            "Astana-1",
        ]
        work_types = [
            "Electrical installation work",
            "Cable installation",
            "Technical maintenance",
        ]

        for full_name in employees:
            Employee.objects.get_or_create(full_name=full_name)
        for name in work_objects:
            WorkObject.objects.get_or_create(name=name)
        for name in work_types:
            WorkType.objects.get_or_create(name=name)

        sample_dir = Path(settings.PROJECT_ROOT) / "sample_documents"
        sample_dir.mkdir(parents=True, exist_ok=True)

        sample_text = (
            "Ivanov Ivan 2026-07-06 Object No. 1 "
            "Electrical installation work 8 hours Cable installation"
        )
        (sample_dir / "sample_worklog.txt").write_text(sample_text, encoding="utf-8")
        (sample_dir / "sample_worklog.csv").write_text(
            "employee_name,date,object,work_type,hours,comment\n"
            "Ivanov Ivan,2026-07-06,Object No. 1,Electrical installation work,8,Cable installation\n",
            encoding="utf-8",
        )

        try:
            from openpyxl import Workbook
        except ImportError:
            self.stdout.write(self.style.WARNING("openpyxl is not installed, skipping XLSX refresh"))
        else:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Worklog"
            sheet.append(["employee_name", "date", "object", "work_type", "hours", "comment"])
            sheet.append([
                "Ivanov Ivan",
                "2026-07-06",
                "Object No. 1",
                "Electrical installation work",
                8,
                "Cable installation",
            ])
            workbook.save(sample_dir / "sample_worklog.xlsx")

        self.stdout.write(self.style.SUCCESS("Demo directories and sample files are ready."))
