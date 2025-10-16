# unifero-cli

<p align="center">
  <img src="./public/unifero.png" alt="unifero logo" width="220" />
</p>

Unifero-CLI is a compact Python toolkit that brings web-search and documentation crawling into a single, easy to use tool. It focuses on safely extracting technical content and code snippets from result pages or documentation sites. The project provides:

- a modern CLI (`main.py`),
- a FastAPI wrapper (`api.py`) for HTTP-based automation and testing, and
- a Python class interface (`tools.unifero.UniferoTool`) for direct programmatic use.

## Table of contents

- Features
- Installation
- Quick examples (CLI and API)
- Inputs & Outputs (examples)
- Edge cases, limitations & behavior
- Error handling and retry policy
- Troubleshooting
- Development & tests
- Project structure

## Features

- Search mode (DuckDuckGo) with result content extraction.
- Docs mode: crawl a base documentation URL and gather pages + code blocks.
- Code-aware extraction: preserves `<pre>`/`<code>` blocks and returns them as fenced Markdown blocks in the output.
- Multiple interfaces: CLI, HTTP API, and programmatic use.
- Networking robustness: connection retries, timeouts and basic backoff for transient failures.
- Output options: pretty JSON, compact JSON, and writing to a file.

## Installation

Requirements:

- Python 3.8+ (recommended)
- A virtual environment is strongly recommended

Install and set up:

```bash
cd /path/to/unifero-cli
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Tip: on macOS and Linux use `source .venv/bin/activate`. For zsh this is the same. Pick the `.venv` interpreter for your editor (VS Code) to avoid "import not found" warnings.

## Quick examples

CLI: run a quick search

```bash
source .venv/bin/activate
python3 main.py --search "Python FastAPI" --limit 3
```

CLI: crawl docs and save to file

```bash
python3 main.py --docs "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot" --output docs_result.json
```

Start the API server (development):

```bash
source .venv/bin/activate
uvicorn api:app --reload
```

HTTP example (POST body JSON):

```json
{
  "mode": "docs",
  "url": "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot",
  "limit": 2,
  "include_content": true
}
```

You can POST this to `http://127.0.0.1:8000/process` and receive the same structure the CLI prints.

## Inputs and outputs (examples)

1. Search mode input (CLI):

```bash
python3 main.py --search "Next.js routing" --limit 2
```

Search mode JSON output (truncated):

````json
{
  "mode": "search",
  "query": "Next.js routing",
  "results": [
    {
      "title": "Next.js — Routing",
      "url": "https://nextjs.org/docs/routing",
      "snippet": "...routing basics...",
      "content": "# Page title\nSome intro text\n```js\n// code block captured from the page\n```"
    }
  ]
}
````

2. Docs mode input (HTTP body):

```json
{
  "mode": "docs",
  "url": "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot",
  "limit": 3,
  "include_content": true
}
```

Docs mode JSON output (truncated):

````json
{
  "mode": "docs",
  "base_url": "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot",
  "results": [
    {
      "url": "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot",
      "title": "AI SDK UI: Chatbot",
      "content": "# AI SDK UI: Chatbot\nSome description...\n```js\nconst chat = useChat(...);\n```",
      "fetched": true
    },
    {
      "url": "https://ai-sdk.dev/docs/ai-sdk-ui/usage",
      "title": "Usage",
      "content": "...",
      "fetched": true
    }
  ]
}
````

Notes on output fields:

- `results`: list of pages (search results or crawled docs pages).
- Each result includes `url`, `title`, `snippet` (search mode), and `content` when `include_content` is true. `content` is a Markdown-ready string with fenced code blocks for extracted code.
- `fetched`: (docs mode) boolean indicating whether the page content was successfully fetched and parsed. If false, the `error` field may provide a short message.

### Additional fields & wrapper metadata

You may also see several additional fields in the CLI/API outputs and test artifacts (for example in `output.txt`). These are emitted by the runner/test harness and the core tool to help clients and debugging tools interpret results:

- `favicon` (per-result): URL to the site's favicon, when available. Useful for UI lists where a compact site icon is shown.
- `og_image` (per-result): URL of the Open Graph image (og:image) if discovered in the page metadata.
- `base_url` (top-level for `docs`): the exact base URL you requested for docs mode. The tool ensures the requested base URL appears in results even if the crawler doesn't discover it.
- `status_code` (wrapper): the HTTP-like status code returned by the wrapper (e.g., 200 for success, 400 for invalid input). This is not the target site's HTTP code but the wrapper's response code.
- `name` and `request` (wrapper): the test-runner or wrapper may produce a `name` label for the run and echo the `request` payload so you can trace which input produced the output.
- `response` (wrapper): when present, this contains the same structured object that the CLI/API returns (the `results` array, etc.).
- `elapsed` (wrapper): number of seconds the operation took. Useful for performance logging.
- `attempts` (wrapper): how many network/operation attempts were made (useful if retries occured).

Example (truncated from a test runner):

```json
{
  "name": "search_minimal",
  "request": {"mode":"search","query":"Next.js routing"},
  "status_code": 200,
  "response": { "query":"Next.js routing", "results": [ ... ] },
  "elapsed": 1.58,
  "attempts": 1
}
```

How to interpret these fields:

- The `response` object is the canonical output your client should consume. Wrapper-level metadata (`name`, `status_code`, `elapsed`, `attempts`, `request`) are intended for test harnesses, logging, or UI telemetry.
- Per-result `favicon` and `og_image` are optional and may be null when the page doesn't declare them or the fetch/parsing failed.
- When `fetched` is false for a result you can check `error` for a short message; wrapper metadata still helps diagnose network timeouts or retry behavior.

## Edge cases, limitations & behavior

1. Single-page docs sites (SPA) and client-rendered content:

- The tool fetches server-side HTML only. If a docs site is heavily client-side rendered (content injected via JavaScript), the tool will likely only see the initial shell and will miss the dynamically rendered content. Use the `fetched: false`/`error` signals to detect this.

2. Robots/toS and politeness:

- This tool does not implement robots.txt parsing or aggressive rate-limiting. It's intended for small-scale testing. For production crawling, add robots parsing, proper rate limits, and caching.

3. Rate limits and blocking:

- Repeated automated requests to the same host may trigger rate-limiting or blocking. The tool uses a short retry/backoff for transient HTTP failures, but it's not stealthy: respect the target site's policies.

4. Duplicate or noisy content:

- Some pages (headers, footers, menus) contain repeated content; the tool attempts to focus on main `<article>` or visible containers but may return noise on poorly structured pages.

5. Redirects and base URL normalization:

