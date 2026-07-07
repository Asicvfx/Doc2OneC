import csv
import json

from django.http import HttpResponse


CSV_COLUMNS = ["employee_name", "date", "object", "work_type", "hours", "comment"]


def export_document_json(document):
    response = HttpResponse(
        json.dumps(document.normalized_json or {}, ensure_ascii=False, indent=2),
        content_type="application/json; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="document-{document.id}.json"'
    return response


def export_document_csv(document):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = f'attachment; filename="document-{document.id}.csv"'
    response.write("\ufeff")
    writer = csv.DictWriter(response, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    writer.writerow({column: (document.normalized_json or {}).get(column, "") for column in CSV_COLUMNS})
    return response
