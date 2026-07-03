# ComputeForge — Agent Context

## Project
Open-source, extensible Computer-Use Agent Platform with browser/desktop control, observability, safety, dashboard, extensibility, LLM providers, SDK, and full documentation.

## Stack
Python 3.12+, Playwright, Gradio 5.x+, FastAPI, SQLite + file storage, Pydantic, Typer, httpx, Pillow

## Key Facts
- **937 tests**, 100% line coverage (4,297 statements, 0 missed)
- **0 lint errors** (ruff, mypy, bandit all pass)
- **6 CI jobs all green**: lint, test (3.12), test (3.13), security, integration, build
- Repo: https://github.com/shubhmartin107-web/computeforge
- Virtual env: `/home/synapsex/computeforge/.venv/`
- Playwright browsers at `~/.cache/ms-playwright/`
- 50 source modules under `src/computeforge/`

## Interface Entry Points
| Interface | Command |
|---|---|
| CLI | `computeforge run/repaly/config/shell` |
| SDK | `from computeforge.sdk.client import ComputeForgeClient` |
| Dashboard | `python -m computeforge.dashboard.app` → `:7860` |
| API | `uvicorn computeforge.api.server:app` → `:8000` |

## Architecture
- **Core**: actions, browser (Playwright), desktop (pyautogui+MSS), element finding, engine, recovery
- **Providers**: base + DeepSeek, OpenAI, Ollama, Groq, Gemini
- **Safety**: permissions, risk assessment, policy engine (YAML), GuardWeave adapter
- **Observability**: session recorder (SQLite WAL, batch flush), screenshot capture, replay (GIF/HTML/JSON), FlowLens adapter
- **Extensibility**: plugin system (entry_points + directory hot-reload), lifecycle hooks, SkillForge adapter
- **SDK**: client, agent builder, workflow composer, progress tracking
- **API**: FastAPI routes for sessions, actions, replay, WebSocket streaming
- **Dashboard**: Gradio monitoring, replay viewer, session manager, intervention panel

## Testing
- `conftest.py` provides shared fixtures for all test modules
- `factories.py` provides factory functions for model construction
- `mocks/playwright_mock.py` provides reusable Playwright mock classes
- Run: `pytest tests/`
- Coverage: `pytest --cov=src/computeforge --cov-report=html`

## CI Pipeline (`.github/workflows/ci.yml`)
1. **lint**: ruff check, ruff format --check, mypy (with `.[dev]` installed for type stubs)
2. **test**: matrix {3.12, 3.13}, install `.[dev]`, playwright install chromium, pytest
3. **integration**: depends on lint+test, runs `-m integration` tests
4. **security**: bandit + pip-audit
5. **build**: python -m build

## Key Decisions
- Multi-browser from start (Chromium default, Firefox + WebKit available)
- Rate limiting + domain pattern matching in PolicyEngine
- WebSocket endpoint for real-time session streaming
- SQLite WAL mode for concurrent reads
- Plugin system uses `importlib.metadata` entry_points + directory hot-reload
- All 5 LLM providers built-in from v0.1
- Batch save buffering in SessionRecorder (10 actions per flush)
- Policy YAML files in `config/policies/` with hot-reload
- Shared test mocks to avoid mocking Playwright in every test file

## Next Steps
- Add SSH deploy key or fresh fine-grained token (both PATs in conversation should be revoked)
- Add more end-to-end integration tests with real Playwright browser
- Set up Codecov for continuous coverage tracking
- Publish to PyPI once stable
