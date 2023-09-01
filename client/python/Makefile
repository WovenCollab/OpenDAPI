# Makefile

APP_PATH=opendapi
TESTS_PATH=tests

requirements:
	curl -sSL https://install.python-poetry.org | python3 -
	poetry env list
	poetry env info
	poetry lock
	poetry install

test:
	poetry run pytest -s -vv									\
		--cov=${APP_PATH}										\
		--cov-fail-under=100									 	\
		--cov-report=term-missing								\
		--cov-report=html:coverage_html_report					\
		$(TESTS_PATH)

lint:
	poetry run pylint --version
	poetry run pylint ${APP_PATH} ${TESTS_PATH}

format:
	poetry run isort $(APP_PATH)/**.py $(TESTS_PATH)/**.py
	poetry run black $(APP_PATH) $(TESTS_PATH)

formatcheck:
	poetry run isort --check-only $(APP_PATH)/**.py $(TESTS_PATH)/**.py
	poetry run black --check $(APP_PATH) $(TESTS_PATH)

security:
	poetry run bandit --version
	poetry run bandit -r ${APP_PATH}

precommit_ci: requirements format test lint formatcheck security
ci: requirements test lint formatcheck security

.PHONY: requirements test lint format formatcheck security ci
