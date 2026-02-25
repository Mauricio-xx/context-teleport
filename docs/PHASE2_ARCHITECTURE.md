# Phase 2: Architecture and Flow

## 1. High-level picture: what lives where

```
~/git/slim-pdk/IHP-Open-PDK/          ~/git/IHP-Open-DesignLib/
(branch: feature/context-teleport)     (branch: feature/context-teleport)
|                                      |
|-- .gitignore  (+ .context-teleport/) |-- .gitignore  (+ .context-teleport/)
|-- CLAUDE.md   (+ managed section)    |-- CLAUDE.md   (+ managed section)
|-- .claude/                           |-- .claude/
|   |-- mcp.json  (MCP registration)   |   |-- mcp.json
|   +-- skills/                        |   +-- skills/
|       |-- debug-drc/SKILL.md         |       |-- debug-drc/SKILL.md
|       |-- debug-lvs/SKILL.md         |       |-- debug-lvs/SKILL.md
|       |-- ... (8 skills total)       |       |-- ... (8 skills total)
|                                      |
|-- .context-teleport/  [GITIGNORED]   |-- .context-teleport/  [GITIGNORED]
|   (internal git repo)                |   (internal git repo)
|   |-- manifest.json                  |   |-- manifest.json
|   |-- knowledge/                     |   |-- knowledge/
|   |   |-- 12 entries (.md)           |   |   |-- 7 entries (.md)
|   |   +-- decisions/                 |   |   +-- decisions/
|   |       +-- 6 ADRs (.md)          |   |       +-- 5 ADRs (.md)
|   |-- skills/                        |   |-- skills/
|   |   +-- 8 skills (SKILL.md)       |   |   +-- 8 skills (SKILL.md)
|   +-- state/, history/, prefs/       |   +-- state/, history/, prefs/
|                                      |
+-- ihp-sg13g2/                        +-- LibreLane/
    ihp-sg13cmos5l/                        designs/ (9 designs)
    ...                                    CLAUDE.md (original, untouched)
```

**Key distinction**: `.claude/` is committed (visible to Claude Code). `.context-teleport/` is gitignored (invisible to the project repo, has its own internal git for sync).

---

## 2. Two-layer git architecture

```
                    PROJECT GIT (IHP-Open-PDK)
                    branch: feature/context-teleport
                    tracks: .gitignore, .claude/*, CLAUDE.md
                    ignores: .context-teleport/
                    |
                    |   .context-teleport/
                    |   |
                    |   |   INTERNAL GIT (context store)
                    |   |   tracks: knowledge/, decisions/, skills/, manifest.json
                    |   |   remote: ~/personal_exp/ctx-remotes/ihp-open-pdk.git
                    |   |
                    v   v

    Project repo                    Context store
    ============                    =============
    committed to project            committed to its OWN repo
    visible in PRs/branches         invisible to project
    .claude/mcp.json                knowledge/*.md
    .claude/skills/*/SKILL.md       knowledge/decisions/*.md
    CLAUDE.md (managed section)     skills/*/SKILL.md
                                    manifest.json

    WHY?
    - Project repo: what Claude Code reads directly
    - Context store: the portable database that syncs independently
    - export copies FROM store TO .claude/ and CLAUDE.md
    - import copies FROM CLAUDE.md TO store
```

---

## 3. Data flow: what happened step by step

