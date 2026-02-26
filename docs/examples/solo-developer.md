# Solo Developer

A complete walkthrough of one developer using Context Teleport across multiple sessions on a FastAPI project.

## Scenario

Jane is building a FastAPI application. She uses Claude Code as her primary agent tool and works from two machines (office desktop and home laptop). She wants her agent to remember architecture decisions, coding patterns, and project state across sessions and devices.

## Day 1: Project setup

### Initialize the project

```bash
cd ~/projects/taskflow-api
git init
context-teleport init --name taskflow-api --repo-url git@github.com:jane/taskflow-api.git
context-teleport register claude-code
```

### First agent session

Jane opens Claude Code. The agent sees the context store is empty and starts fresh.

```
Jane: "We're building a task management API with FastAPI.
       Architecture: hexagonal with ports and adapters.
       Database: PostgreSQL with SQLAlchemy async.
       Auth: JWT with refresh tokens."

Agent: [calls context_add_knowledge(key="architecture", content="...")]
       [calls context_add_knowledge(key="tech-stack", content="...")]
       [calls context_record_decision(title="Use hexagonal architecture", ...)]
       [calls context_record_decision(title="PostgreSQL over SQLite", ...)]
       [calls context_record_decision(title="JWT authentication", ...)]
       Saved architecture knowledge and 3 decisions.

Jane: "Push everything"

Agent: [calls context_sync_push(message="Initial project context")]
       Pushed to remote.
```

## Day 2: Adding patterns and skills

### Morning session

```
Jane: "I keep writing the same FastAPI dependency injection pattern.
       Can you save it as a skill?"

Agent: [calls context_add_skill(
           name="fastapi-dependency",
           description="Standard FastAPI dependency injection pattern",
           instructions="## Pattern\n\n```python\nfrom typing import Annotated..."
       )]
       Skill 'fastapi-dependency' saved.

Jane: "Also save our error handling pattern"

Agent: [calls context_add_skill(
           name="error-handling",
           description="Structured error responses with error codes",
           instructions="## Error Response Format\n\n..."
       )]
       Done. Two skills available now.
```

### Afternoon: working on features

```
Jane: "I'm implementing the user registration endpoint"

Agent: [calls context_update_state(current_task="Implement user registration endpoint")]
       [reads context://skills/fastapi-dependency for the DI pattern]
       [reads context://skills/error-handling for error format]

       Here's the implementation following our patterns...
```

### End of day

```
Jane: "Wrap up for today"

Agent: [calls context_append_session(
           agent="claude-code",
           summary="Implemented user registration with JWT auth. Added DI and error handling skills.",
           knowledge_added="",
           decisions_added=""
       )]
       [calls context_sync_push(message="Session: user registration endpoint")]
       Session logged and pushed.
```

## Day 3: Switching machines

Jane is working from home. She pulls the latest code and opens Claude Code.

### Auto-onboarding

The MCP server starts and generates dynamic instructions:

```
Context Teleport is active for project 'taskflow-api'.
Knowledge base (2 entries): architecture, tech-stack.
Architectural decisions: 3 recorded.
Agent skills (2 available): fastapi-dependency, error-handling.
Current task: Implement user registration endpoint
```

The agent immediately knows the project context without Jane explaining anything.

```
Jane: "I need to add email verification to the registration flow"

Agent: [reads context://knowledge/architecture for the hexagonal pattern]
       [reads context://skills/fastapi-dependency]
       I see from the project context that we're using hexagonal architecture
       with FastAPI. The current task was user registration. Let me add email
       verification following the established patterns...
```

## Week 2: Refining skills

After using the `error-handling` skill several times, Jane notices it's missing retry logic.

```
Jane: "The error handling skill is good but needs a retry section.
       Rate it a 3 -- works but incomplete."

Agent: [calls context_rate_skill(skill_name="error-handling", rating=3,
           comment="Missing retry/backoff patterns for external API calls")]
       Rated. I can propose an improvement if you'd like.

Jane: "Yes, add retry logic with exponential backoff"

Agent: [calls context_propose_skill_improvement(
           skill_name="error-handling",
           proposed_content="---\nname: error-handling\ndescription: ...\n---\n## Error Response Format\n...\n## Retry Logic\n...",
           rationale="Add retry/backoff patterns for external API calls"
       )]
       Proposal created with diff showing the added retry section.
```

Later, via CLI:

```bash
context-teleport skill proposals --status pending
# Shows the proposal with diff summary

context-teleport skill apply-proposal error-handling <proposal-id>
# Accepts and applies the improvement
```

## Month 2: Private notes

Jane keeps some notes that shouldn't be shared if she ever adds teammates:

```
Jane: "Save a private note about the production database credentials location"

Agent: [calls context_add_knowledge(
           key="prod-db-access",
           content="Production DB credentials are in 1Password vault 'TaskFlow Prod'...",
           scope="private"
       )]
       Saved as private (won't be synced or exported).
```

## Key takeaways

| Practice | Benefit |
|----------|---------|
| Knowledge entries for architecture | Agent remembers across sessions and machines |
| Decision records (ADR) | Future sessions understand *why* choices were made |
| Skills for repeated patterns | Consistent code patterns without re-explaining |
| Usage tracking + feedback | Skills improve over time based on actual use |
| Scoping (private) | Personal notes stay local |
| Session summaries | History provides context for returning to a project |
| Auto-push on shutdown | Changes are never lost, even without explicit push |
