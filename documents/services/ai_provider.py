from dataclasses import dataclass

from django.conf import settings

from .ai_extractor import extract_worklog_data


class AIProviderError(Exception):
    pass


@dataclass(frozen=True)
class MockAIProvider:
    name: str = "mock"

    def extract(self, text: str) -> dict:
        return extract_worklog_data(text)


@dataclass(frozen=True)
class OpenAIProvider:
    name: str = "openai"
    api_key: str = ""

    def extract(self, text: str) -> dict:
        if not self.api_key:
            raise AIProviderError("AI_PROVIDER=openai requires AI_API_KEY in the environment.")
        raise AIProviderError("OpenAI provider is scaffolded, but real API calls are not enabled yet.")


def get_ai_provider(provider_name: str | None = None):
    provider = (provider_name or settings.AI_PROVIDER or "mock").strip().lower()
    if provider == "mock":
        return MockAIProvider()
    if provider == "openai":
        return OpenAIProvider(api_key=settings.AI_API_KEY)
    raise AIProviderError(f"Unsupported AI_PROVIDER '{provider}'. Use 'mock' for the local MVP.")
