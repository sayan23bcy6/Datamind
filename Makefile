.PHONY: up down test migrate demo lint

up:
	docker compose up -d

down:
	docker compose down

test:
	python -m pytest backend/tests -v
	cd frontend && npm test -- --run

migrate:
	docker compose exec -T api alembic upgrade head

demo:
	curl -s -X POST http://127.0.0.1:8000/api/v1/datasets/demo

lint:
	cd frontend && npm run build
