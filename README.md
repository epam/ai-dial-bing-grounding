# AI DIAL Bing Grounding

Repository contains DIAL application that implements integration with `Azure AI Agent with Grounding with Bing Search`.

Application addresses the need for web-search enabled agent for **Azure-restricted** environments.

For environments with access to the **GCP** and **Vertex AI** resources, consider using `Gemini 2.5 Pro with Google 
Search Grounding`.

## Deployment of Azure AI Agent with Bing Grounding

1. Follow [the guide](https://learn.microsoft.com/en-us/azure/ai-services/agents/quickstart?pivots=ai-foundry-portal) 
   to create an agent.
2. Create [Grounding with Bing Search resource](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/bing-grounding#setup).
3. Create a [Grounding with Bing Search connection](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/bing-code-samples?pivots=portal)

See also the [API documentation](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme?view=azure-python-preview) 
for Azure AI project client Python library.

## Environment Variables

| Variable                           | Required | Description                                                          | Available Values                      | Default Value |
|------------------------------------|----------|----------------------------------------------------------------------|---------------------------------------|---------------|
| AZURE_AI_PROJECT_CONNECTION_STRING | Yes      | Connection string to the Azure AI Project resource.                  |                                       |               |
| BING_CONNECTION_NAME               | Yes      | Name of the Bing connection in Azure AI Project.                     |                                       |               |
| LOG_LEVEL                          | No       | Log level. Use DEBUG for dev purposes and INFO in prod.              | DEBUG, INFO, WARNING, ERROR, CRITICAL | INFO          |
| DIAL_SDK_LOG                       | No       | Log level for DIAL SDK. Use DEBUG for dev purposes and INFO in prod. | DEBUG, INFO, WARNING, ERROR, CRITICAL | INFO          |
| WEB_CONCURRENCY                    | No       | Number of workers for the server.                                    | Integer                               | 2             |

For development: copy `.env.example` to `.env` and customize it for your environment.

## DIAL Application Configuration

Example configuration for the DIAL application:

```json
{
  "applications": {
    "azure-ai-agent-bing-search": {
      "displayName": "Azure AI Agent with Bing Search",
      "description": "Azure AI Agent with Grounding with Bing Search connection.",
      "iconUrl": "gpt4.svg",
      "endpoint": "http://dial-bing-grounding.dial-development.svc.cluster.local.:80/openai/deployments/azure-ai-agent-bing-search/chat/completions",
      "descriptionKeywords": [
        "Web Search",
        "Bing Search Grounding"
      ]
    }
  }
}
```

## Deployment Configuration

The app deployment has the following configuration schema:
```json
{
  "title": "BingGroundingConfiguration",
  "type": "object",
  "properties": {
    "thread_management_strategy": {
      "description": "Strategy for managing threads. 'retain' keeps threads, 'delete' removes them after use.",
      "default": "delete",
      "allOf": [
        {
          "$ref": "#/definitions/ThreadManagementStrategy"
        }
      ]
    }
  },
  "definitions": {
    "ThreadManagementStrategy": {
      "title": "ThreadManagementStrategy",
      "description": "An enumeration.",
      "enum": [
        "retain",
        "delete"
      ],
      "type": "string"
    }
  }
}
```

Example of request body with configuration:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What's the US GDP forecast for 2025 by IMF?"
    }
  ],
  "custom_fields": {
    "configuration": {
      "thread_management_strategy": "retain"
    }
  }
}
```

## Developer environment

This project uses [Python>=3.11](https://www.python.org/downloads/) and [Poetry>=1.6.1](https://python-poetry.org/) as a dependency manager.

Check out Poetry's [documentation on how to install it](https://python-poetry.org/docs/#installation) on your system before proceeding.

To install requirements:

```sh
poetry install
```

This will install all requirements for running the package, linting, formatting and tests.

### IDE configuration

The recommended IDE is [VSCode](https://code.visualstudio.com/).
Open the project in VSCode and install the recommended extensions.

The VSCode is configured to use PEP-8 compatible formatter [Black](https://black.readthedocs.io/en/stable/index.html).

Alternatively you can use [PyCharm](https://www.jetbrains.com/pycharm/).

Set-up the Black formatter for PyCharm [manually](https://black.readthedocs.io/en/stable/integrations/editors.html#pycharm-intellij-idea) or
install PyCharm>=2023.2 with [built-in Black support](https://blog.jetbrains.com/pycharm/2023/07/2023-2/#black).

### Make on Windows

As of now, Windows distributions do not include the make tool. To run make commands, the tool can be installed using
the following command (since [Windows 10](https://learn.microsoft.com/en-us/windows/package-manager/winget/)):

```sh
winget install GnuWin32.Make
```

For convenience, the tool folder can be added to the PATH environment variable as `C:\Program Files (x86)\GnuWin32\bin`.
The command definitions inside Makefile should be cross-platform to keep the development environment setup simple.

## Run

Run the development server locally:

```sh
make serve
```

Run the development server in Docker:

```sh
make docker_serve
```

Open `localhost:5001/docs` to make sure the server is up and running.

## Lint

Run the linting before committing:

```sh
make lint
```

To auto-fix formatting issues run:

```sh
make format
```

## Test

Run unit tests locally:

```sh
make test
```

Run unit tests in Docker:

```sh
make docker_test
```

Run integration tests locally:

```sh
make integration_tests
```

## Clean

To remove the virtual environment and build artifacts:

```sh
make clean
```

## Build docs

> ℹ️ for user libraries like SDK

To build the docs:

```sh
make docs
```

## Publish

> ℹ️ for user libraries like SDK

To publish the package to PyPI:

```sh
make publish
```