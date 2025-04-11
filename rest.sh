
function test_call() {
  MODEL=app
  HOST=http://0.0.0.0:5006
  URL=${HOST}/openai/deployments/${MODEL}/chat/completions

  curl -X POST $URL \
    -H "api-key:dummy-key" \
    -d '{"model": "whatever", "temperature": 0.0, "messages":[{"role":"user", "content": "2+3=?"}], "stream": true}'
}

test_call