# Watch & Automation

Context Teleport includes a file watcher that monitors the `.context-teleport/` directory and automatically commits and pushes changes to git. This keeps your context store synchronized without manual intervention.

## The Watch Command

```bash
context-teleport watch
```

This starts a foreground process that monitors the context store directory for any file changes. When changes are detected, it waits for a debounce period (to batch rapid writes), then commits and pushes.

### Options

| Flag | Default | Description |
|---|---|---|
| `--debounce`, `-d` | `5.0` | Seconds to wait after the last change before syncing |
| `--interval`, `-i` | `2.0` | Polling interval in seconds (polling mode only) |
| `--no-push` | `false` | Only commit locally, do not push to remote |

### Examples

```bash
# Default behavior: watch, commit, and push
context-teleport watch

# Faster reaction time (1s debounce, 0.5s polling)
context-teleport watch --debounce 1 --interval 0.5

# Local commits only, no push (useful without a remote)
context-teleport watch --no-push
```

## Filesystem Backend

The watcher uses one of two backends depending on what is available:

### Watchdog (Preferred)

If the `watchdog` Python package is installed, the watcher uses native filesystem events. This is more efficient and reacts faster than polling.

Install watchdog via the optional dependency:

```bash
pip install context-teleport[watch]
```

With watchdog, the `--interval` flag is ignored. The debounce timer starts from the last filesystem event.

### Polling (Fallback)

If watchdog is not installed, the watcher falls back to a polling loop that checks for git-tracked changes every `--interval` seconds. This works everywhere but uses slightly more CPU and has higher latency.

The watcher prints which mode it is using on startup:

```
Watching /path/to/.context-teleport (watchdog, debounce 5.0s)
```

or:

```
Watching /path/to/.context-teleport (polling every 2.0s, debounce 5.0s)
```

## Lifecycle

1. **Startup**: The watcher performs an initial sync (commit + push) to capture any pending changes.
2. **Running**: Changes are batched via the debounce window and synced automatically.
3. **Shutdown** (`Ctrl+C`): The watcher performs a final sync before exiting, so no changes are lost.

> **Note:** The watch command requires an initialized context store. Run `context-teleport init` first if you have not already.

## Running in the Background

The watch command is a foreground process by design. To run it persistently, use a terminal multiplexer or process manager.

### With tmux

```bash
tmux new-session -d -s ctx-watch 'context-teleport watch'

# Attach later to check status
tmux attach -t ctx-watch
```

### With screen

```bash
screen -dmS ctx-watch context-teleport watch

# Reattach later
screen -r ctx-watch
```

### With systemd (User Unit)

For persistent operation on Linux, create a user systemd service:

```ini
# ~/.config/systemd/user/ctx-watch.service
[Unit]
Description=Context Teleport Watcher
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/venv/bin/context-teleport watch
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now ctx-watch
systemctl --user status ctx-watch
```

## CI/CD Patterns

The CLI can be used in CI pipelines to automate context updates. While `watch` is designed for interactive development, the underlying `push` and `pull` commands work well in scripts.

### Sync Context in CI

```bash
# In your CI pipeline
pip install context-teleport

# Pull latest context before the job
context-teleport pull

# ... run your build/test steps ...

# Push any updates generated during the job
context-teleport push
```

### Import EDA Results in CI

After a synthesis or signoff run completes in CI, import the results automatically:

```bash
# After LibreLane flow completes
context-teleport import eda results/signoff/${DESIGN_NAME}.drc
context-teleport import eda results/signoff/${DESIGN_NAME}.lvs
context-teleport import eda results/metrics.json

# Commit and push
context-teleport push
```

### Import GitHub Issues on Schedule

A scheduled CI job can periodically import new issues:

```bash
# Cron job or scheduled pipeline
context-teleport import github \
  --repo owner/repo \
  --state all \
  --since $(date -d '7 days ago' +%Y-%m-%d) \
  --limit 100

context-teleport push
```

## Combining Watch with Multi-Agent Workflows

When multiple agents are working on the same project (e.g., Claude Code and Cursor on different tasks), the watcher ensures that context written by one agent is committed and pushed promptly. The other agent can then pull the latest context on its next MCP interaction.

A typical setup:

```
Terminal 1: context-teleport watch
Terminal 2: Claude Code (writing knowledge via MCP)
Terminal 3: Cursor (reading knowledge via MCP)
```

The MCP server itself performs a best-effort push on shutdown via its lifespan handler, but the watch command provides continuous synchronization while agents are actively working.

## Troubleshooting

**"Context store not initialized"**: Run `context-teleport init <project-name>` before starting the watcher.

**Changes not pushing**: If there is no git remote configured, the watcher commits locally but cannot push. Use `--no-push` explicitly to suppress the warning, or add a remote with `git remote add origin <url>`.

**High CPU usage with polling**: Install watchdog (`pip install context-teleport[watch]`) to switch to event-based monitoring.

**Debounce too aggressive**: If you need near-instant sync, reduce debounce to 1 second: `context-teleport watch --debounce 1`. Setting it to 0 is not recommended as it may cause excessive commits during rapid edits.
