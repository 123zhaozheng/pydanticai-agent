"""Tests for the agent factory."""

import pytest
from pydantic_ai.models.test import TestModel

from pydantic_deep import (
    DeepAgentDeps,
    StateBackend,
    create_deep_agent,
    create_default_deps,
    run_with_files,
)
from pydantic_deep.types import SubAgentConfig, Todo

# Use TestModel to avoid requiring API keys
TEST_MODEL = TestModel()


class TestCreateDeepAgent:
    """Tests for create_deep_agent factory."""

    def test_create_default_agent(self):
        """Test creating an agent with default settings."""
        agent = create_deep_agent(model=TEST_MODEL)

        assert agent is not None

    def test_create_with_custom_model(self):
        """Test creating an agent with a custom model."""
        agent = create_deep_agent(model=TEST_MODEL)
        assert agent is not None

    def test_create_with_instructions(self):
        """Test creating an agent with custom instructions."""
        agent = create_deep_agent(model=TEST_MODEL, instructions="You are a test agent")
        assert agent is not None

    def test_create_without_todo(self):
        """Test creating an agent without todo toolset."""
        agent = create_deep_agent(model=TEST_MODEL, include_todo=False)
        assert agent is not None

    def test_create_without_filesystem(self):
        """Test creating an agent without filesystem toolset."""
        agent = create_deep_agent(model=TEST_MODEL, include_filesystem=False)
        assert agent is not None

    def test_create_without_subagents(self):
        """Test creating an agent without subagent toolset."""
        agent = create_deep_agent(model=TEST_MODEL, include_subagents=False)
        assert agent is not None

    def test_create_with_subagent_configs(self):
        """Test creating an agent with custom subagent configs."""
        subagents = [
            SubAgentConfig(
                name="researcher",
                description="A research agent",
                instructions="You research topics",
            ),
        ]
        agent = create_deep_agent(model=TEST_MODEL, subagents=subagents)
        assert agent is not None


class TestCreateDefaultDeps:
    """Tests for create_default_deps."""

    def test_create_with_defaults(self):
        """Test creating deps with default settings."""
        deps = create_default_deps()

        assert deps is not None
        assert isinstance(deps.backend, StateBackend)
        assert deps.todos == []
        assert deps.subagents == {}

    def test_create_with_custom_backend(self):
        """Test creating deps with a custom backend."""
        backend = StateBackend()
        deps = create_default_deps(backend=backend)

        assert deps.backend is backend


class TestDeepAgentDeps:
    """Tests for DeepAgentDeps."""

    def test_get_todo_prompt_empty(self):
        """Test todo prompt with no todos."""
        deps = DeepAgentDeps(backend=StateBackend())
        prompt = deps.get_todo_prompt()

        assert prompt == ""

    def test_get_todo_prompt_with_todos(self):
        """Test todo prompt with todos."""
        from pydantic_deep.types import Todo

        deps = DeepAgentDeps(
            backend=StateBackend(),
            todos=[
                Todo(content="Test task", status="pending", active_form="Testing"),
            ],
        )
        prompt = deps.get_todo_prompt()

        assert "Test task" in prompt
        assert "[ ]" in prompt

    def test_clone_for_subagent(self):
        """Test cloning deps for a subagent."""
        original = DeepAgentDeps(
            backend=StateBackend(),
            todos=[Todo(content="Task", status="pending", active_form="Working")],
            file_paths=["/test.txt"]
        )

        cloned = original.clone_for_subagent()

        # Should share backend and file_paths
        assert cloned.backend is original.backend
        assert cloned.file_paths is original.file_paths
        assert "/test.txt" in cloned.file_paths

        # Should have empty todos and subagents
        assert cloned.todos == []
        assert cloned.subagents == {}


class TestRunWithFiles:
    """Tests for run_with_files helper."""

    @pytest.mark.anyio
    async def test_run_with_files_uploads_files(self):
        """Test that run_with_files uploads files before running agent."""
        agent = create_deep_agent(model=TEST_MODEL)
        deps = DeepAgentDeps(backend=StateBackend())

        files = [
            ("data.csv", b"a,b\n1,2\n"),
            ("config.json", b"{}"),
        ]

        await run_with_files(
            agent,
            "Test query",
            deps,
            files=files,
        )

        # Files should be uploaded and tracked in file_paths
        assert "/uploads/data.csv" in deps.file_paths
        assert "/uploads/config.json" in deps.file_paths

    @pytest.mark.anyio
    async def test_run_with_files_custom_upload_dir(self):
        """Test run_with_files with custom upload directory."""
        agent = create_deep_agent(model=TEST_MODEL)
        deps = DeepAgentDeps(backend=StateBackend())

        files = [("test.txt", b"content")]

        await run_with_files(
            agent,
            "Test query",
            deps,
            files=files,
            upload_dir="/custom",
        )

        assert "/custom/test.txt" in deps.file_paths

    @pytest.mark.anyio
    async def test_run_with_files_no_files(self):
        """Test run_with_files with no files."""
        agent = create_deep_agent(model=TEST_MODEL)
        deps1 = DeepAgentDeps(backend=StateBackend())
        deps2 = DeepAgentDeps(backend=StateBackend())

        # Should not raise error
        await run_with_files(agent, "Test query", deps1, files=None)
        await run_with_files(agent, "Test query", deps2, files=[])

        assert deps1.file_paths == []
        assert deps2.file_paths == []

