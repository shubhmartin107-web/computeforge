# Extensibility

ComputeForge is designed to be extended at every level.

## Plugin System

Plugins implement `PluginBase` and can hook into all lifecycle events:

```python
from computeforge.extensibility.plugin import PluginBase, PluginMeta

class TimingPlugin(PluginBase):
    def get_meta(self):
        return PluginMeta(name="timing", version="1.0.0", description="Logs action timing")

    async def on_action_before(self, request):
        request.metadata["start_time"] = time.time()
        return request

    async def on_action_after(self, request, result):
        start = request.metadata.get("start_time")
        if start:
            print(f"Action took {time.time() - start:.3f}s")
```

### Registration

Via entry points in `pyproject.toml`:
```toml
[project.entry-points."computeforge.plugins"]
my-plugin = "my_package:MyPlugin"
```

Or directly:
```python
from computeforge.extensibility.registry import PluginRegistry
registry = PluginRegistry()
registry.register(MyPlugin())
```

## Hook System

Fine-grained hooks for specific lifecycle points:
- `BEFORE_ACTION` — Modify or intercept actions
- `AFTER_ACTION` — Observe results
- `SAFETY_CHECK` — Custom safety rules
- `ON_ERROR` — Error handling
- `SESSION_START/END` — Session lifecycle

## Integration Adapters

### SkillForge

Execute reusable skills from SkillForge:

```python
from computeforge.extensibility.skillforge import SkillForgeAdapter
sf = SkillForgeAdapter(endpoint="http://localhost:9090")
await sf.connect()
skills = await sf.list_skills()
```

### FlowLens

Push observability events:

```python
from computeforge.observability.flowlens import FlowLensAdapter
fl = FlowLensAdapter(endpoint="http://localhost:3030")
await fl.connect()
await fl.push_action(action_record, session_id)
```

### GuardWeave

Delegate safety decisions:

```python
from computeforge.safety.guardweave import GuardWeaveAdapter
gw = GuardWeaveAdapter(endpoint="http://localhost:8080")
engine.register_safety_hook(gw.make_safety_hook())
```
