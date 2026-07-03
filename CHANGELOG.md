# Changelog

## v0.1.0 (2026-07-03)

Initial release of ComputeForge — an open-source, extensible Computer-Use Agent Platform.

### Added
- **Core Engine**: Playwright-based browser automation with smart element finding, multi-browser support (Chromium, Firefox, WebKit), desktop control (pyautogui + MSS)
- **Observability**: Full session recording, screenshot capture at configurable intervals, visual replay generation (GIF/HTML/JSON), FlowLens integration
- **Safety**: Capability registry with risk levels, configurable policy engine (allow/deny/confirm), domain pattern matching, rate limiting, GuardWeave integration
- **Extensibility**: Plugin system via `importlib.metadata` entry_points + directory hot-reload, lifecycle hooks (before/after action, session events), SkillForge integration
- **LLM Providers**: DeepSeek, OpenAI, Ollama, Groq, Gemini with uniform interface
- **SDK**: High-level client, agent builder with provider configuration, workflow composition
- **CLI**: Typer-based commands for running sessions, replay, config management, interactive shell
- **Dashboard**: Gradio-based live monitoring, replay viewer, session management, manual intervention
- **API**: FastAPI REST API with session CRUD, action listing, replay data, WebSocket streaming
- **Testing**: 937 tests across all modules with 100% line coverage
- **CI/CD**: GitHub Actions pipeline (lint, test on 3.12/3.13, integration, security, build)
- **Docker**: Dockerfile + docker-compose for one-command deployment
- **Documentation**: Architecture overview, getting-started guide, observability/safety/extensibility docs, API reference
