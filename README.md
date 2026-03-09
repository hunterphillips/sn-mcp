# sn-mcp

MCP server that gives AI coding assistants read access to a ServiceNow instance — useful when building or debugging ServiceNow apps.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — Python package manager
- A ServiceNow instance with a user that has read access to `sys_dictionary` and any tables you want to query

## Setup

```bash
git clone <this-repo>
cd sn-mcp
cp .env.example .env
```

Edit `.env` with your instance details:

```env
SN_INSTANCE=https://yourinstance.service-now.com
SN_USERNAME=your_username
SN_PASSWORD=your_password
```

## Adding to Claude

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "sn-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/sn-mcp", "sn-mcp"],
      "env": {
        "SN_INSTANCE": "https://yourinstance.service-now.com",
        "SN_USERNAME": "your_username",
        "SN_PASSWORD": "your_password"
      }
    }
  }
}
```

> You can use either the `env` block above **or** a `.env` file in the repo directory — whichever you prefer.

### Claude Code (CLI)

```bash
claude mcp add sn-mcp -- uv run --directory /absolute/path/to/sn-mcp sn-mcp
```

Then set credentials in `.env` or pass them via the `env` block in `.mcp.json`.

## Tools

| Tool                                          | Description                                                                                           |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `get_table_schema(table, filter_keyword?)`    | Field definitions for any table from `sys_dictionary` — type, label, mandatory, max_length, reference |
| `query_table(table, query?, fields?, limit?)` | Query any table with an encoded query string (e.g. `state=1^category=network`)                        |
| `get_record(table, sys_id)`                   | Fetch a single record by sys_id from any table                                                        |

## Verify it's working

```bash
uv run python server.py
```

Or test the MCP handshake directly:

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
