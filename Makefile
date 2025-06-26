include .env

PORT ?= 5001
IMAGE_NAME ?= ai-dial-bing-grounding
PLATFORM ?= linux/amd64
DEV_PYTHON ?= 3.11
DOCKER ?= docker
VENV_DIR ?= .venv
POETRY ?= $(VENV_DIR)/bin/poetry
POETRY_VERSION ?= 2.1.1
ARGS ?=

.PHONY: all install build serve clean cleanup_project docs publish lint format test integration_tests allure_serve docker_serve

all: build

init_env:
	python -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install poetry==$(POETRY_VERSION) --quiet

install: init_env
	$(POETRY) env use python$(DEV_PYTHON)
	$(POETRY) install

build: install
	$(POETRY) build

serve: install
	$(POETRY) run uvicorn "aidial_bing_grounding.app:app" --reload --host "0.0.0.0" --port $(PORT) --workers=1 --env-file ./.env

clean:
	$(POETRY) run python -m scripts.clean
	$(POETRY) env remove --all

cleanup_project:
	$(POETRY) run python -m scripts.cleanup_project

docs: install
	@echo "Building docs..."

publish: install
	@echo "Publishing Docker image..."
	# $(DOCKER) push $(IMAGE_NAME):latest

lint: install
	$(POETRY) run nox -s lint

format: install
	$(POETRY) run nox -s format

test: install
	$(POETRY) run nox -s test

integration_tests: install
	$(POETRY) run nox -s integration_tests

# To run unit and integration tests:
#   make all_tests
# To list unit tests:
#   make all_tests TEST_PATH=tests/unit_tests/ ARGS=--collect-only
# To run tests from a particular module:
#   make all_tests TEST_PATH=tests/unit_tests/test_app.py
# To run tests from a particular test function:
#   make all_tests TEST_PATH=tests/unit_tests/test_app.py::test_average
# To print stderr/stdout of each test:
#   make all_tests ARGS="-v --durations=0 -rA"
# To run particular test by name:
#   make all_tests ARGS="-k 0_to_9"
all_tests: install
	$(POETRY) run pytest $(TEST_PATH) $(ARGS)

# serve Allure test results
allure_serve:
	allure serve

docker_serve:
	$(DOCKER) build --platform $(PLATFORM) -t $(IMAGE_NAME):dev .
	$(DOCKER) run --platform $(PLATFORM) --env-file ./.env --rm -p $(PORT):5000 $(IMAGE_NAME):dev

help:
	@echo '===================='
	@echo 'build                        - build the source and wheels archives'
	@echo 'clean                        - clean virtual env and build artifacts'
	@echo 'docs                         - build the documentation'
	@echo 'publish'                     - publish the Docker image to the registry'
	@echo '-- LINTING --'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo '-- RUN --'
	@echo 'serve                        - run the dev server locally'
	@echo 'docker_serve                 - run the dev server from the docker'
	@echo '-- TESTS --'
	@echo 'test                         - run unit tests'
	@echo 'test                         - run all tests in file'
	@echo 'docker_test                  - run unit tests from the docker'
	@echo 'integration_tests            - run integration tests'
	@echo 'all_tests                    - run all tests (allows to pass test files and extra arguments)'