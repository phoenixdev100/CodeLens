"""Phase 4 Engine: orchestrates analysis + AI + risk + priority.

Consumes a Phase 2 AnalysisContext, runs the Phase 3 analysis engine,
then adds AI insights, risk scoring, and review priority to produce a
Phase4Result.
"""
from __future__ import annotations

from config import Settings, get_settings
from models.context import AnalysisContext
from models.phase4 import Phase4Result
from ai.analyzer import AIAnalyzer
from analysis.engine import AnalysisEngine
from priority.engine import PriorityEngine
from risk.engine import RiskEngine


class Phase4Engine:
    """Full pipeline: deterministic analysis → AI → risk → priority."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.analysis_engine = AnalysisEngine(self.settings)
        self.ai_analyzer = AIAnalyzer(self.settings)
        self.risk_engine = RiskEngine(self.settings)
        self.priority_engine = PriorityEngine()

    def analyze(self, ctx: AnalysisContext) -> Phase4Result:
        # Phase 3: deterministic analysis
        analysis = self.analysis_engine.analyze(ctx)

        # Phase 4: AI insights (mock or OpenAI)
        ai_insights = self.ai_analyzer.analyze(analysis)

        # Phase 4: risk scoring
        risk = self.risk_engine.assess(analysis)

        # Phase 4: review priority
        priority = self.priority_engine.prioritize(analysis)

        stats = {
            "total_findings": len(analysis.all_findings),
            "risk_score": risk.total_score,
            "risk_level": risk.level,
            "priority_items": len(priority.items),
            "ai_provider": 1 if ai_insights.provider == "openai" else 0,
            "critical_areas": len(analysis.critical.areas),
        }

        return Phase4Result(
            meta=ctx.meta,
            analysis=analysis,
            ai_insights=ai_insights,
            risk=risk,
            priority=priority,
            stats=stats,
        )
