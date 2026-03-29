# 🔐 mcp-keyguard

**Your AI agent should never see your API keys. Now it won't.**

mcp-keyguard is a local MCP server that acts as a secure proxy between 
your AI agent (Claude, Cursor, Windsurf...) and any external API.

Instead of pasting your OpenAI, Stripe or GitHub keys into the chat context,
you store them encrypted on your machine. The agent calls mcp-keyguard,
which injects the real key server-side and returns the result.

**The key never leaves your machine. The agent never sees it.**

---

## Why this matters

In 2025, a vulnerability in a popular MCP hosting platform exposed thousands
of API keys from over 3,000 servers. The root cause? Keys passed through
infrastructure the user didn't control.

mcp-keyguard is the opposite: fully local, zero external dependencies,
your keys encrypted at rest with AES-128.

---

## How it works
```
Your prompt → Claude → mcp-keyguard → [injects real key] → External API
                           ↑
                    Key never leaves here
```

---

## Installation

**Requirements:** Python 3.10+
```bash
pip install mcp httpx cryptography
git clone https://github.com/ggc180820/mcp-keyguard.git
cd mcp-keyguard
```

Add to your `claude_desktop_config.json`:
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

Restart Claude Desktop. Done.

---

## Usage

**1. Store a key (you do this once per key)**

> "Use add_key to store my OpenAI key with alias 'openai',  
> header_name 'Authorization', header_prefix 'Bearer '"

**2. Make authenticated requests (Claude does this automatically)**

> "Use make_request with alias 'openai' to call  
> https://api.openai.com/v1/models"

**3. Check what's stored**

> "Use list_keys"  
> → Shows aliases and headers. Never the real values.

---

## Tools

| Tool | What it does |
|---|---|
| `add_key` | Store an API key encrypted in the vault |
| `list_keys` | List stored aliases — values are never shown |
| `make_request` | Make an authenticated HTTP request, key injected server-side |
| `delete_key` | Remove a key from the vault |

---

## Security model

- Keys are encrypted with **Fernet (AES-128-CBC + HMAC-SHA256)**
- The encryption key lives in `vault.key` on your machine only
- All HTTP requests are made locally with a 30s timeout
- **Never commit `vault.key` or `vault.json` to git** (already in `.gitignore`)

---

## mcp-keyguard Pro

Need more control? Pro adds:

| Feature | Free | Pro |
|---|---|---|
| Encrypted local vault | ✅ | ✅ |
| Unlimited keys | ✅ | ✅ |
| Multiple vaults (per project/client) | ❌ | ✅ |
| Audit log (who used which key, when, where) | ❌ | ✅ |
| Key rotation alerts | ❌ | ✅ |

👉 **[Get Pro — 5€/month](https://buy.polar.sh/polar_cl_rOKtbDDGXIuZfyBFRXtcZh93UAUmblEoWY38L0d2WYr)** 

---

## License

MIT — free forever for personal use.
