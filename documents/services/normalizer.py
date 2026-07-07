import re


FIELDS = ["employee_name", "date", "object", "work_type", "hours", "comment"]


def normalize_worklog_data(data: dict) -> dict:
    normalized = {}
    for field in FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            value = " ".join(value.strip().split())
        normalized[field] = value if value not in ("", None) else None

    normalized["hours"] = normalize_hours(normalized.get("hours"))
    return normalized


def normalize_hours(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else value

    raw = str(value).strip().lower().replace(",", ".")
    if not raw:
        return None
    if "полный день" in raw:
        return 8

    match = re.search(r"\d+(?:\.\d+)?", raw)
    if not match:
        return None
    number = float(match.group(0))
    return int(number) if number.is_integer() else number