- `docs` mode always includes the exact `base_url` requested as the first result (even if it wasn't discovered by the internal crawler). Redirects are followed by the HTTP client; `results` will contain the final fetched URL.

6. Maximum crawl size:

- To avoid runaway crawls, `limit` is capped (default 5, enforced max 10). If you need larger crawls, modify the code carefully and add rate-limiting.

## Error handling and retry policy

Overview:

- Network calls use a session with retries for transient errors (connection resets, 5xx responses). The retry policy has a small backoff and a limited number of retries.
- Timeouts are applied to HTTP requests. If a request times out, the page is marked with `fetched: false` and an `error` message.

Common error fields returned in `docs` results (per page):

- `fetched`: boolean (true when parsing succeeded)
- `error`: short string describing the failure (network error, timeout, parse failure)

Examples:

- When a page times out:

```json
{
  "url": "https://example.com/slow",
  "fetched": false,
  "error": "timeout after 10s"
}
```

- When a page is client-rendered and contains little server HTML:

```json
{
  "url": "https://spa.example/docs",
  "fetched": false,
  "error": "no usable content found - page may be client-rendered"
}
```

How the CLI/API surfaces errors:

- CLI prints a non-zero exit code when the top-level operation fails (for example, missing required arguments, invalid JSON input).
- For per-page failures, the operation still returns a 200 OK with the `results` list containing `fetched:false` entries; this allows clients to inspect partial success.

## Troubleshooting

- "import fastapi could not be resolved": make sure you selected the `.venv` interpreter in your editor and ran `pip install -r requirements.txt` inside the venv.
- If `pytest` cannot import local modules, set `PYTHONPATH=.` before calling pytest (or install the package into the venv).
- If extracted `content` lacks code blocks you expected, the page is likely client-rendered. Consider using a headless browser approach (not included) or point the tool at a direct source page that serves server-side HTML.

## Development & tests

Run unit tests:

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

Run the API integration script (requires the server to be running):

```bash
uvicorn api:app --reload
python3 scripts/test_api.py
```

## Project structure

```
unifero-cli/
├── assets/              # small assets (logo.svg)
├── main.py              # CLI entrypoint
├── api.py               # FastAPI wrapper
├── requirements.txt     # dependencies
├── tools/
│   ├── __init__.py
│   └── unifero.py       # core logic
├── tests/
│   └── test_main.py
└── scripts/
    └── test_api.py
```

## Contributing

Contributions welcome. Please include tests for bug fixes or new features. Keep `UniferoTool.process_request` contract stable if you rely on it from the CLI or API.

## License

MIT-style (open source). Use respectfully and add tests for changes.

# unifero-cli

A powerful CLI toolkit for web searches and documentation crawling with enhanced code extraction capabilities.

## Features

- **Smart Web Search**: DuckDuckGo-based search with content extraction from result pages
- **Documentation Crawling**: Crawl documentation sites and extract structured content
- **Code Extraction**: Enhanced HTML parsing specifically designed to capture code snippets and technical content
- **Multiple Interfaces**: Modern CLI, legacy JSON input, REST API, and Python library
- **Robust Networking**: Built-in retries, timeout handling, and error recovery
- **Flexible Output**: Pretty JSON, compact JSON, or file output

## Installation

**Requirements:**

- Python 3.8+
- Virtual environment recommended

**Setup:**

```bash
# Clone or download the project
cd unifero-cli

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```bash
# Activate environment
source .venv/bin/activate

# Quick search
python3 main.py --search "Next.js routing"

# Documentation crawl with code extraction
python3 main.py --docs "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot"

# Save results to file
python3 main.py --search "Python FastAPI" --output results.json

# Show all examples
python3 main.py --examples
```

## Usage

### Modern CLI Interface

The enhanced CLI supports intuitive command-line arguments:

**Search mode:**

```bash
# Basic search
python3 main.py --search "Next.js routing"

# Advanced search with options
python3 main.py --search "React hooks" --limit 5 --snippet-len 200 --content-len 3000

# Compact output
python3 main.py --search "Python FastAPI" --compact

# Save to file
python3 main.py --search "Vue.js components" --output search_results.json
```

**Docs mode:**

```bash
# Basic docs crawl
python3 main.py --docs "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot"

# Advanced docs with options
python3 main.py --docs "https://nextjs.org/docs" --limit 3 --content-limit 2000

# Docs without content (URLs only)
python3 main.py --docs "https://example.com/docs" --no-content
```

**Help and examples:**

```bash
# Show help
python3 main.py --help

# Show all examples
python3 main.py --examples
```

### Legacy JSON Interface

For backward compatibility, JSON input is still supported:

```bash
# JSON as argument
python3 main.py '{"mode":"search","query":"Next.js routing","limit":3}'

# JSON via environment variable
export UNIFERO_JSON='{"mode":"docs","url":"https://example.com/docs"}'
python3 main.py

# JSON via pipe
echo '{"mode":"search","query":"test"}' | python3 main.py
```

## Programmatic API

Use the `UniferoTool` class directly from Python code:

```python
from tools.unifero import UniferoTool

tool = UniferoTool()
resp = tool.process_request({
    "mode": "search",
    "query": "Next.js routing",
    "limit": 2
})
print(resp)
```

The `process_request` method accepts a dict with these keys:

- mode: `search` (default) or `docs`
- query: search query (required for `search`)
- limit: maximum number of results
- url: base url for `docs` mode
- include_content: whether to fetch page content for docs

## API Modes

### Search Mode

Performs DuckDuckGo search and extracts content from result pages.

**Parameters:**

- `query` (required): Search query string
- `limit`: Maximum number of results (default: 5)
- `snippet_len`: Maximum snippet length (default: 300)
- `content_len`: Maximum content length (default: 2000)

### Docs Mode

Crawls documentation sites and extracts structured content with code blocks.

**Parameters:**

- `url` (required): Base documentation URL
- `limit`: Maximum pages to crawl (default: 5, max: 10)
- `include_content`: Whether to fetch page content (default: true)
- `content_limit`: Maximum content length per page (default: 2000)

## Development

### Running Tests

```bash
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

### API Testing

A comprehensive test suite is available for the FastAPI server:

```bash
# Start the API server
uvicorn api:app --reload

# In another terminal, run the test suite
python3 scripts/test_api.py
```

## Deployment to Vercel

This project includes configuration for easy deployment to Vercel as a serverless FastAPI application.

### Prerequisites

1. A [Vercel account](https://vercel.com)
2. Vercel CLI installed: `npm i -g vercel`
3. Your project pushed to a Git repository (GitHub, GitLab, or Bitbucket)

### Quick Deployment

1. **Test locally first:**

   ```bash
   source .venv/bin/activate
   ./deploy.sh
   ```

   This will start a local development server at `http://localhost:8000`

2. **Deploy to Vercel:**

   ```bash
   # Login to Vercel (one time setup)
   vercel login

   # Deploy from your project directory
   vercel

   # For production deployment
   vercel --prod
   ```

### Deployment Files

The following files configure Vercel deployment:

- `vercel.json`: Main Vercel configuration
- `runtime.txt`: Specifies Python version (3.11)
- `.vercelignore`: Files to exclude from deployment
- `requirements.txt`: Python dependencies

### API Endpoints

Once deployed, your API will have these endpoints:

- `GET /health`: Health check endpoint
- `POST /process`: Main API endpoint for processing requests
- `GET /docs`: FastAPI auto-generated documentation
- `GET /redoc`: Alternative API documentation

### Example Usage

After deployment, you can use your API like this:

```bash
# Health check
curl https://your-app.vercel.app/health

# Search request
curl -X POST https://your-app.vercel.app/process \
  -H "Content-Type: application/json" \
  -d '{"mode":"search","query":"Next.js routing","limit":3}'

# Docs request
curl -X POST https://your-app.vercel.app/process \
  -H "Content-Type: application/json" \
  -d '{"mode":"docs","url":"https://nextjs.org/docs","limit":2}'
```

### Environment Variables

If your application needs environment variables, you can set them in the Vercel dashboard or via CLI:

```bash
vercel env add VARIABLE_NAME
```

### Troubleshooting Deployment

- **Import errors**: Make sure all dependencies are in `requirements.txt`
- **Timeout issues**: Vercel has a 10-second timeout for serverless functions
- **Memory issues**: Consider reducing content limits for large documents
- **Module not found**: Ensure proper Python path structure

### Local Testing

Before deploying, always test locally:

```bash
# Start local development server
./deploy.sh

# Test endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"mode":"search","query":"test","limit":1}'
```

### Project Structure

```
unifero-cli/
├── main.py              # Enhanced CLI interface
├── api.py               # FastAPI server wrapper
├── requirements.txt     # Python dependencies
├── tools/
│   ├── __init__.py     # Package initialization
│   └── unifero.py      # Core extraction logic
├── tests/
│   └── test_main.py    # Unit tests
└── scripts/
    └── test_api.py     # API integration tests
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass: `PYTHONPATH=. pytest`
5. Submit a pull request

## License

Open source - contributions welcome. Keep changes focused and add tests for new functionality.
