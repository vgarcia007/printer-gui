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
	docker compose run --rm --no-deps --workdir /src -v "$(CURDIR):/src:ro" web python -m unittest discover -s tests -v

validate:
	python3 -m compileall -q app scanner ocr tests config.py run.py
	sh -n app/entrypoint.sh cups/entrypoint.sh scanner/entrypoint.sh
	python3 -m json.tool config/printers.json >/dev/null
	docker compose config --quiet
	docker compose run --rm --no-deps --workdir /src -v "$(CURDIR):/src:ro" web python -m unittest discover -s tests -v
