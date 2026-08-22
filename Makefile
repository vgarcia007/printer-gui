.PHONY: up down build logs status test validate

up:
	docker compose up --detach --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs --follow

status:
	docker compose ps

test:
	python3 -m unittest discover -s tests -v

validate: test
	python3 -m compileall -q app tests
	sh -n app/entrypoint.sh cups/entrypoint.sh
	python3 -m json.tool config/printers.json >/dev/null
	docker compose config --quiet
