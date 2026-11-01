.PHONY: install run test frontend
install:
	python -m pip install -r backend/requirements-dev.txt
run:
	PYTHONPATH=backend python -m uvicorn app.main:app --app-dir backend --reload
test:
	PYTHONPATH=backend python -m pytest backend/tests -q
frontend:
	cd frontend && npm ci && npm run dev
