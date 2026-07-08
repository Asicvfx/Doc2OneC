release: python manage.py migrate --noinput
web: gunicorn doc2onec.wsgi:application
worker: celery -A doc2onec worker -l info