.PHONY: run test frontend-dev docker-up docker-down

run:
	python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

test:
	python3 -m pytest -q

frontend-dev:
	cd frontend && npm install && npm run dev

docker-up:
	docker compose up --build

docker-down:
	docker compose down
