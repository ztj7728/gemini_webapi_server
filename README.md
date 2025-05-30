# OpenAI-Compatible API Server

A FastAPI-based REST API server that provides OpenAI-compatible endpoints powered by Google Gemini through the `gemini_webapi` integration.

## Features

- **OpenAI-Compatible Endpoints**: `/v1/chat/completions` and `/v1/models`
- **Streaming Support**: Server-Sent Events for real-time response streaming
- **Bearer Token Authentication**: Standard API key authentication with `sk-` prefix
- **Async/Await Architecture**: High-performance async request handling
- **Comprehensive Error Handling**: Proper HTTP status codes and error responses
- **Auto-Refresh Integration**: Seamless integration with gemini_webapi's credential management
- **Configurable Logging**: Structured logging with multiple levels

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Obtain Gemini Credentials

Run the credential extraction script to get your Google Gemini session cookies:

```bash
python get_certificate.py
```

This will open a browser where you can log into Google Gemini. After login, press Enter in the terminal to extract the credentials to `.env`.

### 3. Start the Server

```bash
python start_server.py
```

The server will start on `http://localhost:8000` by default.

### 4. Test the API

#### Using curl:

```bash
# List available models
curl -H "Authorization: Bearer sk-demo1234567890abcdef1234567890abcdef1234567890abcdef" \
     http://localhost:8000/v1/models

# Chat completion (non-streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo1234567890abcdef1234567890abcdef1234567890abcdef" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'

# Chat completion (streaming)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo1234567890abcdef1234567890abcdef1234567890abcdef" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ],
    "stream": true
  }'
```

#### Using OpenAI Python Client:

```python
from openai import OpenAI

# Initialize client with your local server
client = OpenAI(
    api_key="sk-demo1234567890abcdef1234567890abcdef1234567890abcdef",
    base_url="http://localhost:8000/v1"
)

# Chat completion
response = client.chat.completions.create(
    model="gemini-2.0-flash",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response.choices[0].message.content)

# Streaming chat completion
stream = client.chat.completions.create(
    model="gemini-2.0-flash",
    messages=[
        {"role": "user", "content": "Tell me a story"}
    ],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

## API Endpoints

### Chat Completions

**POST** `/v1/chat/completions`

OpenAI-compatible chat completions endpoint that supports both streaming and non-streaming responses.

**Request Body:**
```json
{
  "model": "gemini-2.0-flash",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1000
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gemini-2.0-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

### Models

**GET** `/v1/models`

Lists available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "gemini-2.0-flash",
      "object": "model",
      "created": 1677610602,
      "owned_by": "google"
    }
  ]
}
```

### Health Check

**GET** `/health`

Service health check endpoint.

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Gemini Credentials (automatically managed)
SECURE_1PSID=your_psid_here
SECURE_1PSIDTS=your_psidts_here

# Proxy Configuration
# Set to your proxy URL or comment out/set to empty to disable proxy
PROXY=http://127.0.0.1:15665

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# API Keys (optional - comma-separated custom API keys)
# API_KEYS=sk-your-custom-key1,sk-your-custom-key2
```

### Default API Keys

For development, the server includes demo API keys:
- `sk-demo1234567890abcdef1234567890abcdef1234567890abcdef`
- `sk-test1234567890abcdef1234567890abcdef1234567890abcdef`

## Architecture

The server follows a modular architecture:

```
├── app.py                 # Main FastAPI application
├── config.py             # Configuration management
├── start_server.py       # Server startup script
├── models/               # Pydantic models for request/response schemas
│   ├── __init__.py
│   └── openai_models.py
├── services/             # Business logic services
│   ├── __init__.py
│   └── gemini_service.py # Gemini integration service
├── auth/                 # Authentication services
│   ├── __init__.py
│   └── auth_service.py   # Bearer token authentication
└── utils/                # Utility functions
    ├── __init__.py
    └── logging_config.py # Logging configuration
```

## Integration with Existing gemini_webapi

The server seamlessly integrates with the existing `gemini_webapi` files:

- **Credential Management**: Uses the same `.env` file and credential format as `main.py` and `get_certificate.py`
- **Auto-Refresh**: Leverages gemini_webapi's auto-refresh capability for credential management
- **Proxy Support**: Supports the same proxy configuration as the existing integration

## Error Handling

The API returns OpenAI-compatible error responses:

```json
{
  "error": {
    "message": "Invalid API key provided",
    "type": "invalid_request_error",
    "param": null,
    "code": "invalid_api_key"
  }
}
```

Common error codes:
- `401 Unauthorized`: Invalid or missing API key
- `400 Bad Request`: Invalid request format or parameters
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server-side errors
- `503 Service Unavailable`: Gemini service unavailable

## Development

### Running in Development Mode

```bash
# Enable auto-reload
export RELOAD=true
python start_server.py
```

### Logging

The server uses structured logging. Set the log level with:

```bash
export LOG_LEVEL=DEBUG
```

Available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

## Production Deployment

For production deployment:

1. Set secure API keys in environment variables
2. Configure proper proxy settings if needed
3. Set up reverse proxy (nginx) for SSL termination
4. Configure monitoring and alerting
5. Set up log aggregation

## Troubleshooting

### Common Issues

1. **"Missing SECURE_1PSID or SECURE_1PSIDTS"**
   - Run `python get_certificate.py` to obtain credentials

2. **"Gemini client initialization failed"**
   - Check your internet connection
   - Verify proxy settings
   - Ensure credentials are valid

3. **"Authentication service not available"**
   - Check server startup logs
   - Verify API key format (must start with `sk-`)

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export LOG_LEVEL=DEBUG
python start_server.py
```

## License

This project integrates with and extends the existing gemini_webapi functionality. Please refer to the original project's license terms.