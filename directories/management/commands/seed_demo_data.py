import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from directories.models import Employee, WorkObject, WorkType


SAMPLE_TEXT = (
    "Иванов Иван 2026-07-06 Объект №1 "
    "Электромонтажные работы 8 часов Монтаж кабеля"
)


class Command(BaseCommand):
    help = "Seed demo directories and sample documents for Doc2OneC."

    def handle(self, *args, **options):
        employees = [
            ("Иванов Иван", "EMP-001"),
            ("Петров Сергей", "EMP-002"),
            ("Сидоров Алексей", "EMP-003"),
        ]
        work_objects = [
            ("Объект №1", "OBJ-001"),
            ("Объект №2", "OBJ-002"),
            ("Астана-1", "OBJ-003"),
        ]
        work_types = [
            ("Электромонтажные работы", "WT-001"),
            ("Монтаж кабеля", "WT-002"),
            ("Техническое обслуживание", "WT-003"),
        ]

        for full_name, external_id in employees:
            Employee.objects.update_or_create(
                full_name=full_name,
                defaults={"external_1c_id": external_id, "is_active": True},
            )
        for name, external_id in work_objects:
            WorkObject.objects.update_or_create(
                name=name,
                defaults={"external_1c_id": external_id, "is_active": True},
            )
        for name, external_id in work_types:
            WorkType.objects.update_or_create(
                name=name,
                defaults={"external_1c_id": external_id, "is_active": True},
            )

        sample_dir = Path(settings.BASE_DIR) / "sample_documents"
        sample_dir.mkdir(exist_ok=True)
        (sample_dir / "sample_worklog.txt").write_text(SAMPLE_TEXT, encoding="utf-8")

        with (sample_dir / "sample_worklog.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["employee_name", "date", "object", "work_type", "hours", "comment"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "employee_name": "Иванов Иван",
                    "date": "2026-07-06",
                    "object": "Объект №1",
                    "work_type": "Электромонтажные работы",
                    "hours": "8 часов",
                    "comment": "Монтаж кабеля",
                }
            )

        try:
            from openpyxl import Workbook
        except ImportError:
            self.stdout.write(self.style.WARNING("openpyxl is not installed; skipped xlsx sample."))
        else:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Worklog"
            sheet.append(["employee_name", "date", "object", "work_type", "hours", "comment"])
            sheet.append(
                [
                    "Иванов Иван",
                    "2026-07-06",
                    "Объект №1",
                    "Электромонтажные работы",
                    "8 часов",
                    "Монтаж кабеля",
                ]
            )
            workbook.save(sample_dir / "sample_worklog.xlsx")

        self.stdout.write(self.style.SUCCESS("Demo directories and sample documents are ready."))
