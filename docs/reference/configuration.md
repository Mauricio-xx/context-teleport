# Configuration

Context Teleport uses a layered configuration system with global defaults and per-project overrides.

## Global configuration

Global config is stored at `~/.config/ctx/config.json`. Manage it via the CLI:

```bash
# List all settings
context-teleport config list

# Get a specific setting
context-teleport config get default_strategy

# Set a value
context-teleport config set default_strategy theirs
```

### Available settings

| Key | Default | Description |
|-----|---------|-------------|
| `default_strategy` | `ours` | Default merge strategy for `pull`. Values: `ours`, `theirs`, `interactive`, `agent` |
| `default_scope` | `public` | Default scope for new entries. Values: `public`, `private`, `ephemeral` |

### Config file format

```json
{
  "default_strategy": "ours",
  "default_scope": "public"
}
```

## Project configuration

Project-level settings are stored in the manifest (`manifest.json`) within the `.context-teleport/` directory. These are set during `context-teleport init` and synced via git.

### Manifest settings

| Field | Description |
|-------|-------------|
| `project.name` | Project display name |
| `project.repo_url` | Git remote URL for sync |
| `adapters` | Per-adapter enable/disable settings |
| `team.members` | List of team members |

Access via dotpath:

```bash
context-teleport get manifest.project.name
context-teleport set manifest.project.repo_url git@github.com:team/project.git
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `MCP_CALLER` | Agent identity for attribution. Set automatically by adapter registration. Format: `mcp:<tool-name>` (e.g., `mcp:claude-code`) |
| `CTX_NO_AUTO_INIT` | Set to `1` to disable automatic store initialization when the MCP server starts in a git repo without a `.context-teleport/` directory. The server will return an error instead of silently creating a store. |
| `PDK_ROOT` | EDA: Path to PDK installation. Used by EDA project detection |

## Per-project preferences

### Team preferences (`preferences/team.json`)

Synced via git. Shared across all team members.

```bash
context-teleport set preferences.team.style "concise"
```

### User preferences (`preferences/user.json`)

Gitignored. Local to the machine.

```bash
context-teleport set preferences.user.editor "vim"
```

## Scope defaults

The default scope for new entries is `public`. Change it globally:

```bash
context-teleport config set default_scope private
```

Or per-entry at creation time:

```bash
# CLI
context-teleport knowledge set my-notes "..." --scope private

# MCP tool
context_add_knowledge(key="my-notes", content="...", scope="private")
```

## Merge strategy defaults

The default merge strategy is `ours` (keep local on conflict). Change it globally:

```bash
context-teleport config set default_strategy theirs
```

Or per-operation:

```bash
context-teleport pull -s agent
```
