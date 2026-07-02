"""Tests for the SDK agent."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from computeforge.core.actions import ActionResult, ActionType
from computeforge.models.session import SessionConfig
from computeforge.sdk.agent import Agent, AgentBuilder


class TestAgentBuilder:
    def test_builder_requires_provider(self):
        builder = AgentBuilder()
        with pytest.raises(ValueError, match="Provider is required"):
            builder.build()

    def test_builder_creates_agent(self):
        provider = MagicMock()
        with patch("computeforge.sdk.agent.ComputeEngine") as mock_engine:
            agent = AgentBuilder().with_provider(provider).build()
            assert isinstance(agent, Agent)
            assert agent._provider is provider
            mock_engine.assert_called_once()

    def test_builder_configuration(self):
        provider = MagicMock()
        engine_config = MagicMock()
        session_config = MagicMock()
        with patch("computeforge.sdk.agent.ComputeEngine"):
            agent = (
                AgentBuilder()
                .with_provider(provider)
                .with_config(engine_config)
                .with_session_config(session_config)
                .with_max_iterations(10)
                .build()
            )
            assert agent._max_iterations == 10

    def test_builder_hooks(self):
        provider = MagicMock()
        pre_hook = MagicMock()
        post_hook = MagicMock()
        with patch("computeforge.sdk.agent.ComputeEngine") as mock_engine:
            instance = mock_engine.return_value
            (
                AgentBuilder()
                .with_provider(provider)
                .add_pre_action_hook(pre_hook)
                .add_post_action_hook(post_hook)
                .build()
            )
            instance.register_pre_action_hook.assert_called_once_with(pre_hook)
            instance.register_post_action_hook.assert_called_once_with(post_hook)

    def test_builder_adds_multiple_hooks(self):
        provider = MagicMock()
        hooks = [MagicMock(), MagicMock()]
        with patch("computeforge.sdk.agent.ComputeEngine") as mock_engine:
            instance = mock_engine.return_value
            builder = AgentBuilder().with_provider(provider)
            for h in hooks:
                builder.add_pre_action_hook(h)
            builder.build()
            assert instance.register_pre_action_hook.call_count == 2


class TestAgent:
    @pytest.fixture
    def mock_provider(self):
        provider = MagicMock()
        provider.act = AsyncMock(return_value={"type": "finished", "params": {}})
        return provider

    @pytest.fixture
    def mock_engine(self):
        engine = MagicMock()
        engine.create_session = AsyncMock()
        engine.start_session = AsyncMock()
        engine.stop_session = AsyncMock()
        engine.is_running = True
        engine.screenshot = AsyncMock(
            return_value=ActionResult(success=True, data={"image": b"fake_screenshot"})
        )
        engine.extract_text = AsyncMock(
            return_value=ActionResult(success=True, data={"text": "Sample page text"})
        )
        engine.execute = AsyncMock(
            return_value=ActionResult(
                success=True, action_type=ActionType.CLICK, data={}
            )
        )
        return engine

    def test_agent_properties(self, mock_provider, mock_engine):
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
            max_iterations=20,
        )
        assert agent.action_history == []
        assert agent.engine is mock_engine

    @pytest.mark.asyncio
    async def test_agent_run_immediate_success(self, mock_provider, mock_engine):
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
        )
        result = await agent.run("test task")
        assert result["success"] is True
        assert result["actions_taken"] == 0
        assert result["task"] == "test task"
        mock_engine.create_session.assert_called_once()
        mock_engine.start_session.assert_called_once()
        mock_engine.stop_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_run_single_action(self, mock_provider, mock_engine):
        mock_provider.act = AsyncMock(
            side_effect=[
                {"type": "click", "params": {"selector": "#btn"}},
                {"type": "finished", "params": {}},
            ]
        )
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
        )
        result = await agent.run("click the button")
        assert result["success"] is True
        assert result["actions_taken"] == 1
        assert len(agent.action_history) == 1
        assert agent.action_history[0]["type"] == "click"
        assert agent.action_history[0]["success"] is True

    @pytest.mark.asyncio
    async def test_agent_run_action_error(self, mock_provider, mock_engine):
        mock_provider.act = AsyncMock(
            side_effect=[
                {"type": "click", "params": {"selector": "#missing"}},
                {"type": "finished", "params": {}},
            ]
        )
        mock_engine.execute = AsyncMock(side_effect=Exception("Element not found"))
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
        )
        result = await agent.run("click the missing button")
        assert result["success"] is True
        assert result["actions_taken"] == 1
        assert agent.action_history[0]["success"] is False
        assert "Element not found" in agent.action_history[0]["error"]

    @pytest.mark.asyncio
    async def test_agent_run_outer_error(self, mock_provider, mock_engine):
        mock_provider.act = AsyncMock(side_effect=Exception("Provider crashed"))
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
        )
        result = await agent.run("test task")
        assert result["success"] is False
        assert result["error"] == "Provider crashed"
        mock_engine.stop_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_agent_run_engine_not_running(self, mock_provider, mock_engine):
        mock_engine.is_running = False
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
        )
        result = await agent.run("test task")
        assert result["success"] is False
        assert result["actions_taken"] == 0

    @pytest.mark.asyncio
    async def test_agent_run_max_iterations(self, mock_provider, mock_engine):
        mock_provider.act = AsyncMock(
            return_value={"type": "click", "params": {"selector": "#btn"}}
        )
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
            max_iterations=3,
        )
        result = await agent.run("test task")
        assert result["success"] is True
        assert result["actions_taken"] == 3
        assert "note" in result

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, mock_provider, mock_engine):
        agent = Agent(
            provider=mock_provider,
            engine=mock_engine,
            session_config=SessionConfig(),
        )
        await agent.run("test")
        mock_engine.create_session.assert_called_once()
        mock_engine.start_session.assert_called_once()
        mock_engine.stop_session.assert_called_once()
