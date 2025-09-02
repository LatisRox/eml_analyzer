import asyncio
import sys
import types
from pathlib import Path
from importlib.machinery import SourceFileLoader


def test_multiple_context_managers_close_client(monkeypatch):
    """Ensure the OpenAI client is closed after each context use."""
    module = types.ModuleType("openai")
    closed_calls = 0

    class DummyResponse:
        output_text = "ok"

    class DummyResponses:
        async def create(self, *, model: str, input: str):  # type: ignore[override]
            return DummyResponse()

    class DummyAsyncOpenAI:
        def __init__(self, api_key: str):
            self.responses = DummyResponses()

        async def close(self):
            nonlocal closed_calls
            closed_calls += 1

    module.AsyncOpenAI = DummyAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)

    loguru_module = types.ModuleType("loguru")
    class DummyLogger:
        def debug(self, *args, **kwargs):
            pass
        def warning(self, *args, **kwargs):
            pass
        def exception(self, *args, **kwargs):
            pass
    loguru_module.logger = DummyLogger()
    monkeypatch.setitem(sys.modules, "loguru", loguru_module)

    starlette_module = types.ModuleType("starlette")
    ds_module = types.ModuleType("starlette.datastructures")
    class Secret(str):
        def get_secret_value(self):
            return str(self)
    ds_module.Secret = Secret
    starlette_module.datastructures = ds_module
    monkeypatch.setitem(sys.modules, "starlette", starlette_module)
    monkeypatch.setitem(sys.modules, "starlette.datastructures", ds_module)

    module_path = Path(__file__).resolve().parents[2] / "backend" / "clients" / "openai.py"
    openai_client = SourceFileLoader("openai_client", str(module_path)).load_module()

    async def run():
        for _ in range(3):
            async with openai_client.Openai(api_key="test") as client:
                await client.send_prompt("hello")

    asyncio.run(run())
    assert closed_calls == 3
