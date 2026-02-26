"""Skill subcommands: list, get, add, rm, scope, stats, feedback, review, proposals, apply-proposal, propose-upstream."""

from __future__ import annotations

import sys
from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION, get_store
from ctx.core.frontmatter import build_frontmatter, parse_frontmatter
from ctx.core.scope import Scope
from ctx.utils.output import error, info, output, output_table, success

skill_app = typer.Typer(no_args_is_help=True)


def _parse_scope(value: str) -> Scope | None:
    if not value:
        return None
    try:
        return Scope(value.lower())
    except ValueError:
        return None


@skill_app.command("list")
def skill_list(
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Filter by scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List available skills."""
    store = get_store()
    scope_filter = _parse_scope(scope) if scope else None
    entries = store.list_skills(scope=scope_filter)
    if fmt == "json":
        items = []
        for e in entries:
            items.append({
                "name": e.name,
                "description": e.description,
                "scope": store.get_skill_scope(e.name).value,
            })
        output(items, fmt="json")
    else:
        if not entries:
            info("No skills yet. Use `context-teleport skill add <name>` to add one.")
            return
        rows = []
        for e in entries:
            rows.append({
                "name": e.name,
                "description": e.description[:60],
                "scope": store.get_skill_scope(e.name).value,
            })
        output_table(rows, columns=["name", "description", "scope"])


@skill_app.command("get")
def skill_get(
    name: str = typer.Argument(..., help="Skill name"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Print full SKILL.md content."""
    store = get_store()
    entry = store.get_skill(name)
    if entry is None:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)
    if fmt == "json":
        output({"name": entry.name, "description": entry.description, "content": entry.content}, fmt="json")
    else:
        output(entry.content, title=entry.name)


