"""Tests for merge logic."""

from ctx.core.merge import merge_json, merge_ndjson


class TestJsonMerge:
    def test_no_conflict(self):
        base = {"a": 1, "b": 2}
        ours = {"a": 1, "b": 3}  # changed b
        theirs = {"a": 2, "b": 2}  # changed a
        result = merge_json(base, ours, theirs)
        assert not result.has_conflicts
        assert result.content == {"a": 2, "b": 3}

    def test_both_agree(self):
        base = {"a": 1}
        ours = {"a": 2}
        theirs = {"a": 2}
        result = merge_json(base, ours, theirs)
        assert not result.has_conflicts
        assert result.content == {"a": 2}

    def test_conflict(self):
        base = {"a": 1}
        ours = {"a": 2}
        theirs = {"a": 3}
        result = merge_json(base, ours, theirs)
        assert result.has_conflicts
        assert len(result.conflict_details) == 1
        # Defaults to ours
        assert result.content["a"] == 2

    def test_new_keys(self):
        base = {}
        ours = {"a": 1}
        theirs = {"b": 2}
        result = merge_json(base, ours, theirs)
        assert not result.has_conflicts
        assert result.content == {"a": 1, "b": 2}

    def test_deleted_key(self):
        base = {"a": 1, "b": 2}
        ours = {"a": 1}  # deleted b
        theirs = {"a": 1, "b": 2}  # no change
        result = merge_json(base, ours, theirs)
        assert not result.has_conflicts
        assert "b" not in result.content


class TestNdjsonMerge:
    def test_union_merge(self):
        ours = '{"id":"1","text":"a"}\n{"id":"2","text":"b"}\n'
        theirs = '{"id":"2","text":"b"}\n{"id":"3","text":"c"}\n'
        result = merge_ndjson(ours, theirs)
        assert not result.has_conflicts
        lines = [l for l in result.content.strip().split("\n") if l]
        assert len(lines) == 3  # union of ids 1, 2, 3

    def test_empty_inputs(self):
        result = merge_ndjson("", "")
        assert not result.has_conflicts
        assert result.content == ""
