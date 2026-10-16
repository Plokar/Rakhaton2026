"""MCP server MDT Copilot nad IRIS (T-308, ARCH §4.7). Nástroje: services/mcp/server.py.

    # stdio (Claude Desktop / Claude Code / jiný MCP klient), uvnitř dev stacku:
    docker compose -f docker-compose.dev.yml exec -T backend python mcp_server.py
    # streamable HTTP na http://localhost:8765/mcp (port je potřeba publikovat, jen lokálně / přes SSH tunel)
    docker compose -f docker-compose.dev.yml exec backend python mcp_server.py --http --port 8765
"""
import argparse
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / '.env')

from services.mcp.server import mcp  # noqa: E402  (env až po .env)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--http', action='store_true', help='streamable HTTP místo stdio')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.http:
        mcp.run(transport='http', host=args.host, port=args.port, show_banner=False)
    else:
        mcp.run(show_banner=False)


if __name__ == '__main__':
    main()
