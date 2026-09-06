"""Prompt templates for the OpenAI provider.

The prompts are designed to produce structured JSON output that maps to
AIInsights. We instruct the model to be conservative and mark inferences.
"""
from __future__ import annotations

import json

from models.ai import AIContextPayload


def build_system_prompt() -> str:
    return (
        "You are CodeLens AI, a PR analysis assistant. Your job is to help a "
        "code reviewer understand a pull request. You receive compact, "
        "structured context about a PR (NOT the full repository). "
        "You must produce structured JSON output.\n\n"
        "Rules:\n"
        "1. Base your analysis ONLY on the provided context. Do not invent "
        "files, findings, or facts not present in the context.\n"
        "2. Mark any reasoning that cannot be directly verified as an "
        "inference (is_inference=true).\n"
        "3. Be concise and specific. Avoid generic statements.\n"
        "4. Do not claim scientific certainty. Use hedged language for "
        "inferences.\n"
        "5. Your output must be valid JSON matching the specified schema.\n"
    )


def build_user_prompt(payload: AIContextPayload) -> str:
    context = {
        "pr_title": payload.pr_title,
        "pr_body": payload.pr_body,
        "pr_author": payload.pr_author,
        "files_changed": payload.files_changed,
        "lines_added": payload.lines_added,
        "lines_removed": payload.lines_removed,
        "size_class": payload.size_class,
        "functional_areas": payload.functional_areas,
        "scope_drift": payload.scope_drift,
        "critical_areas": payload.critical_areas,
        "findings": payload.finding_summaries,
    }

    schema_hint = {
        "pr_intent": "string — what the PR is trying to accomplish",
        "functional_area_interpretation": "string — interpretation of affected areas",
        "scope_drift_reasoning": "object or null — {assessment: string, is_inference: true} if scope drift present, else null",
        "finding_explanations": "array of {finding_id: string, explanation: string, is_inference: boolean}",
        "risk_reasoning": "string — narrative explanation of overall risk",
    }

    return (
        f"Analyze the following PR context and produce structured insights.\n\n"
        f"PR Context (JSON):\n{json.dumps(context, indent=2)}\n\n"
        f"Output JSON schema:\n{json.dumps(schema_hint, indent=2)}\n\n"
        f"Return ONLY valid JSON matching the schema. No markdown, no commentary."
    )
