# now-util

MCP server exposing ServiceNow REST API capabilities as tools for AI assistants.

## Stack

- Python 3.12, managed with `uv`
- `FastMCP` (from `mcp[cli]`) for tool registration and stdio transport
- `httpx` for async HTTP, `python-dotenv` for credentials

## Structure

- `server.py` — all MCP tools and server entrypoint; this is the only substantive file
- `main.py` — unused stub, ignore
- `pyproject.toml` — entry point: `now-util = "server:main"`
- `.env.example` — documents required env vars

## Development

### Setup

```bash
cp .env.example .env  # fill in SN_INSTANCE, SN_USERNAME, SN_PASSWORD
uv sync
```

### Running

```bash
uv run python server.py   # start MCP server over stdio
```

For interactive testing via MCP Inspector:
- Command: `uv`, Arguments: `run --directory <abs-path> python server.py`

### Verification

Test the MCP handshake directly:
```bash
python3 -c "
import subprocess, json, select
proc = subprocess.Popen(['uv','run','python','server.py'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
def send(msg):
    proc.stdin.write((json.dumps(msg)+'\n').encode()); proc.stdin.flush()
    ready,_,_ = select.select([proc.stdout],[],[],5)
    return json.loads(proc.stdout.readline()) if ready else None
r = send({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'test','version':'0'}}})
print('server:', r['result']['serverInfo'])
proc.terminate()
"
```

## Patterns

- Tools registered with `@mcp.tool()` on `async def` functions; docstring becomes the tool description
- All tools are async and use `httpx.AsyncClient` per call
- Credentials fetched per-call via `_sn_credentials()` — raises `ValueError` if any env var is missing
- `_val(field, key)` normalizes SN API response fields (handles `{"value": "..."}` dict or plain string)
- Tools return JSON strings; use `json.dumps(...)` for structured output
