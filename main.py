import asyncio
import json
import os
import base64
import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from cryptography.fernet import Fernet

# --- Vault Configuration ---
VAULT_FILE = os.path.join(os.path.dirname(__file__), "vault.json")
KEY_FILE   = os.path.join(os.path.dirname(__file__), "vault.key")

def load_or_create_fernet() -> Fernet:
    """Loads the encryption key or creates it if it does not exist."""
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return Fernet(f.read())
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    return Fernet(key)

def load_vault() -> dict:
    if not os.path.exists(VAULT_FILE):
        return {}
    with open(VAULT_FILE, "r") as f:
        return json.load(f)

def save_vault(data: dict):
    with open(VAULT_FILE, "w") as f:
        json.dump(data, f, indent=2)

fernet = load_or_create_fernet()
server  = Server("mcp-keyguard")

# --- Tools ---

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="add_key",
            description=(
                "Saves an API key in the local encrypted vault. "
                "The key remains encrypted on disk and will never be visible in the chat. "
                "Use a short alias to identify it (e.g., 'openai', 'stripe')."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "Short name to identify the key (e.g., openai, stripe, github)"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "The real value of the API key to save encrypted"
                    },
                    "header_name": {
                        "type": "string",
                        "description": "Name of the HTTP header where the key will be injected (e.g., Authorization, X-API-Key)"
                    },
                    "header_prefix": {
                        "type": "string",
                        "description": "Optional prefix before the value (e.g., 'Bearer '). Leave empty if not applicable."
                    }
                },
                "required": ["alias", "api_key", "header_name"]
            }
        ),
        types.Tool(
            name="list_keys",
            description="Lists all aliases of keys saved in the vault. Does not show the real values.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="make_request",
            description=(
                "Makes an authenticated HTTP request using an API key from the vault. "
                "The AI never sees the real key: the server automatically injects it into the header. "
                "Supports GET, POST, PUT, DELETE, and PATCH."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "Alias of the API key to use (must exist in the vault)"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method"
                    },
                    "url": {
                        "type": "string",
                        "description": "Full URL of the endpoint to call"
                    },
                    "body": {
                        "type": "object",
                        "description": "JSON body of the request (optional, only for POST/PUT/PATCH)"
                    },
                    "extra_headers": {
                        "type": "object",
                        "description": "Optional additional headers (e.g., Content-Type)"
                    }
                },
                "required": ["alias", "method", "url"]
            }
        ),
        types.Tool(
            name="delete_key",
            description="Deletes an API key from the vault using its alias.",
            inputSchema={
                "type": "object",
                "properties": {
                    "alias": {
                        "type": "string",
                        "description": "Alias of the key to delete"
                    }
                },
                "required": ["alias"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):

    if name == "add_key":
        alias       = arguments["alias"].strip().lower()
        api_key     = arguments["api_key"]
        header_name = arguments["header_name"]
        prefix      = arguments.get("header_prefix", "")

        encrypted = fernet.encrypt(api_key.encode()).decode()
        vault = load_vault()
        vault[alias] = {
            "encrypted_key": encrypted,
            "header_name": header_name,
            "header_prefix": prefix
        }
        save_vault(vault)
        return [types.TextContent(
            type="text",
            text=f"Key '{alias}' successfully saved in the encrypted vault. The real value will never leave your machine."
        )]

    elif name == "list_keys":
        vault = load_vault()
        if not vault:
            return [types.TextContent(type="text", text="The vault is empty. Use add_key to save your first API key.")]
        lines = ["Keys saved in the vault:\n"]
        for alias, data in vault.items():
            lines.append(f"  • {alias} → header: {data['header_name']} | prefix: '{data.get('header_prefix','')}'")
        return [types.TextContent(type="text", text="\n".join(lines))]

    elif name == "make_request":
        alias  = arguments["alias"].strip().lower()
        method = arguments["method"].upper()
        url    = arguments["url"]
        body   = arguments.get("body")
        extra  = arguments.get("extra_headers", {})

        vault = load_vault()
        if alias not in vault:
            return [types.TextContent(type="text", text=f"Error: no key with alias '{alias}' exists in the vault.")]

        entry      = vault[alias]
        real_key   = fernet.decrypt(entry["encrypted_key"].encode()).decode()
        prefix     = entry.get("header_prefix", "")
        header_val = f"{prefix}{real_key}"

        headers = {entry["header_name"]: header_val, **extra}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.request(method, url, headers=headers, json=body)
            try:
                result = response.json()
                result_text = json.dumps(result, indent=2, ensure_ascii=False)
            except Exception:
                result_text = response.text

            return [types.TextContent(
                type="text",
                text=f"Status: {response.status_code}\n\nResponse:\n{result_text}"
            )]
        except httpx.TimeoutException:
            return [types.TextContent(type="text", text="Error: the request exceeded the 30-second timeout.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error making the request: {str(e)}")]

    elif name == "delete_key":
        alias = arguments["alias"].strip().lower()
        vault = load_vault()
        if alias not in vault:
            return [types.TextContent(type="text", text=f"No key exists with alias '{alias}'.")]
        del vault[alias]
        save_vault(vault)
        return [types.TextContent(type="text", text=f"Key '{alias}' deleted from the vault.")]

    raise ValueError(f"Unknown tool: {name}")

# --- Startup ---

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-keyguard",
                server_version="0.2.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())