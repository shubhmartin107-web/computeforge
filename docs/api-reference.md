# API Reference

## Engine API

### ComputeEngine

```python
engine = ComputeEngine(config=EngineConfig())
await engine.create_session(config=SessionConfig())
await engine.start_session()
await engine.navigate(url: str) -> ActionResult
await engine.click(selector: str) -> ActionResult
await engine.type_text(text: str, selector: str | None) -> ActionResult
await engine.screenshot() -> ActionResult
await engine.scroll(delta_y: int) -> ActionResult
await engine.extract_text(selector: str | None) -> ActionResult
await engine.stop_session()
```

## REST API

### Sessions

- `POST /api/v1/sessions` — Create session
- `POST /api/v1/sessions/{id}/start` — Start session
- `POST /api/v1/sessions/{id}/stop` — Stop session
- `POST /api/v1/sessions/{id}/pause` — Pause session
- `POST /api/v1/sessions/{id}/resume` — Resume session
- `GET /api/v1/sessions/{id}` — Get session details
- `GET /api/v1/sessions` — List sessions

### Actions

- `POST /api/v1/actions/execute` — Execute single action
- `POST /api/v1/actions/batch` — Execute batch of actions

### Health

- `GET /api/v1/health` — Health check

## CLI Reference

```bash
computeforge run <url> [options]
computeforge replay <session_id> [options]
computeforge config [show|set|reset|caps|policies]
computeforge --version
```

## SDK Reference

### ComputeForgeClient

```python
client = ComputeForgeClient()
await client.connect()
await client.create_session(config=SessionConfig())
await client.navigate(url)
await client.click(selector)
await client.type_text(text, selector)
await client.screenshot()
await client.extract_text()
await client.list_sessions()
await client.export_session(session_id, output_path)
await client.close()
```

### Agent

```python
agent = AgentBuilder().with_provider(provider).build()
result = await agent.run(task: str)
```

### Workflow

```python
workflow = Workflow("name")
workflow.navigate(url).click(selector).screenshot()
results = await workflow.execute(engine)
```
