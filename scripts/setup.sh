#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv /workspace/discipleship-venv
/workspace/discipleship-venv/bin/python -m pip install -r requirements.txt
/workspace/discipleship-venv/bin/python manage.py migrate --noinput
/workspace/discipleship-venv/bin/python manage.py collectstatic --noinput
/workspace/discipleship-venv/bin/python manage.py check
