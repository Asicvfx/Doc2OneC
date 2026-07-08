import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "doc2onec.settings")

app = Celery("doc2onec")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()