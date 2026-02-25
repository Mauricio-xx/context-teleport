"""Tests for the shared frontmatter parser/builder."""

from ctx.core.frontmatter import build_frontmatter, parse_frontmatter


class TestParseFrontmatter:
    def test_basic(self):
        text = "---\nname: deploy\ndescription: Deploy to staging\n---\n\nRun the deploy script.\n"
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "deploy"
        assert meta["description"] == "Deploy to staging"
        assert body == "Run the deploy script."

    def test_no_frontmatter(self):
        text = "Just plain markdown content."
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_empty_body(self):
        text = "---\nname: empty\n---\n\n"
        meta, body = parse_frontmatter(text)
        assert meta["name"] == "empty"
        assert body == ""

    def test_boolean_values(self):
        text = "---\nalwaysApply: true\ndisabled: false\n---\n\nBody.\n"
        meta, body = parse_frontmatter(text)
        assert meta["alwaysApply"] is True
        assert meta["disabled"] is False

    def test_array_values(self):
        text = '---\nglobs: ["**/*.py", "src/*.ts"]\n---\n\nBody.\n'
        meta, body = parse_frontmatter(text)
        assert meta["globs"] == ["**/*.py", "src/*.ts"]

    def test_incomplete_frontmatter(self):
        text = "---\nname: broken\nno closing delimiter"
        meta, body = parse_frontmatter(text)
        assert meta == {}
        assert body == text

    def test_empty_string(self):
        meta, body = parse_frontmatter("")
        assert meta == {}
        assert body == ""


class TestBuildFrontmatter:
    def test_basic(self):
        result = build_frontmatter(
            {"name": "deploy", "description": "Deploy to staging"},
            "Run the deploy script.",
        )
        assert result.startswith("---\n")
        assert "name: deploy" in result
        assert "description: Deploy to staging" in result
        assert result.endswith("Run the deploy script.\n")

    def test_boolean_values(self):
        result = build_frontmatter({"enabled": True, "hidden": False}, "Body.")
        assert "enabled: true" in result
        assert "hidden: false" in result

    def test_array_values(self):
        result = build_frontmatter({"globs": ["*.py", "*.ts"]}, "Body.")
        assert '["*.py", "*.ts"]' in result

    def test_empty_body(self):
        result = build_frontmatter({"name": "test"}, "")
        meta, body = parse_frontmatter(result)
        assert meta["name"] == "test"
        assert body == ""


class TestRoundTrip:
    def test_parse_then_build(self):
        original = "---\nname: my-skill\ndescription: Does stuff\n---\n\n# Instructions\n\nDo the thing.\n"
        meta, body = parse_frontmatter(original)
        rebuilt = build_frontmatter(meta, body)
        meta2, body2 = parse_frontmatter(rebuilt)
        assert meta == meta2
        assert body == body2

    def test_build_then_parse(self):
        meta = {"name": "test-skill", "description": "A test"}
        body = "Step 1: Do X\nStep 2: Do Y"
        built = build_frontmatter(meta, body)
        parsed_meta, parsed_body = parse_frontmatter(built)
        assert parsed_meta == meta
        assert parsed_body == body
