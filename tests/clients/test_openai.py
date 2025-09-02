from starlette.datastructures import Secret

from backend.clients.openai import Openai
from backend import settings


class DummyClient:
    def __init__(self, *, api_key, timeout=None):
        self.api_key = api_key
        self.timeout = timeout


def test_openai_passes_custom_timeout(monkeypatch):
    created = {}

    def dummy_ctor(*, api_key, timeout=None):
        created['api_key'] = api_key
        created['timeout'] = timeout
        return DummyClient(api_key=api_key, timeout=timeout)

    monkeypatch.setattr('backend.clients.openai.AsyncOpenAI', dummy_ctor)
    client = Openai(api_key=Secret('secret'), timeout=123)
    assert isinstance(client.client, DummyClient)
    assert created['api_key'] == 'secret'
    assert created['timeout'] == 123


def test_openai_uses_default_timeout(monkeypatch):
    created = {}

    def dummy_ctor(*, api_key, timeout=None):
        created['timeout'] = timeout
        return DummyClient(api_key=api_key, timeout=timeout)

    monkeypatch.setattr('backend.clients.openai.AsyncOpenAI', dummy_ctor)
    Openai(api_key=Secret('secret'))
    assert created['timeout'] == settings.OPENAI_TIMEOUT