@skill_app.command("add")
def skill_add(
    name: str = typer.Argument(..., help="Skill name (used as directory name)"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read SKILL.md content from file"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Skill description (for auto-generated frontmatter)"),
    scope: Optional[str] = typer.Option(None, "--scope", "-s", help="Scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Create or update a skill from file, stdin, or editor template."""
    store = get_store()

    if file:
        from pathlib import Path

        text = Path(file).read_text()
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        # Generate a template if no input provided
        desc = description or f"Description for {name}"
        text = build_frontmatter(
            {"name": name, "description": desc},
            f"# {name}\n\nInstructions for this skill go here.\n",
        )

    # Ensure frontmatter has name field
    meta, body = parse_frontmatter(text)
    if "name" not in meta:
        meta["name"] = name
        if description and "description" not in meta:
            meta["description"] = description or ""
        text = build_frontmatter(meta, body)

    scope_val = _parse_scope(scope) if scope else None
    entry = store.set_skill(name, text, scope=scope_val)
    if fmt == "json":
        output({"name": entry.name, "status": "written"}, fmt="json")
    else:
        success(f"Skill '{entry.name}' written")


@skill_app.command("rm")
def skill_rm(
    name: str = typer.Argument(..., help="Skill name"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Remove a skill."""
    store = get_store()
    if store.rm_skill(name):
        if fmt == "json":
            output({"name": name, "status": "removed"}, fmt="json")
        else:
            success(f"Skill '{name}' removed")
    else:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)


@skill_app.command("scope")
def skill_scope(
    name: str = typer.Argument(..., help="Skill name"),
    scope: str = typer.Argument(..., help="New scope (public/private/ephemeral)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Change the scope of an existing skill."""
    store = get_store()
    scope_val = _parse_scope(scope)
    if scope_val is None:
        error(f"Invalid scope '{scope}'. Use public, private, or ephemeral.")
        raise typer.Exit(1)

    if store.set_skill_scope(name, scope_val):
        if fmt == "json":
            output({"name": name, "scope": scope_val.value, "status": "updated"}, fmt="json")
        else:
            success(f"Skill '{name}' scope set to {scope_val.value}")
    else:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)


# -- Phase 7a: stats, feedback, review --


@skill_app.command("stats")
def skill_stats(
    sort: Optional[str] = typer.Option("name", "--sort", help="Sort by: usage, rating, name"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Show usage and feedback stats for all skills."""
    store = get_store()
    stats = store.list_skill_stats()
    if not stats:
        info("No skills yet.")
        return

    if sort == "usage":
        stats.sort(key=lambda s: s.usage_count, reverse=True)
    elif sort == "rating":
        stats.sort(key=lambda s: s.avg_rating, reverse=True)
    else:
        stats.sort(key=lambda s: s.skill_name)

    if fmt == "json":
        output([s.model_dump() for s in stats], fmt="json")
    else:
        rows = []
        for s in stats:
            rows.append({
                "name": s.skill_name,
                "usage": str(s.usage_count),
                "avg_rating": f"{s.avg_rating:.1f}" if s.rating_count else "-",
                "ratings": str(s.rating_count),
                "last_used": s.last_used.strftime("%Y-%m-%d") if s.last_used else "-",
                "attention": "!" if s.needs_attention else "",
            })
        output_table(rows, columns=["name", "usage", "avg_rating", "ratings", "last_used", "attention"])


@skill_app.command("feedback")
def skill_feedback(
    name: str = typer.Argument(..., help="Skill name"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List feedback entries for a skill."""
    store = get_store()
    entry = store.get_skill(name)
    if entry is None:
        error(f"Skill '{name}' not found")
        raise typer.Exit(1)

    feedback = store.list_skill_feedback(name)
    if not feedback:
        info(f"No feedback for '{name}' yet.")
        return

    if fmt == "json":
        output([f.model_dump() for f in feedback], fmt="json")
    else:
        rows = []
        for f in feedback:
            rows.append({
                "agent": f.agent,
                "rating": str(f.rating),
                "comment": f.comment[:60],
                "timestamp": f.timestamp.strftime("%Y-%m-%d %H:%M"),
            })
        output_table(rows, columns=["agent", "rating", "comment", "timestamp"])


@skill_app.command("review")
def skill_review(
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Show skills needing attention (avg rating < 3.0 with 2+ ratings)."""
    store = get_store()
    stats = store.list_skill_stats()
    attention = [s for s in stats if s.needs_attention]

    if not attention:
        info("No skills need attention.")
        return

    if fmt == "json":
        items = []
        for s in attention:
            recent_fb = store.list_skill_feedback(s.skill_name)[-3:]
            items.append({
                "skill": s.model_dump(),
                "recent_feedback": [f.model_dump() for f in recent_fb],
            })
        output(items, fmt="json")
    else:
        for s in attention:
            info(f"\n{s.skill_name} - avg: {s.avg_rating:.1f}, ratings: {s.rating_count}, uses: {s.usage_count}")
            recent_fb = store.list_skill_feedback(s.skill_name)[-3:]
            for f in recent_fb:
                info(f"  [{f.rating}/5] {f.agent}: {f.comment[:80]}")


# -- Phase 7b: proposals, apply-proposal, propose-upstream --


@skill_app.command("proposals")
def skill_proposals(
    skill: Optional[str] = typer.Option(None, "--skill", help="Filter by skill name"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status (pending/accepted/rejected/upstream)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List skill improvement proposals."""
    from ctx.core.schema import ProposalStatus

    store = get_store()
    status_filter = None
    if status:
        try:
            status_filter = ProposalStatus(status.lower())
        except ValueError:
            error(f"Invalid status '{status}'. Use pending, accepted, rejected, or upstream.")
            raise typer.Exit(1)

    proposals = store.list_skill_proposals(skill_name=skill, status=status_filter)
    if not proposals:
        if fmt == "json":
            output([], fmt="json")
        else:
            info("No proposals found.")
        return

    if fmt == "json":
        output([p.model_dump() for p in proposals], fmt="json")
    else:
        rows = []
        for p in proposals:
            rows.append({
                "id": p.id[:8],
                "skill": p.skill_name,
                "status": p.status.value,
                "diff": p.diff_summary,
                "agent": p.agent,
                "created": p.created_at.strftime("%Y-%m-%d"),
            })
        output_table(rows, columns=["id", "skill", "status", "diff", "agent", "created"])


@skill_app.command("apply-proposal")
def skill_apply_proposal(
    skill_name: str = typer.Argument(..., help="Skill name"),
    proposal_id: str = typer.Argument(..., help="Proposal ID (or prefix)"),
    reject: bool = typer.Option(False, "--reject", help="Reject instead of accept"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Accept or reject a skill improvement proposal."""
    store = get_store()

    # Support prefix matching for proposal IDs
    proposals = store.list_skill_proposals(skill_name=skill_name)
    matched = [p for p in proposals if p.id.startswith(proposal_id)]
    if not matched:
        error(f"Proposal '{proposal_id}' not found for skill '{skill_name}'")
        raise typer.Exit(1)
    if len(matched) > 1:
        error(f"Ambiguous prefix '{proposal_id}', matches {len(matched)} proposals")
        raise typer.Exit(1)

    full_id = matched[0].id
    result = store.resolve_skill_proposal(
        skill_name, full_id, accept=not reject, resolved_by="cli"
    )
    if result is None:
        error(f"Proposal '{proposal_id}' not found")
        raise typer.Exit(1)

    action = "rejected" if reject else "accepted"
    if fmt == "json":
        output({"proposal_id": result.id, "status": result.status.value, "action": action}, fmt="json")
    else:
        success(f"Proposal {result.id[:8]} {action} for skill '{skill_name}'")


@skill_app.command("propose-upstream")
def skill_propose_upstream(
    skill_name: str = typer.Argument(..., help="Skill name"),
    proposal_id: str = typer.Argument(..., help="Proposal ID (or prefix)"),
    repo: str = typer.Option(..., "--repo", help="Target repo (OWNER/REPO)"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Push an accepted proposal as a PR to an upstream skills pack repo."""
    import subprocess
    import tempfile
    from pathlib import Path

    from ctx.core.schema import ProposalStatus

    store = get_store()

    # Resolve prefix
    proposals = store.list_skill_proposals(skill_name=skill_name)
    matched = [p for p in proposals if p.id.startswith(proposal_id)]
    if not matched:
        error(f"Proposal '{proposal_id}' not found for skill '{skill_name}'")
        raise typer.Exit(1)
    if len(matched) > 1:
        error(f"Ambiguous prefix '{proposal_id}', matches {len(matched)} proposals")
        raise typer.Exit(1)

    proposal = matched[0]
    if proposal.status not in (ProposalStatus.accepted, ProposalStatus.pending):
        error(f"Proposal status is '{proposal.status.value}', expected pending or accepted")
        raise typer.Exit(1)

    short_id = proposal.id[:8]
    branch_name = f"skill-improve/{skill_name}-{short_id}"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Clone the repo
        try:
            subprocess.run(
                ["gh", "repo", "clone", repo, str(tmpdir_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            error(f"Failed to clone {repo}: {e.stderr.strip()}")
            raise typer.Exit(1)

        # Create branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=tmpdir_path,
            check=True,
            capture_output=True,
        )

        # Write SKILL.md
        skill_dir = tmpdir_path / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(proposal.proposed_content)

        # Commit
        subprocess.run(["git", "add", "."], cwd=tmpdir_path, check=True, capture_output=True)
        commit_msg = f"Improve skill '{skill_name}'\n\n{proposal.rationale}"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=tmpdir_path,
            check=True,
            capture_output=True,
        )

        # Push
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=tmpdir_path,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            error(f"Failed to push: {e.stderr.strip()}")
            raise typer.Exit(1)

        # Create PR
        try:
            pr_result = subprocess.run(
                [
                    "gh", "pr", "create",
                    "--title", f"Improve skill: {skill_name}",
                    "--body", f"## Rationale\n\n{proposal.rationale}\n\n## Diff\n\n{proposal.diff_summary}\n\nProposal ID: `{proposal.id}`",
                ],
                cwd=tmpdir_path,
                check=True,
                capture_output=True,
                text=True,
            )
            pr_url = pr_result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error(f"Failed to create PR: {e.stderr.strip()}")
            raise typer.Exit(1)

    # Update proposal status
    import json

    proposal.status = ProposalStatus.upstream
    proposal_path = store._skill_proposals_dir(skill_name) / f"{proposal.id}.json"
    proposal_path.write_text(
        json.dumps(proposal.model_dump(), indent=2, default=str) + "\n"
    )

    if fmt == "json":
        output({"proposal_id": proposal.id, "status": "upstream", "pr_url": pr_url}, fmt="json")
    else:
        success(f"PR created: {pr_url}")
