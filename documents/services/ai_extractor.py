import re


KEY_MAP = {
    "employee_name": "employee_name",
    "employee": "employee_name",
    "date": "date",
    "object": "object",
    "work_object": "object",
    "work_type": "work_type",
    "hours": "hours",
    "comment": "comment",
}

KNOWN_WORK_TYPES = [
    "Электромонтажные работы",
    "Техническое обслуживание",
    "Монтаж кабеля",
]


def extract_worklog_data(text: str) -> dict:
    text = (text or "").strip()
    data = {
        "employee_name": None,
        "date": None,
        "object": None,
        "work_type": None,
        "hours": None,
        "comment": None,
    }
    if not text:
        return data

    keyed = _extract_keyed_data(text)
    if keyed:
        data.update(keyed)
        return data

    date_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if date_match:
        data["date"] = date_match.group(0)
        data["employee_name"] = text[: date_match.start()].strip() or None

    object_match = re.search(r"(Объект\s*[№#]?\s*[\w-]+|Астана-\d+)", text, flags=re.IGNORECASE)
    if object_match:
        data["object"] = object_match.group(0).strip()

    for work_type in KNOWN_WORK_TYPES:
        if work_type.lower() in text.lower():
            data["work_type"] = work_type
            break

    hours_match = _find_hours(text, data.get("work_type"))
    if hours_match:
        data["hours"] = hours_match.group(1).strip()
        comment = text[hours_match.end() :].strip(" .,-;")
        data["comment"] = comment or None

    if not data["comment"] and data["work_type"]:
        after_work_type = text.split(data["work_type"], 1)[-1].strip()
        data["comment"] = after_work_type or None

    return data


def _find_hours(text: str, work_type: str | None):
    full_day = re.search(r"(полный\s+день)", text, flags=re.IGNORECASE)
    if full_day:
        return full_day

    explicit = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:час(?:ов|а)?|ч\b)", text, flags=re.IGNORECASE)
    if explicit:
        return explicit

    if work_type and work_type in text:
        tail = text.split(work_type, 1)[-1]
        offset = len(text) - len(tail)
        standalone = re.search(r"\b(\d+(?:[.,]\d+)?)\b", tail)
        if standalone:
            start = offset + standalone.start()
            end = offset + standalone.end()
            return _SimpleMatch(text[start:end], start, end)
    return None


class _SimpleMatch:
    def __init__(self, value: str, start: int, end: int):
        self.value = value
        self._start = start
        self._end = end

    def group(self, index: int):
        return self.value

    def end(self):
        return self._end


def _extract_keyed_data(text: str) -> dict:
    result = {}
    parts = re.split(r"[;\n]+", text)
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        normalized_key = KEY_MAP.get(key.strip().lower())
        if normalized_key:
            result[normalized_key] = value.strip() or None
    return result
