import json
import os
import urllib.parse

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("sn-mcp", "1.0", description="A tool to query ServiceNow tables and metadata via the REST API.")


def _sn_credentials() -> tuple[str, str, str]:
    instance = os.environ.get("SN_INSTANCE", "").rstrip("/")
    username = os.environ.get("SN_USERNAME", "")
    password = os.environ.get("SN_PASSWORD", "")
    if not all([instance, username, password]):
        raise ValueError(
            "Missing ServiceNow credentials. Set SN_INSTANCE, SN_USERNAME, and SN_PASSWORD."
        )
    return instance, username, password


def _val(field: dict, key: str) -> str:
    v = field.get(key, "")
    return v.get("value", "") if isinstance(v, dict) else str(v or "")


@mcp.tool()
async def get_table_schema(table: str, filter_keyword: str = "") -> str:
    """Return field schema for a ServiceNow table from sys_dictionary.

    Args:
        table: ServiceNow table name (e.g. dmn_demand, sc_cat_item_producer)
        filter_keyword: Optional keyword to filter results by element name or column label
    """
    instance, username, password = _sn_credentials()

    query = f"name={table}^elementISNOTEMPTY^internal_type!=collection"
    fields = "element,column_label,internal_type,mandatory,max_length,reference"
    encoded_query = urllib.parse.quote(query)
    url = (
        f"{instance}/api/now/table/sys_dictionary"
        f"?sysparm_query={encoded_query}"
        f"&sysparm_fields={fields}"
        f"&sysparm_display_value=false"
        f"&sysparm_limit=300"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            auth=(username, password),
            headers={"Accept": "application/json"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    if "error" in data:
        return f"API Error: {data['error']}"

    all_fields = data.get("result", [])

    keyword = filter_keyword.lower()
    if keyword:
        all_fields = [
            f for f in all_fields
            if keyword in _val(f, "element").lower()
            or keyword in _val(f, "column_label").lower()
        ]

    all_fields.sort(key=lambda f: _val(f, "element"))

    fields_out = {}
    for f in all_fields:
        el = _val(f, "element")
        entry = {
            "type": _val(f, "internal_type"),
            "label": _val(f, "column_label"),
            "mandatory": _val(f, "mandatory") == "true",
            "max_length": _val(f, "max_length"),
        }
        ref = _val(f, "reference")
        if ref:
            entry["reference"] = ref
        fields_out[el] = entry

    return json.dumps({"table": table, "field_count": len(fields_out), "fields": fields_out})


@mcp.tool()
async def query_table(table: str, query: str = "", fields: str = "", limit: int = 50) -> str:
    """Run a parameterized query against any ServiceNow table.

    Args:
        table: Table name (e.g. incident, sc_request, cmdb_ci_server)
        query: Encoded query string (e.g. state=1^category=network)
        fields: Comma-separated field names to return; empty returns all fields
        limit: Max number of records (default 50, max 1000)
    """
    instance, username, password = _sn_credentials()
    params = f"?sysparm_limit={min(limit, 1000)}&sysparm_display_value=true"
    if query:
        params += f"&sysparm_query={urllib.parse.quote(query)}"
    if fields:
        params += f"&sysparm_fields={urllib.parse.quote(fields)}"
    url = f"{instance}/api/now/table/{table}{params}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(username, password), headers={"Accept": "application/json"}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        return f"API Error: {data['error']}"
    results = data.get("result", [])
    return json.dumps({"table": table, "count": len(results), "results": results})


@mcp.tool()
async def get_record(table: str, sys_id: str) -> str:
    """Fetch a single record by sys_id from any ServiceNow table.

    Args:
        table: Table name (e.g. incident, change_request)
        sys_id: The sys_id of the record
    """
    instance, username, password = _sn_credentials()
    url = f"{instance}/api/now/table/{table}/{sys_id}?sysparm_display_value=true"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, auth=(username, password), headers={"Accept": "application/json"}, timeout=30.0)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        return f"API Error: {data['error']}"
    return json.dumps(data.get("result", {}))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
