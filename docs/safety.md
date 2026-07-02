# Safety & Guardrails

ComputeForge includes a multi-layer safety system.

## Capability Registry

All system capabilities are declared with:
- **Name** — Unique identifier
- **Risk Level** — Low, Medium, High, Critical
- **Required Permissions** — Fine-grained permission scopes
- **Parameters** — Valid parameter definitions

View capabilities: `computeforge config caps`

## Risk Assessment

Every action is assessed before execution:
- **URL Analysis** — Detects dangerous URLs (file://, javascript:, private networks)
- **Script Analysis** — Scans JavaScript for dangerous API usage
- **Action Type** — Evaluates based on capability risk level
- **Context Analysis** — Considers page context and parameters

## Policy Engine

Policies define rules for action decisions:
- **Allow** — Action proceeds
- **Deny** — Action is blocked
- **Require Confirmation** — Action needs human approval

Default policies block:
- JavaScript execution (evaluate)
- Desktop clicks and keystrokes

View policies: `computeforge config policies`

## GuardWeave Integration

For advanced governance, integrate with GuardWeave:

```python
from computeforge.safety.guardweave import GuardWeaveAdapter

adapter = GuardWeaveAdapter(endpoint="http://localhost:8080")
await adapter.connect()
```

## Configuration

Safety is configured via `EngineConfig`:

```python
config = EngineConfig()
config.safety.enabled = True
config.safety.risk_threshold = "high"
config.safety.blocklist_domains = ["malicious.example.com"]
```
