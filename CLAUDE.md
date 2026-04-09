# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI DIAL Bing Grounding — a FastAPI-based DIAL application that integrates Azure AI Agents with Bing Search and Bing Custom Search grounding tools. It implements the DIAL SDK `ChatCompletion` interface, exposing chat completion and configuration endpoints for use within the DIAL ecosystem.

Python >=3.11, <3.14. Dependency management via Poetry >=2.1.1. Azure AI packages (`azure-ai-agents`, `azure-ai-projects`) are core integration libraries.

## Common Commands

```bash
# Setup
make install              # Create venv + install all deps (poetry)
make serve                # Dev server on port 5001 with auto-reload

# Linting & formatting
make lint                 # Runs pyright, flake8, then checks autoflake/isort/black
make format               # Auto-fix formatting (autoflake -> isort -> black)

# Testing
make test                 # Unit tests + doctests
make integration_tests    # Integration tests (requires Azure credentials)
make all_tests            # All tests with custom path/args support
# Examples:
#   make all_tests TEST_PATH=tests/unit_tests/test_dummy.py
#   make all_tests ARGS="-k test_bing_search -v"

# Docker
make docker_serve         # Build & run in Docker (port 5001 -> 5000)
make clean                # Remove venv and build artifacts
```

Nox orchestrates lint/format/test sessions (see `noxfile.py`). Pytest runs with `-n=auto` (parallel), 60s timeout, and `--asyncio-mode=auto`.

## Code Style

- **black** (80-char line length), **isort** (black profile), **autoflake** (remove unused imports)
- **pyright** in basic mode — errors on unused variables and incompatible method overrides
- **flake8** ignores E501, W503, E203
- `PYDANTIC_V2=True` is required (exported in Makefile)

## Architecture

**Entry point:** `aidial_bing_grounding/app.py` — creates a `DIALApp` with telemetry, registers `BingGroundingApplication` on the `{model_id}` route.

**Request flow:**
1. `BingGroundingApplication.chat_completion()` (`agent/bing_grounding.py`) — main handler
2. Reads per-request config from `x-upstream-extra-data` header (`agent/upstream_config.py`) with env var fallbacks
3. Parses user configuration from `custom_fields.configuration` (`agent/configuration.py`) — thread strategy + optional custom search config
4. Creates/reuses Azure project client and agent via caching layer (`agent/cache.py`)
5. Manages thread lifecycle as an async context manager (`agent/thread.py`) — creates/reuses threads, converts DIAL messages to Azure format
6. Streams agent response via `EventHandler` (`agent/event_handler.py`) — processes message deltas, citations, tool calls, and usage

**Key patterns:**
- Async-first throughout (aiohttp, Azure SDK async clients)
- Agent/tool caching with invalidation on specific Azure errors (API key missing, agent/thread not found)
- Thread state persisted in DIAL response `custom_content` for multi-turn conversations
- Error handling via `@dial_exception_decorator` converting all exceptions to `DialException`
- Custom error types in `utils/errors.py`: `UserError` (chat-facing) and `ValidationError` (API-facing)

## Environment Variables

Required: `AZURE_AI_PROJECT_ENDPOINT`, `BING_CONNECTION_NAME`
Optional: `BING_CUSTOM_CONNECTION_NAME`, `BING_CUSTOM_CONFIGURATION`, `LOG_LEVEL`, `DIAL_SDK_LOG`

See `.env.example` for full list including OpenTelemetry config. Dev overrides go in `.env.dev` (loaded by Makefile).
