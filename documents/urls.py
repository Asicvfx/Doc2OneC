from django.urls import path

from . import views


app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("upload/", views.document_upload, name="upload"),
    path("<int:pk>/", views.document_detail, name="detail"),
    path("<int:pk>/process/", views.process_document_view, name="process"),
    path("<int:pk>/export/json/", views.export_json_view, name="export_json"),
    path("<int:pk>/export/csv/", views.export_csv_view, name="export_csv"),
    path("<int:pk>/mark-exported/", views.mark_exported_view, name="mark_exported"),
]
