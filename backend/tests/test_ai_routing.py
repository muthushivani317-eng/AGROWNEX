"""Unit tests for AI model routing + Flash→Pro fallback (Phase 1)."""
from __future__ import annotations

import pytest
from app.modules.ai.exceptions import AIUnavailableError
from app.modules.ai.provider import AIResult, RoutedChatProvider


class _Provider:
    def __init__(self, model: str, *, text: str = "", raise_error: bool = False):
        self.model = model
        self._text = text
        self._raise = raise_error
        self.calls = 0

    async def generate(self, *, system, history, message) -> AIResult:
        self.calls += 1
        if self._raise:
            raise AIUnavailableError()
        return AIResult(text=self._text, model=self.model)


async def test_uses_flash_when_it_answers():
    primary = _Provider("gemini-2.5-flash", text="Flash answer")
    fallback = _Provider("gemini-2.5-pro", text="Pro answer")
    provider = RoutedChatProvider(primary=primary, fallback=fallback)

    result = await provider.generate(system="s", history=[], message="hi")

    assert result.text == "Flash answer"
    assert result.model == "gemini-2.5-flash"
    assert primary.calls == 1
    assert fallback.calls == 0  # no needless (expensive) Pro call


async def test_escalates_to_pro_after_two_empty_flash_responses():
    primary = _Provider("gemini-2.5-flash", text="   ")  # empty/whitespace
    fallback = _Provider("gemini-2.5-pro", text="Pro rescue")
    provider = RoutedChatProvider(primary=primary, fallback=fallback)

    result = await provider.generate(system="s", history=[], message="hi")

    assert result.text == "Pro rescue"
    assert result.model == "gemini-2.5-pro"
    assert primary.calls == 2  # tried Flash twice before escalating
    assert fallback.calls == 1


async def test_hard_failure_escalates_immediately():
    primary = _Provider("gemini-2.5-flash", raise_error=True)
    fallback = _Provider("gemini-2.5-pro", text="Pro rescue")
    provider = RoutedChatProvider(primary=primary, fallback=fallback)

    result = await provider.generate(system="s", history=[], message="hi")

    assert result.text == "Pro rescue"
    assert primary.calls == 1  # no pointless retry on a hard failure
    assert fallback.calls == 1


async def test_fallback_failure_propagates():
    primary = _Provider("gemini-2.5-flash", raise_error=True)
    fallback = _Provider("gemini-2.5-pro", raise_error=True)
    provider = RoutedChatProvider(primary=primary, fallback=fallback)

    with pytest.raises(AIUnavailableError):
        await provider.generate(system="s", history=[], message="hi")