```
    CLAUDE.md (668 lines)                   eda-skills-pack/
    SESSION_LOG.md (4 sessions)             8 x SKILL.md
            |                                      |
            v                                      v
    +------------------+                +-------------------+
    | import claude-code|                | skill add -f ...  |
    | (automatic)       |                | (x8, from files)  |
    +--------+---------+                +--------+----------+
             |                                   |
             v                                   v
    +--------------------------------------------------+
    |           .context-teleport/ (store)              |
    |                                                  |
    |   knowledge/                                     |
    |   |-- project-instructions.md  <-- from import   |
    |   |-- memory.md                <-- from import   |
    |   |-- slim-pdk-layer-reduction.md   \            |
    |   |-- slim-pdk-device-status.md      |           |
    |   |-- slim-pdk-tech-json-changes.md  | manual    |
    |   |-- drm-layout-rules-source...md   | entries   |
    |   |-- ihp-manufacturing-grid.md      | (via CLI) |
    |   |-- ihp-no-tapcells.md            /            |
    |   +-- decisions/                                 |
    |       |-- 0001-use-json-databases...md  \        |
    |       |-- 0002-comment-out-topmetal...md | from  |
    |       |-- 0003-symlink-unchanged...md    | stdin  |
    |       |-- 0004-include-cmos-resistors.md | heredoc|
    |       |-- 0005-guardring-not-standalone.md|       |
    |       +-- 0006-drm-pdfs-authoritative.md/        |
    |                                                  |
    |   skills/                                        |
    |   |-- debug-drc/SKILL.md                         |
    |   |-- debug-lvs/SKILL.md                         |
    |   |-- ... (8 total)                              |
    +--------------------------------------------------+
             |
             | export claude-code
             v
    +--------------------------------------------------+
    |   .claude/                  CLAUDE.md            |
    |   |-- mcp.json              |                    |
    |   +-- skills/               +-- <!-- ctx -->     |
    |       |-- debug-drc/            knowledge summary|
    |       |-- debug-lvs/            decision list    |
    |       |-- ... (8 dirs)          <!-- end ctx --> |
    +--------------------------------------------------+
             |
             | register claude-code --local
             v
    +--------------------------------------------------+
    |   .claude/mcp.json                               |
    |   {                                              |
    |     "mcpServers": {                              |
    |       "context-teleport": {                      |
    |         "command": "/.../context-teleport",      |
    |         "env": { "MCP_CALLER": "mcp:claude-code"}|
    |       }                                          |
    |     }                                            |
    |   }                                              |
    +--------------------------------------------------+
```

---

## 4. Sync architecture: how context travels

```
    Machine A (you)                          Machine B (team member)
    ==============                           ======================

    project/                                 project/
    |-- .context-teleport/                   |-- .context-teleport/
        |-- .git/                                |-- .git/
        |   remote: ctx-remotes/x.git            |   remote: ctx-remotes/x.git
        |                                        |
        +-- knowledge/, skills/, ...             +-- knowledge/, skills/, ...

             |                                        ^
             | git push                               | git pull
             v                                        |
        +----------------------------------------+
        |   ~/personal_exp/ctx-remotes/x.git     |
        |   (bare git repo -- the "hub")         |
        |                                        |
        |   Could also be:                       |
        |   - GitHub repo                        |
        |   - GitLab repo                        |
        |   - Any git remote                     |
        +----------------------------------------+


    WHAT SYNCS:                      WHAT DOESN'T SYNC:
    - knowledge/*.md                 - .claude/mcp.json (local registration)
    - knowledge/decisions/*.md       - .claude/skills/ (local export)
    - skills/*/SKILL.md              - CLAUDE.md managed section (local export)
    - manifest.json                  - project files
    - state/, history/, prefs/

    The store IS the sync unit.
    The .claude/ exports are local materializations of store content.
    Each machine runs `export claude-code` after pulling to refresh its local files.
```

---

## 5. How Claude Code sees it at runtime

```
    Claude Code session starts
    |
    |-- reads CLAUDE.md
    |   +-- sees managed section with knowledge summary + decision list
    |
    |-- reads .claude/mcp.json
    |   +-- starts context-teleport MCP server
    |       |
    |       +-- server discovers .context-teleport/ via find_project_root()
    |           |
    |           +-- 19 MCP tools available:
    |               context_read, context_write, context_search,
    |               context_add_skill, context_sync_pull, context_sync_push,
    |               context_record_decision, context_resolve_conflict, ...
    |
    |           +-- 10 MCP resources available:
    |               context://knowledge, context://decisions,
    |               context://skills, context://skills/{name}, ...
    |
    |           +-- 4 MCP prompts available:
    |               context_onboarding, context_summary,
    |               context_resolve_conflicts, context_skill_guide
    |
    |-- reads .claude/skills/*/SKILL.md
    |   +-- 8 EDA skills available as agent capabilities
    |
    v
    Agent has: static knowledge (CLAUDE.md) + live MCP tools + 8 domain skills
```

---

## 6. What got committed vs what's internal

```
    git status (project repo)
    =========================

    COMMITTED (in feature/context-teleport branch):
    M  .gitignore                          # added .context-teleport/ ignore
    A  .claude/mcp.json                    # MCP server registration
    A  .claude/skills/debug-drc/SKILL.md   # 8 skill files
    A  .claude/skills/debug-lvs/SKILL.md
    A  .claude/skills/...
    A  CLAUDE.md                           # with managed section appended

    NOT COMMITTED (gitignored):
       .context-teleport/                  # the actual context store
                                           # has its own git, its own remote
                                           # syncs independently of the project
```
