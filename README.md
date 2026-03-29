# mcp-keyguard 🔐

MCP server that protects your API keys from LLMs. Instead of exposing your real keys
to Claude, Cursor or any AI agent, KeyGuard stores them encrypted locally and injects
them transparently into HTTP requests.

**Your keys never leave your machine.**

## Why

Every time you use a third-party MCP server, you're trusting that code with your API
keys. KeyGuard eliminates that risk by acting as a local secure proxy.

## Tools

- `add_key` — Store an API key encrypted in the local vault
- `list_keys` — List stored aliases (values are never shown)
- `make_request` — Make authenticated HTTP requests (key injected server-side)
- `delete_key` — Remove a key from the vault

## Installation
```bash
pip install mcp httpx cryptography
```

Clone this repo and add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-keyguard": {
      "command": "python",
      "args": ["/path/to/mcp-keyguard/main.py"]
    }
  }
}
```

## Usage example

Ask Claude:
> "Use add_key to store my OpenAI key with alias 'openai',
>  header_name 'Authorization', header_prefix 'Bearer '"

Then:
> "Use make_request with alias 'openai' to call
>  https://api.openai.com/v1/models"

Claude never sees your real key.

## Security

- Keys are encrypted with Fernet (AES-128-CBC) and stored locally
- The encryption key lives in `vault.key` — never commit it to git
- All HTTP requests are made server-side with a 30s timeout
