import pytest

from backend import factories


class DummyOpenAIClient:
    def send_prompt(self, prompt: str, model: str = "gpt-4o-mini") -> str:
        return "dummy response"


@pytest.fixture
def factory() -> factories.OpenAIVerdictFactory:
    client = DummyOpenAIClient()
    return factories.OpenAIVerdictFactory(client)


@pytest.mark.asyncio
async def test_openai_factory(
    sample_eml: bytes, factory: factories.OpenAIVerdictFactory
):
    eml = factories.EmlFactory().call(sample_eml)
    verdict = await factory.call(eml)
    assert verdict.details[0].description == "dummy response"
