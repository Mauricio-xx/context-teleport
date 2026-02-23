"""E2E tests: spawn ctx-mcp subprocess and talk to it via MCP protocol."""

from __future__ import annotations

import json

import pytest

from tests.mcp.conftest import spawn_mcp_session

pytestmark = pytest.mark.anyio


class TestInitialization:
    """MCP handshake and capability negotiation."""

    async def test_handshake_completes(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            caps = session.get_server_capabilities()
            assert caps is not None

    async def test_capabilities_include_tools(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            caps = session.get_server_capabilities()
            assert caps.tools is not None

    async def test_capabilities_include_resources(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            caps = session.get_server_capabilities()
            assert caps.resources is not None


class TestToolDiscovery:
    """Verify tool listing via the protocol."""

    async def test_list_tools_returns_tools(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.list_tools()
            assert len(result.tools) >= 10

    async def test_expected_tool_names_present(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.list_tools()
            names = {t.name for t in result.tools}
            expected = {
                "context_search",
                "context_add_knowledge",
                "context_remove_knowledge",
                "context_record_decision",
                "context_update_state",
                "context_append_session",
                "context_sync_push",
                "context_sync_pull",
                "context_get",
                "context_set",
                "context_merge_status",
                "context_resolve_conflict",
            }
            assert expected.issubset(names), f"Missing tools: {expected - names}"

    async def test_tools_have_input_schemas(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.list_tools()
            for tool in result.tools:
                assert tool.inputSchema is not None


class TestResourceDiscovery:
    """Verify resource listing via the protocol."""

    async def test_list_resources_returns_static(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.list_resources()
            uris = {str(r.uri) for r in result.resources}
            expected_static = {
                "context://manifest",
                "context://knowledge",
                "context://decisions",
                "context://state",
                "context://history",
                "context://summary",
            }
            assert expected_static.issubset(uris), f"Missing resources: {expected_static - uris}"

    async def test_list_resource_templates(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.list_resource_templates()
            template_uris = {str(t.uriTemplate) for t in result.resourceTemplates}
            assert len(template_uris) >= 2


class TestPromptDiscovery:
    """Verify prompt listing via the protocol."""

    async def test_list_prompts(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.list_prompts()
            names = {p.name for p in result.prompts}
            expected = {"context_onboarding", "context_handoff", "context_review_decisions"}
            assert expected.issubset(names), f"Missing prompts: {expected - names}"


class TestResourceReads:
    """Read resources via MCP protocol and verify content."""

    async def test_read_manifest(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.read_resource("context://manifest")
            content = _extract_text(result)
            data = json.loads(content)
            assert data["project"]["name"] == "e2e-test-project"
            assert data["schema_version"] == "0.2.0"

    async def test_read_knowledge_empty(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.read_resource("context://knowledge")
            content = _extract_text(result)
            data = json.loads(content)
            assert data == []

    async def test_read_knowledge_populated(self, populated_e2e_store):
        async with spawn_mcp_session(populated_e2e_store) as session:
            result = await session.read_resource("context://knowledge")
            content = _extract_text(result)
            data = json.loads(content)
            keys = {e["key"] for e in data}
            assert "architecture" in keys
            assert "conventions" in keys

    async def test_read_decisions_populated(self, populated_e2e_store):
        async with spawn_mcp_session(populated_e2e_store) as session:
            result = await session.read_resource("context://decisions")
            content = _extract_text(result)
            data = json.loads(content)
            assert len(data) == 1
            assert data[0]["title"] == "Use PostgreSQL"

    async def test_read_state(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.read_resource("context://state")
            content = _extract_text(result)
            data = json.loads(content)
            assert "current_task" in data

    async def test_read_summary(self, populated_e2e_store):
        async with spawn_mcp_session(populated_e2e_store) as session:
            result = await session.read_resource("context://summary")
            content = _extract_text(result)
            data = json.loads(content)
            assert data["project"] == "e2e-test-project"
            assert data["knowledge_count"] == 2


class TestToolInvocation:
    """Call tools via MCP protocol and verify results."""

    async def test_add_knowledge(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.call_tool(
                "context_add_knowledge",
                {"key": "tech-stack", "content": "Python 3.12 with FastMCP"},
            )
            data = json.loads(result.content[0].text)
            assert data["status"] == "ok"
            assert data["key"] == "tech-stack"

    async def test_remove_knowledge(self, populated_e2e_store):
        async with spawn_mcp_session(populated_e2e_store) as session:
            result = await session.call_tool(
                "context_remove_knowledge", {"key": "conventions"}
            )
            data = json.loads(result.content[0].text)
            assert data["status"] == "removed"

    async def test_remove_knowledge_not_found(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.call_tool(
                "context_remove_knowledge", {"key": "nonexistent"}
            )
            data = json.loads(result.content[0].text)
            assert data["status"] == "not_found"

    async def test_record_decision(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.call_tool(
                "context_record_decision",
                {
                    "title": "Use Redis",
                    "context": "Need caching layer",
                    "decision": "Redis for session cache",
                    "consequences": "Additional infrastructure",
                },
            )
            data = json.loads(result.content[0].text)
            assert data["status"] == "ok"
            assert data["id"] == 1

    async def test_update_state(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.call_tool(
                "context_update_state",
                {"current_task": "Running E2E tests"},
            )
            data = json.loads(result.content[0].text)
            assert data["status"] == "ok"
            assert data["current_task"] == "Running E2E tests"

    async def test_search_empty(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            result = await session.call_tool("context_search", {"query": "nonexistent"})
            data = json.loads(result.content[0].text)
            assert data == []

    async def test_context_get(self, populated_e2e_store):
        async with spawn_mcp_session(populated_e2e_store) as session:
            result = await session.call_tool(
                "context_get", {"dotpath": "knowledge.architecture"}
            )
            data = json.loads(result.content[0].text)
            assert "Hexagonal" in str(data)

    async def test_sync_push_no_remote(self, e2e_store):
        """Sync push commits locally when no remote is configured."""
        async with spawn_mcp_session(e2e_store) as session:
            # Add something so there are changes to push
            await session.call_tool(
                "context_add_knowledge", {"key": "sync-test", "content": "testing sync"}
            )
            result = await session.call_tool("context_sync_push", {})
            data = json.loads(result.content[0].text)
            assert data["status"] == "committed"


class TestRoundTrip:
    """Write via tool, then read back via resource in the same session."""

    async def test_add_knowledge_then_read(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            await session.call_tool(
                "context_add_knowledge",
                {"key": "api-design", "content": "REST with OpenAPI 3.1"},
            )
            result = await session.read_resource("context://knowledge")
            content = _extract_text(result)
            data = json.loads(content)
            keys = {e["key"] for e in data}
            assert "api-design" in keys

    async def test_record_decision_then_read(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            await session.call_tool(
                "context_record_decision",
                {"title": "Use GraphQL", "context": "API flexibility"},
            )
            result = await session.read_resource("context://decisions")
            content = _extract_text(result)
            data = json.loads(content)
            assert len(data) == 1
            assert data[0]["title"] == "Use GraphQL"

    async def test_update_state_then_read(self, e2e_store):
        async with spawn_mcp_session(e2e_store) as session:
            await session.call_tool(
                "context_update_state",
                {"current_task": "Integration testing"},
            )
            result = await session.read_resource("context://state")
            content = _extract_text(result)
            data = json.loads(content)
            assert data["current_task"] == "Integration testing"


def _extract_text(result) -> str:
    """Extract text content from a ReadResourceResult."""
    return result.contents[0].text
