FROM python:3.11-alpine AS builder

RUN apk update && apk upgrade --no-cache libcrypto3 libssl3
RUN apk add --no-cache alpine-sdk linux-headers
RUN pip install poetry==2.1.1

WORKDIR /app

# Install split into two steps (the dependencies and the sources)
# in order to leverage the Docker caching
COPY pyproject.toml poetry.lock poetry.toml README.md ./
RUN poetry install --no-interaction --no-ansi --no-cache --no-root \
  --no-directory --only main

COPY aidial_bing_grounding aidial_bing_grounding
RUN poetry install --no-interaction --no-ansi --no-cache --only main

FROM python:3.11-alpine AS server

RUN apk update && apk upgrade --no-cache libcrypto3 libssl3

# CVE-2023-52425
RUN apk upgrade --no-cache libexpat
# CVE-2024-6345
RUN pip install setuptools==70.0.0

WORKDIR /app

# Copy the sources and virtual env. No poetry.
RUN adduser -u 1001 --disabled-password --gecos "" appuser
COPY --chown=appuser --from=builder /app .

COPY ./scripts/docker_entrypoint.sh /docker_entrypoint.sh
RUN chmod +x /docker_entrypoint.sh

EXPOSE 5000

USER appuser
ENTRYPOINT ["/docker_entrypoint.sh"]

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=6 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

CMD ["uvicorn", "aidial_bing_grounding.app:app", "--host", "0.0.0.0", "--port", "5000"]
