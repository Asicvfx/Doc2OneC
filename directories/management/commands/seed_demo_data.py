import csv
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from directories.models import Employee, WorkObject, WorkType


SAMPLE_TEXT = (
    "\u0418\u0432\u0430\u043d\u043e\u0432 \u0418\u0432\u0430\u043d 2026-07-06 \u041e\u0431\u044a\u0435\u043a\u0442 \u21161 "
    "\u042d\u043b\u0435\u043a\u0442\u0440\u043e\u043c\u043e\u043d\u0442\u0430\u0436\u043d\u044b\u0435 \u0440\u0430\u0431\u043e\u0442\u044b 8 \u0447\u0430\u0441\u043e\u0432 \u041c\u043e\u043d\u0442\u0430\u0436 \u043a\u0430\u0431\u0435\u043b\u044f"
)

EMPLOYEES = [
    ("\u0418\u0432\u0430\u043d\u043e\u0432 \u0418\u0432\u0430\u043d", "EMP-001"),
    ("\u041f\u0435\u0442\u0440\u043e\u0432 \u0421\u0435\u0440\u0433\u0435\u0439", "EMP-002"),
    ("\u0421\u0438\u0434\u043e\u0440\u043e\u0432 \u0410\u043b\u0435\u043a\u0441\u0435\u0439", "EMP-003"),
]

WORK_OBJECTS = [
    ("\u041e\u0431\u044a\u0435\u043a\u0442 \u21161", "OBJ-001"),
    ("\u041e\u0431\u044a\u0435\u043a\u0442 \u21162", "OBJ-002"),
    ("\u0410\u0441\u0442\u0430\u043d\u0430-1", "OBJ-003"),
]

WORK_TYPES = [
    ("\u042d\u043b\u0435\u043a\u0442\u0440\u043e\u043c\u043e\u043d\u0442\u0430\u0436\u043d\u044b\u0435 \u0440\u0430\u0431\u043e\u0442\u044b", "WT-001"),
    ("\u041c\u043e\u043d\u0442\u0430\u0436 \u043a\u0430\u0431\u0435\u043b\u044f", "WT-002"),
    ("\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u043e\u0435 \u043e\u0431\u0441\u043b\u0443\u0436\u0438\u0432\u0430\u043d\u0438\u0435", "WT-003"),
]


class Command(BaseCommand):
    help = "Seed demo directories and sample documents for Doc2OneC."

    def handle(self, *args, **options):
        for full_name, external_id in EMPLOYEES:
            Employee.objects.update_or_create(
                full_name=full_name,
                defaults={"external_1c_id": external_id, "is_active": True},
            )
        for name, external_id in WORK_OBJECTS:
            WorkObject.objects.update_or_create(
                name=name,
                defaults={"external_1c_id": external_id, "is_active": True},
            )
        for name, external_id in WORK_TYPES:
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
                    "employee_name": EMPLOYEES[0][0],
                    "date": "2026-07-06",
                    "object": WORK_OBJECTS[0][0],
                    "work_type": WORK_TYPES[0][0],
                    "hours": "8 \u0447\u0430\u0441\u043e\u0432",
                    "comment": WORK_TYPES[1][0],
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
                    EMPLOYEES[0][0],
                    "2026-07-06",
                    WORK_OBJECTS[0][0],
                    WORK_TYPES[0][0],
                    "8 \u0447\u0430\u0441\u043e\u0432",
                    WORK_TYPES[1][0],
                ]
            )
            workbook.save(sample_dir / "sample_worklog.xlsx")

        self.stdout.write(self.style.SUCCESS("Demo directories and sample documents are ready."))