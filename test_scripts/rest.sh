
function test_call() {
  MODEL=gpt-4o
  HOST=http://0.0.0.0:5006
  URL=${HOST}/openai/deployments/${MODEL}/chat/completions

  curl -X POST $URL -v \
    -H "api-key:dummy-key" \
    -d '{"model": "whatever", "temperature": 0.0, "messages":[{"role":"user", "content": "What is in the latest news?"}], "stream": true}'
}

test_call