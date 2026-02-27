# Adapter Protocol

Adapters provide bidirectional context transfer between the central store and tool-specific file formats. Each adapter implements `AdapterProtocol`, enabling import, export, and MCP registration for a specific agent tool.

## AdapterProtocol

Defined in `src/ctx/adapters/base.py`:

```python
@runtime_checkable
class AdapterProtocol(Protocol):
    name: str

    def detect(self) -> bool:
        """Check if this adapter's tool is installed and available."""

    def import_context(self, dry_run: bool = False) -> dict:
        """Extract context from the tool into the store."""

    def export_context(self, dry_run: bool = False) -> dict:
        """Inject store content into the tool's locations."""

    def mcp_config_path(self) -> Path | None:
        """Return the path to this tool's MCP config file."""

    def register_mcp(self, local: bool = False) -> dict:
        """Register context-teleport in the tool's MCP config."""

    def unregister_mcp(self) -> dict:
        """Remove context-teleport from the tool's MCP config."""
```

All adapters are instantiated with a `ContextStore` and the project root path.

## Adapter registry

The registry in `src/ctx/adapters/registry.py` provides:

- `detect_adapters()` -- Returns a list of all adapters whose `detect()` returns `True`
- `get_adapter(name)` -- Instantiates a specific adapter by name

Available adapter names: `claude-code`, `opencode`, `codex`, `gemini`, `cursor`.

## Per-adapter details

### Claude Code

| Aspect | Detail |
|--------|--------|
| **Name** | `claude-code` |
| **Imports from** | `MEMORY.md`, `CLAUDE.md`, `.claude/rules/*.md`, `.claude/skills/*/SKILL.md` |
| **Exports to** | `CLAUDE.md` (managed section with conventions + knowledge), `MEMORY.md`, `.claude/skills/` |
| **MCP config** | `.claude/mcp.json` |
| **Detection** | Checks for `.claude/` directory or `CLAUDE.md` file |

Import parses `MEMORY.md` and `CLAUDE.md` as knowledge entries. Rules files are imported with their filename as the key. Skills are imported as-is from `.claude/skills/*/SKILL.md`.

Export writes a managed section in `CLAUDE.md` delimited by markers:

```markdown
<!-- ctx:start -->
... generated content ...
<!-- ctx:end -->
```

### OpenCode

| Aspect | Detail |
|--------|--------|
| **Name** | `opencode` |
| **Imports from** | `AGENTS.md`, `.opencode/opencode.db` (SQLite sessions), `.opencode/skills/*/SKILL.md` |
| **Exports to** | `AGENTS.md` (managed section), `.opencode/skills/` |
| **MCP config** | `opencode.json` |
| **Detection** | Checks for `AGENTS.md` or `.opencode/` directory |

Session import reads from OpenCode's SQLite database to extract session history. Knowledge is imported from the `AGENTS.md` file.

### Codex

| Aspect | Detail |
|--------|--------|
| **Name** | `codex` |
| **Imports from** | `AGENTS.md`, `.codex/instructions.md`, `.codex/skills/*/SKILL.md` |
| **Exports to** | `AGENTS.md` (managed section), `.codex/skills/` |
| **MCP config** | Not supported |
| **Detection** | Checks for `AGENTS.md` or `.codex/` directory |

Codex does not support MCP server registration. The adapter only provides import/export functionality.

### Gemini

| Aspect | Detail |
|--------|--------|
| **Name** | `gemini` |
| **Imports from** | `.gemini/rules/*.md`, `.gemini/STYLEGUIDE.md`, `GEMINI.md`, `.gemini/skills/*/SKILL.md` |
| **Exports to** | `.gemini/rules/ctx-*.md`, `.gemini/skills/` |
| **MCP config** | `.gemini/settings.json` |
| **Detection** | Checks for `.gemini/` directory or `GEMINI.md` file |

Export writes each knowledge entry as `ctx-<key>.md` and each convention as `ctx-convention-<key>.md` in `.gemini/rules/`. The `ctx-` prefix distinguishes managed files from user-created rules.

### Cursor

| Aspect | Detail |
|--------|--------|
| **Name** | `cursor` |
| **Imports from** | `.cursor/rules/*.mdc` (MDC format), `.cursorrules`, `.cursor/skills/*/SKILL.md` |
| **Exports to** | `.cursor/rules/ctx-*.mdc`, `.cursor/skills/` |
| **MCP config** | `.cursor/mcp.json` |
| **Detection** | Checks for `.cursor/` directory or `.cursorrules` file |

Cursor uses MDC (Markdown with Context) format for rules files. The adapter handles parsing and generating MDC frontmatter. Export writes knowledge as `ctx-<key>.mdc` and conventions as `ctx-convention-<key>.mdc` with `alwaysApply: True`.

## Shared modules

### `_mcp_reg.py`

Handles JSON-based MCP config file registration. Used by Claude Code, OpenCode, Cursor, and Gemini adapters.

Core function: `register_mcp_json(config_path, server_name, command, args, env)` -- reads existing config, adds/updates the server entry, writes back.

When `local=True`, the command points to the local Python interpreter instead of `uvx`.

### `_agents_md.py`

Handles parsing and writing `AGENTS.md` files with managed sections. Used by OpenCode and Codex adapters.

Managed sections are delimited by HTML comments:

```markdown
<!-- ctx:start -->
## Project Context (managed by Context Teleport)
...
<!-- ctx:end -->
```

Content outside the markers is preserved during export.

## Import/export behavior

### Import

- Reads tool-specific files and creates corresponding store entries
- Each imported entry is attributed with `import:<tool>` as the author
- Skills are imported as-is (SKILL.md format is the cross-tool standard)
- Supports `--dry-run` to preview without writing

### Export

- Writes only **public-scope** entries to tool locations
- Conventions are exported **before** knowledge in all formats (higher priority)
- Preserves existing content outside managed sections
- Skills are exported as `SKILL.md` files in the tool's skills directory
- Supports `--dry-run` to preview without writing

Convention export formats per adapter:

| Adapter | Convention format |
|---------|-----------------|
| Claude Code | `### Team Conventions` section in `CLAUDE.md` managed block |
| Cursor | `.cursor/rules/ctx-convention-{key}.mdc` (`alwaysApply: True`) |
| Gemini | `.gemini/rules/ctx-convention-{key}.md` |
| OpenCode | `### convention: {key}` entries in `AGENTS.md` managed section |
| Codex | `### convention: {key}` entries in `AGENTS.md` managed section |

## MCP registration

Registration writes the MCP server config for the tool, including:

- **Command**: `uvx` (default) or local Python path (`--local`)
- **Args**: `["context-teleport"]`
- **Type**: `stdio`
- **Env**: `{"MCP_CALLER": "mcp:<tool-name>"}` for agent attribution

```bash
# Register with uvx (default)
context-teleport register claude-code

# Register with local install
context-teleport register claude-code --local

# Auto-detect and register all available tools
context-teleport register
```
