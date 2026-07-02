# Architecture

ComputeForge follows a layered architecture with clear separation of concerns.

## Layer Overview

### 1. Interface Layer
- **CLI** (Typer) — Command-line interface for running and debugging sessions
- **SDK** (Python) — High-level client for programmatic access
- **Dashboard** (Gradio) — Visual monitoring, replay, and control
- **API** (FastAPI) — REST API for remote access

### 2. Engine Layer
- **ComputeEngine** — Orchestrates session lifecycle and action dispatch
- **BrowserManager** — Manages Playwright browser instances
- **Action Registry** — Maps action types to handlers

### 3. Control Layer
- **Browser Backend** — Playwright-based browser automation
- **Desktop Backend** — PyAutoGUI and MSS for OS-level control
- **ElementFinder** — Multi-strategy element location with fallbacks

### 4. Cross-Cutting Layers
- **Safety** — Permission system, risk assessment, policy enforcement
- **Observability** — Session recording, screenshot capture, replay
- **Extensibility** — Plugin system, hooks, integration adapters

### 5. Storage Layer
- **SQLite** — Session metadata and action records
- **File System** — Screenshots and binary assets

## Key Design Decisions

- **Async-first**: All I/O operations are async for performance
- **Plugin-based**: Extensible via entry points and hook system
- **Provider abstraction**: LLM providers via strategy pattern
- **Safety by default**: Critical actions blocked by default
