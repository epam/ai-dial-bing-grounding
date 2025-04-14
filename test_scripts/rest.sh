
function test_call() {
  MODEL=gpt-4o
  HOST=http://0.0.0.0:5006
  URL=${HOST}/openai/deployments/${MODEL}/chat/completions

  curl -X POST $URL -v \
    -H "api-key:dummy-key" \
    -d '{"model": "whatever", "temperature": 0.0, "messages":[{"role":"user", "content": "What is in the latest news?"}], "stream": true, "max_tokens": 16}'
}

function rest() {
  URL=https://eastus.api.azureml.ms/agents/v1.0/subscriptions/cac80694-eee4-49c2-963d-4789b6fa9867/resourceGroups/sbx-dial-rg-weu/providers/Microsoft.MachineLearningServices/workspaces/azure-ai-project-for-bing-ground/assistants?api-version=2024-12-01-preview
  KEY=7F0bhaIozqG7ButSX7QXnsIVTqbEpZI2X6F725Ir2J6piukhr8QSJQQJ99BDACYeBjFXJ3w3AAAAACOGjFxd

  curl -X POST $URL \
    -H api-key:${KEY}
}

# rest
test_call