# Observability

ComputeForge provides comprehensive observability for computer-use sessions.

## Session Recording

Every action within a session is recorded with:
- Action type and parameters
- Timestamps and duration
- Success/failure status
- Error messages
- Risk assessment results
- Screenshots (before/after)

## Storage

- **Metadata**: SQLite database at `~/.computeforge/sessions.db`
- **Screenshots**: File system at `~/.computeforge/screenshots/<session_id>/`

## Visual Replay

The replay system provides step-by-step playback:
1. Load a session by ID
2. Navigate through actions with a slider
3. View screenshots at each step
4. See action details and timing

### CLI Replay

```bash
# List actions
computeforge replay <session_id> --list

# Interactive replay
computeforge replay <session_id> --interactive
```

### Dashboard Replay

Open the Dashboard → **Replay** tab to browse and step through sessions visually.

## FlowLens Integration

ComputeForge can push observability events to FlowLens:

```bash
export COMPUTEFORGE_FLOWLENS_ENDPOINT=http://localhost:3030
```
