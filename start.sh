#!/usr/bin/env bash
set -o errexit

python backend/manage.py migrate --noinput
if [ "${AUTO_SEED_DEMO_DATA:-true}" = "true" ]; then
  python backend/manage.py seed_demo_data
fi
exec gunicorn --chdir backend doc2onec.wsgi:application --log-file -
