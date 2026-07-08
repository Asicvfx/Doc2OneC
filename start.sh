#!/usr/bin/env bash
set -o errexit

python backend/manage.py migrate --noinput
exec gunicorn --chdir backend doc2onec.wsgi:application --log-file -
