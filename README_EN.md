# X Feed Digest

[中文](README.md) | English

> Transform your X/Twitter following list into a curated daily digest with AI-powered analysis.

X Feed Digest is an open-source tool that fetches tweets from your X/Twitter following list and generates an intelligent summary using AI. It leverages Grok's real-time X data access to collect tweets and Claude's analytical capabilities to produce editor-quality digests.

## Features

- **CSV Upload**: Import your X/Twitter following list exported as CSV
- **Real-time Tweet Fetching**: Uses Grok API to fetch tweets from the past 24 hours
- **Multi-threaded Processing**: Concurrent batch processing for faster data collection
- **AI-Powered Summary**: Claude generates a curated digest with categorized insights
- **Job History**: Track and revisit all your previous digest jobs
- **Modern Web UI**: Clean Vue 3 interface with real-time progress tracking

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Upload CSV │ ──▶ │  Grok API   │ ──▶ │  Claude AI  │ ──▶ │   Digest    │
│ (Following) │     │ (Fetch 24h) │     │ (Summarize) │     │  (Output)   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

1. **Upload** your X/Twitter following list CSV (exported from X)
2. **Fetch** tweets from each user in the past 24 hours via Grok
3. **Analyze** collected tweets using Claude with an editor-style prompt
4. **Output** a structured digest with highlights, categories, and recommendations

## Tech Stack

### Backend
- **Python 3.10+** with FastAPI
- **OpenAI-compatible API client** for LLM integration
- **ThreadPoolExecutor** for concurrent processing
- **YAML-based configuration**

### Frontend
- **Vue 3** with Composition API
- **TypeScript** for type safety
- **Pinia** for state management
- **Element Plus** UI components
- **Vite** for fast development

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- API access to Grok and Claude (or compatible endpoints)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/ChineseLsh/x-feed-digest.git
cd x-feed-digest
```

2. **Install backend dependencies**
```bash
pip install -r requirements.txt
```

3. **Install frontend dependencies**
```bash
cd frontend
npm install
cd ..
```

4. **Configure API providers**

Copy the example config and add your API keys:
```bash
cp config/providers.example.yaml config/providers.yaml
```

Edit `config/providers.yaml`:
```yaml
providers:
  grok:
    type: openai_compatible
    api_key: your-grok-api-key
    base_url: https://api.x.ai/v1
    model: grok-2

  claude:
    type: openai_compatible
    api_key: your-claude-api-key
    base_url: https://api.anthropic.com/v1
    model: claude-sonnet-4-20250514
```

### Running the Application

1. **Start the backend**
```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 5001 --reload
```

2. **Start the frontend** (in a new terminal)
```bash
cd frontend
npm run dev
```

3. **Open your browser** at `http://localhost:3000`

## Configuration

### `config/app.yaml`

```yaml
storage:
  root: data
  uploads: data/uploads      # Uploaded CSV files
  outputs: data/outputs      # Fetched tweets CSV
  summaries: data/summaries  # Generated digests
  jobs: data/jobs            # Job status files

batching:
  default_batch_size: 10     # Users per batch
  max_batch_size: 50         # Maximum allowed batch size
  max_workers: 5             # Concurrent threads for API calls

retry:
  max_retries: 3             # Retry attempts on failure
  backoff_base_s: 0.5        # Base backoff time
  backoff_max_s: 8.0         # Maximum backoff time

grok:
  provider: grok             # Provider name from providers.yaml
  timeout_s: 120             # Request timeout
  temperature: 0.2           # LLM temperature

claude:
  provider: claude
  timeout_s: 120
  temperature: 0.3
```

### `config/providers.yaml`

Configure your LLM providers. Both Grok and Claude use OpenAI-compatible API format:

```yaml
providers:
  grok:
    type: openai_compatible
    api_key: ${GROK_API_KEY}      # Supports env var substitution
    base_url: https://api.x.ai/v1
    model: grok-2
    headers:                       # Optional custom headers
      X-Custom-Header: value

  claude:
    type: openai_compatible
    api_key: ${CLAUDE_API_KEY}
    base_url: https://api.anthropic.com/v1
    model: claude-sonnet-4-20250514
```

## CSV Format

The input CSV should contain your X/Twitter following list. Required column:
- `Handle` or `username` or `screen_name` - The Twitter handle

Optional columns (passed to Grok for context):
- `Name` - Display name
- `Bio` - User bio
- `Location` - User location
- `FollowersCount` - Follower count
- `FollowingCount` - Following count

Example:
```csv
Handle,Name,Bio,FollowersCount
elonmusk,Elon Musk,Mars & Cars,180000000
sama,Sam Altman,OpenAI CEO,3000000
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Create a new digest job (multipart form with CSV file) |
| `GET` | `/api/jobs` | List all job history |
| `GET` | `/api/jobs/{job_id}` | Get job status |
| `GET` | `/api/jobs/{job_id}/summary` | Get generated digest text |
| `GET` | `/api/jobs/{job_id}/download` | Download tweets CSV |

## Project Structure

```
x-feed-digest/
├── backend/
│   ├── api/
│   │   └── routes.py          # FastAPI routes
│   ├── core/
│   │   ├── config.py          # YAML config loader
│   │   └── storage.py         # File storage utilities
│   ├── llm/
│   │   └── openai_compatible.py  # LLM client
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── services/
│   │   ├── batch_fetcher.py   # Multi-threaded tweet fetcher
│   │   ├── csv_parser.py      # CSV parsing with encoding detection
│   │   └── summarizer.py      # AI digest generator
│   └── app.py                 # FastAPI app factory
├── frontend/
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # Vue components
│   │   ├── stores/            # Pinia stores
│   │   ├── types/             # TypeScript types
│   │   └── views/             # Page views
│   └── vite.config.ts
├── config/
│   ├── app.yaml               # Application config
│   └── providers.yaml         # LLM provider config
├── data/                      # Runtime data (gitignored)
└── requirements.txt
```

## Digest Output Format

The AI generates a structured digest including:

1. **Deep Brief** - A 100-200 word summary of the day's highlights
2. **Editor's Choice** - Top 3-5 curated items categorized as:
   - Tools - New developer tools and utilities
   - Insights - Deep technical or industry insights
   - News - Major announcements and updates
   - Resources - Learning materials and references
3. **Full List** - All valuable tweets with ratings (1-3 stars)

## Development

### Backend Development
```bash
# Run with auto-reload
python -m uvicorn backend.app:app --reload --port 5001

# Type checking
mypy backend/
```

### Frontend Development
```bash
cd frontend

# Development server
npm run dev

# Type checking
npm run type-check

# Build for production
npm run build
```

## Environment Variables

You can use environment variables in `providers.yaml`:

```bash
export GROK_API_KEY=your-key-here
export CLAUDE_API_KEY=your-key-here
```

Then reference them in config:
```yaml
api_key: ${GROK_API_KEY}
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- [Grok](https://x.ai/) for real-time X/Twitter data access
- [Claude](https://anthropic.com/) for intelligent summarization
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [Vue.js](https://vuejs.org/) for the frontend framework
- [Element Plus](https://element-plus.org/) for UI components