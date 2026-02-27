"""Dotpath resolution for context store values (e.g. 'knowledge.architecture')."""

from __future__ import annotations

from ctx.core.store import ContextStore


def resolve_dotpath(store: ContextStore, dotpath: str):
    """Resolve a dotpath like 'knowledge.architecture' into a value."""
    parts = dotpath.split(".")

    if not parts:
        return None

    section = parts[0]
    rest = parts[1:]

    if section == "knowledge":
        if not rest:
            entries = store.list_knowledge()
            return {e.key: e.content for e in entries}
        key = rest[0]
        entry = store.get_knowledge(key)
        if entry is None:
            return None
        return entry.content

    elif section == "conventions":
        if not rest:
            entries = store.list_conventions()
            return {e.key: e.content for e in entries}
        key = rest[0]
        entry = store.get_convention(key)
        if entry is None:
            return None
        return entry.content

    elif section == "decisions":
        if not rest:
            decisions = store.list_decisions()
            return [
                {"id": d.id, "title": d.title, "status": d.status.value}
                for d in decisions
            ]
        dec = store.get_decision(rest[0])
        if dec is None:
            return None
        if len(rest) > 1:
            return getattr(dec, rest[1], None)
        return {
            "id": dec.id,
            "title": dec.title,
            "status": dec.status.value,
            "context": dec.context,
            "decision": dec.decision,
            "consequences": dec.consequences,
        }

    elif section == "state":
        state = store.read_active_state()
        if not rest:
            return state.model_dump()
        return getattr(state, rest[0], state.progress.get(rest[0]))

    elif section == "preferences":
        if rest and rest[0] == "team":
            prefs = store.read_team_preferences()
            if len(rest) > 1:
                return prefs.values.get(rest[1])
            return prefs.values
        elif rest and rest[0] == "user":
            prefs = store.read_user_preferences()
            if len(rest) > 1:
                return prefs.values.get(rest[1])
            return prefs.values
        return {
            "team": store.read_team_preferences().values,
            "user": store.read_user_preferences().values,
        }

    elif section == "manifest":
        manifest = store.read_manifest()
        data = manifest.model_dump()
        obj = data
        for p in rest:
            if isinstance(obj, dict):
                obj = obj.get(p)
            else:
                return None
        return obj

    elif section == "activity":
        activity = store.list_activity()
        if not rest:
            return [a.model_dump() for a in activity]
        member = rest[0]
        entry = store.get_activity(member)
        if entry is None:
            return None
        return entry.model_dump()

    elif section == "history":
        sessions = store.list_sessions()
        return [s.model_dump() for s in sessions]

    return None


def set_dotpath(store: ContextStore, dotpath: str, value: str):
    """Set a value at a dotpath."""
    parts = dotpath.split(".")

    if not parts:
        raise ValueError("Empty dotpath")

    section = parts[0]
    rest = parts[1:]

    if section == "knowledge":
        if not rest:
            raise ValueError("Specify a knowledge key: knowledge.<key>")
        store.set_knowledge(rest[0], value)
        return

    if section == "conventions":
        if not rest:
            raise ValueError("Specify a convention key: conventions.<key>")
        store.set_convention(rest[0], value)
        return

    if section == "state":
        state = store.read_active_state()
        if not rest:
            raise ValueError("Specify a state field: state.<field>")
        field = rest[0]
        if field == "current_task":
            state.current_task = value
        elif field == "blockers":
            state.blockers = [b.strip() for b in value.split(",") if b.strip()]
        elif field == "last_agent":
            state.last_agent = value
        elif field == "last_machine":
            state.last_machine = value
        else:
            state.progress[field] = value
        store.write_active_state(state)
        return

    if section == "preferences":
        if not rest:
            raise ValueError("Specify preferences.team.<key> or preferences.user.<key>")
        if rest[0] == "team":
            prefs = store.read_team_preferences()
            if len(rest) > 1:
                prefs.values[rest[1]] = value
            store.write_team_preferences(prefs)
        elif rest[0] == "user":
            prefs = store.read_user_preferences()
            if len(rest) > 1:
                prefs.values[rest[1]] = value
            store.write_user_preferences(prefs)
        return

    raise ValueError(f"Cannot set values in section '{section}'")
