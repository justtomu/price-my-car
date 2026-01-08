# Price My Car API

AI-powered car pricing API using LLM for make/model extraction from car listings.

## Features

- 🤖 **LLM-based extraction**: Uses LangChain with Ollama (dev) or OpenAI (prod) to extract car make/model
- ⚡ **Fast caching**: Redis-based caching for repeated queries
- 📊 **Comprehensive metrics**: Request, cache, LLM, and performance statistics
- 🔒 **Rate limiting**: Configurable rate limits per client
- 🏗️ **Clean architecture**: Provider/Service/API layer separation
- 🐳 **Docker ready**: Full docker-compose setup with Ollama and Redis
- ✅ **Well tested**: 80%+ code coverage with unit and integration tests

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Docker & Docker Compose (for local development)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/price-my-car.git
cd price-my-car

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv sync --all-extras

# Copy environment file
cp .env.example .env
```

### Running with Docker (Recommended)

```bash
# Start all services (app, redis, ollama)
docker-compose up -d

# Wait for Ollama to download the model (first time ~5 minutes)
docker-compose logs -f ollama

# Check service status
docker-compose ps

# View application logs
docker-compose logs -f app
```

### Running Locally

```bash
# Start Redis (if not using Docker)
redis-server

# Start the application
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Get Car Price

```bash
curl -X POST http://localhost:8000/price-car \
  -H "Content-Type: application/json" \
  -d '{
    "title": "2007 Honda Accord EX-L V6",
    "description": "Clean title, one owner, 150k miles, leather seats, runs great"
  }'
```

**Response:**
```json
{
  "make": "Honda",
  "model": "Accord",
  "price": 12500,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Health Check

```bash
curl http://localhost:8000/health
```

### Get Metrics

```bash
curl http://localhost:8000/health/metrics | jq .
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Configuration

All configuration is done via environment variables. See `.env.example` for all options.

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | `development` or `production` | `development` |
| `LLM_MODEL` | LLM model name | `llama3` (dev) / `gpt-4o-mini` (prod) |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API key | Required in production |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CACHE_TTL` | Cache TTL in seconds | `3600` |
| `LLM_TIMEOUT` | LLM request timeout | `5` |
| `RATE_LIMIT_PER_MINUTE` | Rate limit per client | `100` |

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/app --cov-report=html

# Run specific tests
uv run pytest tests/test_schemas.py -v
```

### Code Quality

```bash
# Format code
uv run black src/ tests/

# Lint code
uv run ruff check src/ tests/

# Type check
uv run mypy src/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run on all files
uv run pre-commit run --all-files
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                      │
│              (Endpoint handlers, request/response)           │
└─────────────────────────────────────────────────────────────┘
                            ▲
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
│         (LLMService, PricingService, CacheService)          │
└─────────────────────────────────────────────────────────────┘
                            ▲
┌─────────────────────────────────────────────────────────────┐
│                 DATA ACCESS / PROVIDER LAYER                │
│     (OllamaProvider, OpenAIProvider, Redis operations)      │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
price-my-car/
├── src/app/
│   ├── api/           # API routes and dependencies
│   ├── providers/     # LLM provider implementations
│   ├── services/      # Business logic services
│   ├── schemas/       # Pydantic models
│   ├── utils/         # Helpers and exceptions
│   ├── main.py        # FastAPI application
│   ├── settings.py    # Configuration
│   └── logger.py      # Logging setup
├── tests/             # Test suite
├── .github/workflows/ # CI/CD pipelines
├── docker-compose.yml # Local development setup
├── Dockerfile         # Production container
└── pyproject.toml     # Project dependencies
```

## Production Deployment

```bash
# Build Docker image
docker build -t price-my-car:latest .

# Run with production settings
docker run -d \
  -e ENVIRONMENT=production \
  -e OPENAI_API_KEY=sk-... \
  -e REDIS_URL=redis://prod-redis:6379 \
  -p 8000:8000 \
  price-my-car:latest
```

### With Gunicorn (Recommended)

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

## License

MIT License - see LICENSE file for details.
