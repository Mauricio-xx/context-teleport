# Reference

Complete API and configuration reference for Context Teleport.

## Interfaces

- **[CLI](cli.md)** -- All commands, subcommands, options, and examples
- **[MCP Tools](mcp-tools.md)** -- All 23 MCP tools with parameters, return values, and examples
- **[MCP Resources](mcp-resources.md)** -- All 13 resources with URI patterns and response schemas
- **[MCP Prompts](mcp-prompts.md)** -- All 4 prompts with descriptions and output format

## Data Model

- **[Schema](schema.md)** -- Pydantic models, versioning, and migrations
- **[Bundle Format](bundle-format.md)** -- `.context-teleport/` directory layout and file formats

## Extensibility

- **[Adapter Protocol](adapter-protocol.md)** -- `AdapterProtocol` interface and per-adapter details
- **[EDA Parsers](eda-parsers.md)** -- `EdaImporter` protocol and the 6 built-in parsers
- **[Source Importers](source-importers.md)** -- `SourceConfig`, `SourceItem`, and `GitHubSource`

## Settings

- **[Configuration](configuration.md)** -- Config file, defaults, and environment variables
