"""Tests for the workflow system."""

from unittest.mock import AsyncMock

import pytest

from computeforge.core.actions import ActionResult, ActionType
from computeforge.core.engine import ComputeEngine
from computeforge.sdk.workflow import Workflow, WorkflowStep


def test_workflow_build():
    wf = Workflow("test")
    wf.navigate("https://example.com").click("#btn").screenshot("result")
    assert len(wf._steps) == 3
    assert wf._steps[0].action_type == ActionType.NAVIGATE
    assert wf._steps[1].action_type == ActionType.CLICK


def test_workflow_custom_step():
    wf = Workflow("custom")
    step = WorkflowStep(name="custom_action", action_type=ActionType.EVALUATE, params={"script": "1+1"})
    wf.add_step(step)
    assert len(wf._steps) == 1
    assert wf._steps[0].name == "custom_action"


def test_workflow_context():
    wf = Workflow("ctx")
    assert wf.context == {}
    wf.navigate("https://example.com")
    assert len(wf._steps) == 1


def test_workflow_fluent():
    wf = (Workflow("fluent")
        .navigate("https://a.com")
        .click("#btn1")
        .type_text("hello", "#input")
        .scroll(delta_y=200)
        .screenshot("final"))
    assert len(wf._steps) == 5
    assert wf._steps[0].action_type == ActionType.NAVIGATE
    assert wf._steps[2].action_type == ActionType.TYPE


def test_workflow_extract_text():
    wf = Workflow("ext")
    wf.extract_text("my_extract")
    assert len(wf._steps) == 1
    assert wf._steps[0].action_type == ActionType.EXTRACT_TEXT
    assert wf._steps[0].name == "my_extract"


def test_workflow_results_property():
    wf = Workflow("res")
    assert wf.results == []
    wf._results.append(ActionResult(success=True, action_type=ActionType.SCREENSHOT))
    assert len(wf.results) == 1
    assert wf.results[0].success is True


@pytest.mark.asyncio
async def test_workflow_execute_success():
    engine = AsyncMock(spec=ComputeEngine)
    result = ActionResult(success=True, action_type=ActionType.NAVIGATE, data={"url": "https://example.com"})
    engine.execute = AsyncMock(return_value=result)

    wf = Workflow("exec_test")
    wf.navigate("https://example.com")
    results = await wf.execute(engine)

    assert len(results) == 1
    assert results[0].success is True
    engine.execute.assert_awaited_once_with(ActionType.NAVIGATE, url="https://example.com")


@pytest.mark.asyncio
async def test_workflow_execute_on_failure_stop():
    engine = AsyncMock(spec=ComputeEngine)
    fail_result = ActionResult(success=False, action_type=ActionType.NAVIGATE, error="fail")
    engine.execute = AsyncMock(return_value=fail_result)

    wf = Workflow("stop_test")
    step = WorkflowStep(name="step1", action_type=ActionType.NAVIGATE, params={"url": "https://x.com"}, on_failure="stop")
    wf.add_step(step)
    wf.navigate("https://y.com")
    results = await wf.execute(engine)

    assert len(results) == 1
    assert results[0].success is False


@pytest.mark.asyncio
async def test_workflow_execute_on_failure_retry():
    engine = AsyncMock(spec=ComputeEngine)
    fail_result = ActionResult(success=False, action_type=ActionType.NAVIGATE, error="fail")
    engine.execute = AsyncMock(return_value=fail_result)

    wf = Workflow("retry_test")
    step = WorkflowStep(name="step1", action_type=ActionType.NAVIGATE, params={"url": "https://x.com"}, on_failure="retry", max_retries=3)
    wf.add_step(step)
    results = await wf.execute(engine)

    assert len(results) == 3
    assert engine.execute.await_count == 3


@pytest.mark.asyncio
async def test_workflow_execute_on_failure_skip():
    engine = AsyncMock(spec=ComputeEngine)
    fail_result = ActionResult(success=False, action_type=ActionType.NAVIGATE, error="fail")
    engine.execute = AsyncMock(return_value=fail_result)

    wf = Workflow("skip_test")
    step = WorkflowStep(name="step1", action_type=ActionType.NAVIGATE, params={"url": "https://x.com"}, on_failure="skip")
    wf.add_step(step)
    results = await wf.execute(engine)

    assert len(results) == 1
    assert engine.execute.await_count == 1


@pytest.mark.asyncio
async def test_workflow_execute_context_populated():
    engine = AsyncMock(spec=ComputeEngine)
    result = ActionResult(success=True, action_type=ActionType.NAVIGATE, data={"url": "https://example.com"})
    engine.execute = AsyncMock(return_value=result)

    wf = Workflow("ctx_test")
    wf.navigate("https://example.com")
    await wf.execute(engine)

    assert wf.context["Navigate to https://example.com"] == {"url": "https://example.com"}


@pytest.mark.asyncio
async def test_workflow_execute_context_none_on_failure():
    engine = AsyncMock(spec=ComputeEngine)
    result = ActionResult(success=False, action_type=ActionType.NAVIGATE, error="fail")
    engine.execute = AsyncMock(return_value=result)

    wf = Workflow("ctx_fail")
    wf.navigate("https://example.com")
    await wf.execute(engine)

    assert wf.context["Navigate to https://example.com"] is None


@pytest.mark.asyncio
async def test_workflow_execute_exception_exhausted():
    engine = AsyncMock(spec=ComputeEngine)
    engine.execute = AsyncMock(side_effect=ValueError("engine error"))

    wf = Workflow("exc_test")
    wf.navigate("https://example.com")
    results = await wf.execute(engine)

    assert len(results) == 1
    assert results[0].success is False
    assert str(results[0].error) == "engine error"


@pytest.mark.asyncio
async def test_workflow_execute_exception_stop():
    engine = AsyncMock(spec=ComputeEngine)
    engine.execute = AsyncMock(side_effect=ValueError("engine error"))

    wf = Workflow("exc_stop")
    step = WorkflowStep(name="step1", action_type=ActionType.NAVIGATE, params={"url": "https://x.com"}, on_failure="stop", max_retries=2)
    wf.add_step(step)
    results = await wf.execute(engine)

    assert len(results) == 1
    assert results[0].success is False
    assert "engine error" in results[0].error


@pytest.mark.asyncio
async def test_workflow_execute_multi_step():
    engine = AsyncMock(spec=ComputeEngine)
    engine.execute = AsyncMock(side_effect=[
        ActionResult(success=True, action_type=ActionType.NAVIGATE, data={"url": "https://a.com"}),
        ActionResult(success=True, action_type=ActionType.CLICK, data={}),
    ])

    wf = Workflow("multi")
    wf.navigate("https://a.com")
    wf.click("#btn")
    results = await wf.execute(engine)

    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is True


@pytest.mark.asyncio
async def test_workflow_execute_empty():
    engine = AsyncMock(spec=ComputeEngine)
    wf = Workflow("empty")
    results = await wf.execute(engine)
    assert results == []
