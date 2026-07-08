from datetime import date

from directories.models import Employee, WorkObject, WorkType


REQUIRED_FIELDS = ["employee_name", "date", "object", "work_type", "hours"]


def validate_worklog_data(data: dict) -> list[dict]:
    errors = []

    for field in REQUIRED_FIELDS:
        if data.get(field) in ("", None):
            errors.append({"field": field, "message": "Required field is missing."})

    _validate_date(data.get("date"), errors)
    _validate_hours(data.get("hours"), errors)
    _validate_directory_value(Employee, "employee_name", data.get("employee_name"), errors, "Employee not found.")
    _validate_directory_value(WorkObject, "object", data.get("object"), errors, "Work object not found.")
    _validate_directory_value(WorkType, "work_type", data.get("work_type"), errors, "Work type not found.")
    return errors


def _validate_date(value, errors):
    if not value:
        return
    try:
        date.fromisoformat(str(value))
    except ValueError:
        errors.append({"field": "date", "message": "Date must use YYYY-MM-DD format."})


def _validate_hours(value, errors):
    if value is None:
        return
    try:
        hours = float(value)
    except (TypeError, ValueError):
        errors.append({"field": "hours", "message": "Hours must be a number."})
        return
    if hours <= 0 or hours > 24:
        errors.append({"field": "hours", "message": "Hours must be between 0 and 24."})


def _validate_directory_value(model, field, value, errors, message):
    if not value:
        return
    lookup = {"full_name__iexact": value} if model.__name__ == "Employee" else {"name__iexact": value}
    if not model.objects.active().filter(**lookup).exists():
        errors.append({"field": field, "message": message})
