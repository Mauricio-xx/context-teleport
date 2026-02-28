"""Tests for project auto-detection in ContextStore.init()."""

import json
from pathlib import Path

import git

from ctx.core.store import ContextStore, _detect_project


class TestDetectProject:
    def test_empty_directory(self, tmp_path):
        languages, build_systems = _detect_project(tmp_path)
        assert languages == []
        assert build_systems == []

    def test_python_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        languages, build_systems = _detect_project(tmp_path)
        assert "Python" in languages
        assert "pyproject.toml" in build_systems

    def test_rust_cargo(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
        languages, build_systems = _detect_project(tmp_path)
        assert "Rust" in languages
        assert "Cargo" in build_systems

    def test_javascript_npm(self, tmp_path):
        (tmp_path / "package.json").write_text('{"name": "test"}')
        languages, build_systems = _detect_project(tmp_path)
        assert "JavaScript" in languages
        assert "npm" in build_systems

    def test_cpp_cmake(self, tmp_path):
        (tmp_path / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.0)")
        languages, build_systems = _detect_project(tmp_path)
        assert "C/C++" in languages
        assert "CMake" in build_systems

    def test_go_mod(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/test\n\ngo 1.21\n")
        languages, build_systems = _detect_project(tmp_path)
        assert "Go" in languages
        assert "Go modules" in build_systems

    def test_multiple_languages(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "Makefile").write_text("all:\n\techo ok\n")
        languages, build_systems = _detect_project(tmp_path)
        assert "Python" in languages
        assert "JavaScript" in languages
        assert "Make" in build_systems

    def test_typescript_detected(self, tmp_path):
        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "package.json").write_text("{}")
        languages, build_systems = _detect_project(tmp_path)
        assert "TypeScript" in languages
        assert "JavaScript" in languages

    def test_makefile_only_build(self, tmp_path):
        (tmp_path / "Makefile").write_text("all:")
        languages, build_systems = _detect_project(tmp_path)
        # Makefile alone doesn't imply a language
        assert languages == []
        assert "Make" in build_systems

    def test_docker_detected(self, tmp_path):
        (tmp_path / "Dockerfile").write_text("FROM python:3.12\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")
        languages, build_systems = _detect_project(tmp_path)
        assert "Docker" in build_systems
        assert "Docker Compose" in build_systems

    def test_results_sorted(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("")
        (tmp_path / "pyproject.toml").write_text("")
        (tmp_path / "package.json").write_text("")
        languages, build_systems = _detect_project(tmp_path)
        assert languages == sorted(languages)
        assert build_systems == sorted(build_systems)

    def test_java_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text("")
        languages, build_systems = _detect_project(tmp_path)
        assert "Java" in languages
        assert "Gradle" in build_systems

    def test_ruby_bundler(self, tmp_path):
        (tmp_path / "Gemfile").write_text('source "https://rubygems.org"')
        languages, build_systems = _detect_project(tmp_path)
        assert "Ruby" in languages
        assert "Bundler" in build_systems


class TestInitAutoDetection:
    def test_init_detects_python(self, tmp_path):
        repo = git.Repo.init(tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n")
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        store = ContextStore(tmp_path)
        manifest = store.init(project_name="test")
        assert "Python" in manifest.languages
        assert "pyproject.toml" in manifest.build_systems

    def test_init_empty_project(self, tmp_path):
        repo = git.Repo.init(tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        store = ContextStore(tmp_path)
        manifest = store.init(project_name="test")
        assert manifest.languages == []
        assert manifest.build_systems == []

    def test_init_persists_detection(self, tmp_path):
        repo = git.Repo.init(tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n")
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        store = ContextStore(tmp_path)
        store.init(project_name="test")

        # Read back from disk
        manifest = store.read_manifest()
        assert "Rust" in manifest.languages
        assert "Cargo" in manifest.build_systems

    def test_manifest_backward_compatible(self, tmp_path):
        """Old manifests without languages/build_systems should still parse."""
        repo = git.Repo.init(tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        store = ContextStore(tmp_path)
        store.init(project_name="test")

        # Simulate old manifest by removing the new fields
        manifest_path = tmp_path / ".context-teleport" / "manifest.json"
        data = json.loads(manifest_path.read_text())
        del data["languages"]
        del data["build_systems"]
        manifest_path.write_text(json.dumps(data))

        # Should still read without error (fields default to [])
        manifest = store.read_manifest()
        assert manifest.languages == []
        assert manifest.build_systems == []
