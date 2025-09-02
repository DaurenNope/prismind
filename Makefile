run:
	streamlit run app.py

collect:
	python collect_multi_platform.py

 scheduler:
	python services/aps_scheduler_runner.py

 test:
	pytest -q

 lint:
	ruff check . || true

 format:
	black . && isort .
