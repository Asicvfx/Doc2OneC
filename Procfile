release: python backend/manage.py migrate --noinput
web: gunicorn --chdir backend doc2onec.wsgi:application
worker: celery --workdir backend -A doc2onec worker -l info
