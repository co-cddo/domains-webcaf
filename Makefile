up-devserver:
	docker compose -f docker-compose.yml run --rm --service-ports --entrypoint "python manage.py runserver 0.0.0.0:8000" web

up-devserver-nodebug:
	docker compose -f docker-compose.yml run --rm --service-ports --env DEBUG=False --entrypoint "python manage.py runserver 0.0.0.0:8000" web

shell:
	docker compose exec web bash

clear-db:
	docker compose down && docker container prune -f && docker volume rm domains-webcaf_postgres-data

test:
	docker compose run --rm --service-ports --entrypoint "python manage.py test -v 2" web
build:
	BUILDKIT_PROGRESS=plain docker compose build

behave:
	FEATURE_TEST_ARGS="$(FEATURE_TEST_ARGS)" docker compose -f docker-compose.yml -f docker-compose.feature-tests.yml up --build --abort-on-container-exit --exit-code-from feature-tests feature-tests
