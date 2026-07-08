release: python backend/manage.py migrate --noinput
web: ./start.sh
worker: celery --workdir backend -A doc2onec worker -l info
