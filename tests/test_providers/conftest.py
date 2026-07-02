from __future__ import annotations

import sys
from unittest.mock import MagicMock

if "openai" not in sys.modules:
    import types
    m = types.ModuleType("openai")
    m.AsyncOpenAI = MagicMock()
    sys.modules["openai"] = m

if "google" not in sys.modules:
    import types
    gm = types.ModuleType("google")
    gm.__path__ = []
    ggm = types.ModuleType("google.genai")
    ggm.aio = MagicMock()
    gm.genai = ggm
    sys.modules["google"] = gm
    sys.modules["google.genai"] = ggm
