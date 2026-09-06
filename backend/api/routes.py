"""API routes for Phase 1-5: GitHub Foundation, Repository Context, Analysis Engine, AI + Risk + Priority, Impact Map."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from analysis.engine import AnalysisEngine
from config import get_settings
from context.builder import ContextBuilder
from github.auth import GitHubAuthError, GitHubAuthenticator
from github.client import GitHubAPIError, GitHubClient, summarize_diff
from github.url_parser import InvalidPRURL, parse_pr_url
from impact_map.builder import ImpactMapBuilder
from models.analysis import AnalysisResult
from models.context import AnalysisContext
from models.impact_map import ImpactMap
from models.phase4 import Phase4Result
from models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
)
from phase4 import Phase4Engine

router = APIRouter(prefix="/api", tags=["codeLens"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    auth = GitHubAuthenticator(settings)
    return HealthResponse(status="ok", auth_mode=auth.mode)


@router.post("/analyze", response_model=AnalyzeResponse, responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}})
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    # Validate URL shape early (before hitting GitHub).
    try:
        owner, repo, number = parse_pr_url(req.pr_url)
    except InvalidPRURL as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    settings = get_settings()
    client = GitHubClient(settings=settings)

    try:
        meta, files, raw_diff = client.fetch_all(req.pr_url)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub auth error: {exc}")
    except GitHubAPIError as exc:
        status = exc.status_code if exc.status_code in (401, 403, 404) else 502
        raise HTTPException(status_code=status, detail=str(exc))

    # Truncate very large raw diffs to keep the response manageable for the MVP.
    max_diff_chars = 200_000
    raw_diff_out = raw_diff[:max_diff_chars] if raw_diff else None

    return AnalyzeResponse(
        meta=meta,
        diff_summary=summarize_diff(files),
        files=files,
        raw_diff=raw_diff_out,
    )


@router.post("/context", response_model=AnalysisContext, responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}})
def context(req: AnalyzeRequest) -> AnalysisContext:
    """Phase 2: build structured repository context from a PR.

    Reuses the Phase 1 GitHub integration to fetch raw PR data, then runs the
    context builder (classification, diff parsing, retrieval, imports, tests).
    """
    try:
        parse_pr_url(req.pr_url)
    except InvalidPRURL as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    settings = get_settings()
    client = GitHubClient(settings=settings)

    try:
        meta, files, raw_diff = client.fetch_all(req.pr_url)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub auth error: {exc}")
    except GitHubAPIError as exc:
        status = exc.status_code if exc.status_code in (401, 403, 404) else 502
        raise HTTPException(status_code=status, detail=str(exc))

    builder = ContextBuilder(client=client, settings=settings)
    return builder.build(meta, files, raw_diff)


@router.post("/analyze-signals", response_model=AnalysisResult, responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}})
def analyze_signals(req: AnalyzeRequest) -> AnalysisResult:
    """Phase 3: run deterministic analysis over a PR and return structured signals.

    Reuses Phase 1 (GitHub fetch) + Phase 2 (context builder), then runs the
    analysis engine (change, critical, security, quality, tests).
    No AI, no risk score, no review priority (Phase 4).
    """
    try:
        parse_pr_url(req.pr_url)
    except InvalidPRURL as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    settings = get_settings()
    client = GitHubClient(settings=settings)

    try:
        meta, files, raw_diff = client.fetch_all(req.pr_url)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub auth error: {exc}")
    except GitHubAPIError as exc:
        status = exc.status_code if exc.status_code in (401, 403, 404) else 502
        raise HTTPException(status_code=status, detail=str(exc))

    builder = ContextBuilder(client=client, settings=settings)
    ctx = builder.build(meta, files, raw_diff)

    engine = AnalysisEngine(settings=settings)
    return engine.analyze(ctx)


@router.post("/analyze-full", response_model=Phase4Result, responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}})
def analyze_full(req: AnalyzeRequest) -> Phase4Result:
    """Phase 4: full pipeline — analysis + AI insights + risk + review priority.

    Reuses Phase 1 (GitHub fetch) + Phase 2 (context builder) + Phase 3
    (deterministic analysis), then adds AI insights, risk scoring, and
    review priority. Uses the mock AI provider if no OpenAI key is configured.
    """
    try:
        parse_pr_url(req.pr_url)
    except InvalidPRURL as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    settings = get_settings()
    client = GitHubClient(settings=settings)

    try:
        meta, files, raw_diff = client.fetch_all(req.pr_url)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub auth error: {exc}")
    except GitHubAPIError as exc:
        status = exc.status_code if exc.status_code in (401, 403, 404) else 502
        raise HTTPException(status_code=status, detail=str(exc))

    builder = ContextBuilder(client=client, settings=settings)
    ctx = builder.build(meta, files, raw_diff)

    engine = Phase4Engine(settings=settings)
    return engine.analyze(ctx)


@router.post("/impact-map", response_model=ImpactMap, responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}})
def impact_map(req: AnalyzeRequest) -> ImpactMap:
    """Phase 5: build a visual Impact Map from the full analysis pipeline.

    Reuses Phase 1-4 (GitHub fetch, context, analysis, AI, risk, priority),
    then builds a graph of changed files, connected dependencies, test files,
    and functional areas with risk/severity visualization data.
    """
    try:
        parse_pr_url(req.pr_url)
    except InvalidPRURL as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    settings = get_settings()
    client = GitHubClient(settings=settings)

    try:
        meta, files, raw_diff = client.fetch_all(req.pr_url)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub auth error: {exc}")
    except GitHubAPIError as exc:
        status = exc.status_code if exc.status_code in (401, 403, 404) else 502
        raise HTTPException(status_code=status, detail=str(exc))

    builder = ContextBuilder(client=client, settings=settings)
    ctx = builder.build(meta, files, raw_diff)

    engine = Phase4Engine(settings=settings)
    result = engine.analyze(ctx)

    map_builder = ImpactMapBuilder()
    return map_builder.build(ctx, result)
