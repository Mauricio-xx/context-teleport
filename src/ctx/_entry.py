"""Smart entry point: CLI when interactive, MCP server when spawned over stdio."""

import sys


def main():
    if not sys.stdin.isatty() and len(sys.argv) == 1:
        from ctx.mcp.server import main as mcp_main

        mcp_main()
    else:
        from ctx.cli.main import app

        app()


if __name__ == "__main__":
    main()
