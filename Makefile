PORT ?= 5001
IMAGE_NAME ?= ai-dial-bing-grounding
PLATFORM ?= linux/amd64
DEV_PYTHON ?= 3.11
DOCKER ?= docker
POETRY ?= poetry
POETRY_PYTHON ?= python
FILES ?=
ARGS ?=

# Any non-empty CI value (even 'false' or '0') means that CI is enabled
CI ?=

# AI DIAL SDK: pydantic v2 mode
export PYDANTIC_V2=True

# Conditional: pass FILES as nox posargs when set
ifdef FILES
  NOX_FILES = -- $(FILES)
else
  NOX_FILES =
endif

.PHONY: all install build serve clean cleanup_project lint format test \
	integration_tests all_tests allure_serve docker_serve help \
	black black_check isort isort_check autoflake autoflake_check flake8 pyright

-include .env.dev
export

all: build

init_env:
	$(if $(CI),,$(POETRY) env use $(POETRY_PYTHON))

install: init_env
	$(POETRY) install

build: install
	$(POETRY) build

clean:
	-$(POETRY) run python -m scripts.clean
	-$(POETRY) env remove --all

cleanup_project:
	$(POETRY) run python -m scripts.cleanup_project

# --- Linting ---

lint: install
	$(POETRY) run nox -s lint

# --- Formatting ---

format: install
	$(POETRY) run nox -s format

# --- Individual tool targets (honor FILES variable, run via nox) ---

black:
	$(POETRY) run -- nox -s black $(NOX_FILES)

black_check:
	$(POETRY) run -- nox -s black_check $(NOX_FILES)

isort:
	$(POETRY) run -- nox -s isort $(NOX_FILES)

isort_check:
	$(POETRY) run -- nox -s isort_check $(NOX_FILES)

autoflake:
	$(POETRY) run -- nox -s autoflake $(NOX_FILES)

autoflake_check:
	$(POETRY) run -- nox -s autoflake_check $(NOX_FILES)

flake8:
	$(POETRY) run -- nox -s flake8 $(NOX_FILES)

pyright:
	$(POETRY) run -- nox -s pyright $(NOX_FILES)

# --- Running ---

serve: install
	$(POETRY) run uvicorn "aidial_bing_grounding.app:app" --reload --host "0.0.0.0" --port $(PORT) --workers=1 --env-file ./.env

docker_serve:
	$(DOCKER) build --platform $(PLATFORM) -t $(IMAGE_NAME):dev .
	$(DOCKER) run --platform $(PLATFORM) --env-file ./.env --rm -p $(PORT):5000 $(IMAGE_NAME):dev

# --- Testing ---

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

# --- Help ---

help:
	@echo '===================='
	@echo 'build                        - build the source and wheels archives'
	@echo 'clean                        - clean virtual env and build artifacts'
	@echo '-- LINTING --'
	@echo 'format                       - run all code formatters'
	@echo 'lint                         - run all linters'
	@echo 'black                        - run black formatter'
	@echo 'isort                        - run isort import sorter'
	@echo 'autoflake                    - run autoflake unused import remover'
	@echo 'flake8                       - run flake8 linter'
	@echo 'pyright                      - run pyright type checker'
	@echo '-- RUN --'
	@echo 'serve                        - run the dev server locally'
	@echo 'docker_serve                 - run the dev server from the docker'
	@echo '-- TESTS --'
	@echo 'test                         - run unit tests'
	@echo 'integration_tests            - run integration tests'
	@echo 'all_tests                    - run all tests (allows to pass test files and extra arguments)'
