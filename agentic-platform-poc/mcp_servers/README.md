# MCP Servers

This directory is a placeholder for OSS MCP server configurations.

The POC uses external MCP servers that are pointed at your hosted databases:

## MariaDB MCP Server
- Use the [mysql-mcp-server](https://github.com/nicholasgasior/mysql-mcp-server) or equivalent
- Point it at your Railway MariaDB instance
- The gateway proxies requests to it with permission enforcement

## Memory MCP Server
- Use the [supabase-mcp-server](https://github.com/supabase/supabase-mcp) or equivalent
- Point it at your Supabase pgvector instance
- The gateway adds async embedding on every exchange

## Running locally
Each MCP server runs as a separate process. Set their URLs in `.env`:

```
MCP_MARIADB_URL=http://localhost:8001
MCP_MEMORY_URL=http://localhost:8002
```
