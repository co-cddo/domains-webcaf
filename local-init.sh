#!/bin/bash

python manage.py makemigrations
python manage.py collectstatic --noinput
python manage.py migrate --noinput
