"""Abstract AI provider interface.

All AI providers implement this interface. The analyzer selects the provider
based on configuration (OpenAI if key is present, else mock).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from models.ai import AIContextPayload, AIInsights


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name: 'openai' | 'mock' | etc."""
        ...

    @abstractmethod
    def analyze(self, payload: AIContextPayload) -> AIInsights:
        """Produce structured AI insights from a compact context payload.

        Must return a validated AIInsights object. Must never raise in a way
        that breaks the pipeline — on failure, return a degraded AIInsights
        with an explanation.
        """
        ...
