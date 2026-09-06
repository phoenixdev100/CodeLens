"""Unit tests for the Impact Map builder (impact_map/builder.py)."""
from __future__ import annotations

from config import Settings
from impact_map.builder import ImpactMapBuilder
from models.analysis import (
    AnalysisResult,
    ChangeSignal,
    CriticalArea,
    CriticalAreaSignal,
    Finding,
    FunctionalArea,
    ScopeDriftSignal,
    SecuritySignal,
    QualitySignal,
    TestCoverageIndication,
    TestSignal,
)
from models.ai import AIInsights
from models.context import (
    AnalysisContext,
    DependencyGraph,
    FileCategory,
    ImportEdge,
    Language,
    NormalizedFile,
    TestMapping,
)
from models.impact_map import ImpactEdge, ImpactNode, NodeType, RiskColor
from models.phase4 import Phase4Result
from models.priority import PriorityItem, ReviewPriority
from models.risk import RiskResult, RiskWeights
from models.schemas import PRMeta
from tests.helpers import make_meta


def _settings() -> Settings:
    return Settings(
        github_app_id="", github_private_key_path="", github_installation_id="",
        github_token="", cors_origins="http://localhost:3000",
        max_files_per_pr=300, max_files_to_retrieve=25, max_file_content_chars=50000,
        large_pr_file_count=20, xlarge_pr_file_count=50,
        large_pr_line_count=500, large_function_line_count=80, high_nesting_threshold=4,
        openai_api_key="", openai_model="gpt-4o-mini",
        ai_provider="mock", ai_max_context_findings=30,
        risk_weight_change=15, risk_weight_scope=15, risk_weight_critical=25,
        risk_weight_security=20, risk_weight_quality=10, risk_weight_tests=15,
    )


def _make_file(
    filename: str,
    is_source: bool = True,
    is_test: bool = False,
    category: FileCategory = FileCategory.SOURCE,
    additions: int = 10,
    deletions: int = 2,
) -> NormalizedFile:
    return NormalizedFile(
        filename=filename,
        status="modified",
        category=category,
        language=Language.TYPESCRIPT,
        is_source=is_source,
        is_test=is_test,
        additions=additions,
        deletions=deletions,
        changes=additions + deletions,
    )


def _make_phase4_result(
    files: list[NormalizedFile],
    dep_graph: DependencyGraph | None = None,
    test_mappings: list[TestMapping] | None = None,
    findings: list[Finding] | None = None,
    critical_areas: list[CriticalArea] | None = None,
    functional_areas: list[FunctionalArea] | None = None,
    priority_items: list[PriorityItem] | None = None,
) -> tuple[AnalysisContext, Phase4Result]:
    ctx = AnalysisContext(
        meta=make_meta(),
        head_ref="feature/x",
        normalized_files=files,
        parsed_diffs=[],
        dependency_graph=dep_graph or DependencyGraph(),
        test_mappings=test_mappings or [],
        retrieved_contents={},
        stats={},
    )

    analysis = AnalysisResult(
        meta=ctx.meta,
        change=ChangeSignal(
            files_changed=len(files),
            lines_added=sum(f.additions for f in files),
            lines_removed=sum(f.deletions for f in files),
            total_changes=sum(f.changes for f in files),
            size_class="small",
            functional_areas=functional_areas or [],
            scope_drift=ScopeDriftSignal(),
            findings=[],
        ),
        critical=CriticalAreaSignal(areas=critical_areas or []),
        security=SecuritySignal(findings=[]),
        quality=QualitySignal(findings=[]),
        tests=TestSignal(coverage=TestCoverageIndication()),
        all_findings=findings or [],
        stats={},
    )

    ai_insights = AIInsights(
        pr_intent="test",
        functional_area_interpretation="test",
        risk_reasoning="test",
        provider="mock",
    )

    risk = RiskResult(
        total_score=30,
        level="LOW",
        dimension_scores=[],
        top_contributors=[],
        weights=RiskWeights(),
    )

    priority = ReviewPriority(items=priority_items or [])

    result = Phase4Result(
        meta=ctx.meta,
        analysis=analysis,
        ai_insights=ai_insights,
        risk=risk,
        priority=priority,
        stats={},
    )

    return ctx, result


# --- Node creation tests ---

def test_empty_pr_no_nodes() -> None:
    ctx, result = _make_phase4_result([])
    imap = ImpactMapBuilder().build(ctx, result)
    assert len(imap.nodes) == 0
    assert len(imap.edges) == 0
    assert imap.stats["total_nodes"] == 0


def test_changed_source_files_become_nodes() -> None:
    files = [_make_file("src/payment/service.ts"), _make_file("src/auth/session.ts")]
    ctx, result = _make_phase4_result(files)
    imap = ImpactMapBuilder().build(ctx, result)
    node_ids = {n.id for n in imap.nodes}
    assert "src/payment/service.ts" in node_ids
    assert "src/auth/session.ts" in node_ids
    # Both should be marked as changed
    for n in imap.nodes:
        if n.id in ("src/payment/service.ts", "src/auth/session.ts"):
            assert n.changed is True
            assert n.type == NodeType.SOURCE


def test_test_files_become_test_nodes() -> None:
    files = [
        _make_file("src/payment/service.ts"),
        _make_file("src/payment/service.test.ts", is_source=False, is_test=True, category=FileCategory.TEST),
    ]
    ctx, result = _make_phase4_result(files)
    imap = ImpactMapBuilder().build(ctx, result)
    test_node = next(n for n in imap.nodes if n.id == "src/payment/service.test.ts")
    assert test_node.type == NodeType.TEST


def test_config_files_become_config_nodes() -> None:
    files = [_make_file("package.json", is_source=False, category=FileCategory.CONFIG)]
    ctx, result = _make_phase4_result(files)
    imap = ImpactMapBuilder().build(ctx, result)
    config_node = next(n for n in imap.nodes if n.id == "package.json")
    assert config_node.type == NodeType.CONFIG


def test_functional_area_nodes_created() -> None:
    files = [_make_file("src/payment/service.ts")]
    areas = [FunctionalArea(name="payments", files=["src/payment/service.ts"], detected_by="path")]
    ctx, result = _make_phase4_result(files, functional_areas=areas)
    imap = ImpactMapBuilder().build(ctx, result)
    area_node = next((n for n in imap.nodes if n.type == NodeType.AREA), None)
    assert area_node is not None
    assert area_node.id == "area:payments"
    assert area_node.label == "payments"


# --- Edge creation tests ---

def test_import_edges_from_dependency_graph() -> None:
    files = [_make_file("src/payment/service.ts"), _make_file("src/utils/helpers.ts")]
    dep_graph = DependencyGraph(
        nodes=["src/payment/service.ts", "src/utils/helpers.ts"],
        edges=[ImportEdge(
            source_file="src/payment/service.ts",
            raw_specifier="./utils/helpers",
            resolved_path="src/utils/helpers.ts",
            is_external=False,
            import_kind="import",
        )],
    )
    ctx, result = _make_phase4_result(files, dep_graph=dep_graph)
    imap = ImpactMapBuilder().build(ctx, result)
    import_edges = [e for e in imap.edges if e.kind == "import"]
    assert len(import_edges) == 1
    assert import_edges[0].source == "src/payment/service.ts"
    assert import_edges[0].target == "src/utils/helpers.ts"


def test_test_edges_from_test_mappings() -> None:
    files = [
        _make_file("src/payment/service.ts"),
        _make_file("src/payment/service.test.ts", is_source=False, is_test=True, category=FileCategory.TEST),
    ]
    test_mappings = [TestMapping(
        source_file="src/payment/service.ts",
        related_tests=["src/payment/service.test.ts"],
        has_tests=True,
    )]
    ctx, result = _make_phase4_result(files, test_mappings=test_mappings)
    imap = ImpactMapBuilder().build(ctx, result)
    test_edges = [e for e in imap.edges if e.kind == "test"]
    assert len(test_edges) == 1
    assert test_edges[0].source == "src/payment/service.ts"
    assert test_edges[0].target == "src/payment/service.test.ts"


def test_area_edges_connect_area_to_files() -> None:
    files = [_make_file("src/payment/service.ts")]
    areas = [FunctionalArea(name="payments", files=["src/payment/service.ts"], detected_by="path")]
    ctx, result = _make_phase4_result(files, functional_areas=areas)
    imap = ImpactMapBuilder().build(ctx, result)
    area_edges = [e for e in imap.edges if e.kind == "area"]
    assert len(area_edges) == 1
    assert area_edges[0].source == "area:payments"
    assert area_edges[0].target == "src/payment/service.ts"


def test_external_import_edges_excluded() -> None:
    files = [_make_file("src/payment/service.ts")]
    dep_graph = DependencyGraph(
        nodes=["src/payment/service.ts"],
        edges=[ImportEdge(
            source_file="src/payment/service.ts",
            raw_specifier="react",
            resolved_path=None,
            is_external=True,
            import_kind="import",
        )],
    )
    ctx, result = _make_phase4_result(files, dep_graph=dep_graph)
    imap = ImpactMapBuilder().build(ctx, result)
    # External packages should not create edges
    assert len(imap.edges) == 0


# --- Connected file (blast radius) tests ---

def test_connected_files_included_via_dependency_graph() -> None:
    """A file imported by a changed file should appear in the map even if not changed."""
    files = [_make_file("src/payment/service.ts")]  # only service.ts is changed
    dep_graph = DependencyGraph(
        nodes=["src/payment/service.ts", "src/utils/helpers.ts"],
        edges=[ImportEdge(
            source_file="src/payment/service.ts",
            raw_specifier="./utils/helpers",
            resolved_path="src/utils/helpers.ts",
            is_external=False,
            import_kind="import",
        )],
    )
    ctx, result = _make_phase4_result(files, dep_graph=dep_graph)
    imap = ImpactMapBuilder().build(ctx, result)
    # helpers.ts should appear as a connected (unchanged) node
    helper_node = next((n for n in imap.nodes if n.id == "src/utils/helpers.ts"), None)
    assert helper_node is not None
    assert helper_node.changed is False


def test_reverse_dependency_includes_importer() -> None:
    """A file that imports a changed file should also appear."""
    files = [_make_file("src/utils/helpers.ts")]  # helpers.ts is changed
    dep_graph = DependencyGraph(
        nodes=["src/payment/service.ts", "src/utils/helpers.ts"],
        edges=[ImportEdge(
            source_file="src/payment/service.ts",
            raw_specifier="./utils/helpers",
            resolved_path="src/utils/helpers.ts",
            is_external=False,
            import_kind="import",
        )],
    )
    ctx, result = _make_phase4_result(files, dep_graph=dep_graph)
    imap = ImpactMapBuilder().build(ctx, result)
    # service.ts (the importer) should appear as connected
    svc_node = next((n for n in imap.nodes if n.id == "src/payment/service.ts"), None)
    assert svc_node is not None
    assert svc_node.changed is False


# --- Risk/severity mapping tests ---

def test_risk_color_red_for_high_severity() -> None:
    files = [_make_file("src/auth/config.ts")]
    findings = [Finding(
        id="sec-1", category="security", severity="high",
        title="Hardcoded password", file="src/auth/config.ts",
    )]
    ctx, result = _make_phase4_result(files, findings=findings)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/auth/config.ts")
    assert node.risk_color == RiskColor.RED
    assert node.severity.value == "high"
    assert node.finding_count == 1


def test_risk_color_orange_for_medium_severity() -> None:
    files = [_make_file("src/payment/service.ts")]
    findings = [Finding(
        id="qual-1", category="quality", severity="medium",
        title="Large function", file="src/payment/service.ts",
    )]
    ctx, result = _make_phase4_result(files, findings=findings)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/payment/service.ts")
    assert node.risk_color == RiskColor.ORANGE


def test_risk_color_yellow_for_low_severity() -> None:
    files = [_make_file("src/utils/helpers.ts")]
    findings = [Finding(
        id="qual-2", category="quality", severity="low",
        title="High nesting", file="src/utils/helpers.ts",
    )]
    ctx, result = _make_phase4_result(files, findings=findings)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/utils/helpers.ts")
    assert node.risk_color == RiskColor.YELLOW


def test_risk_color_green_for_clean_changed_file() -> None:
    files = [_make_file("src/utils/helpers.ts")]
    ctx, result = _make_phase4_result(files)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/utils/helpers.ts")
    assert node.risk_color == RiskColor.GREEN


def test_risk_color_from_priority_score() -> None:
    files = [_make_file("src/payment/service.ts")]
    priority_items = [PriorityItem(
        rank=1, file="src/payment/service.ts", score=85,
        severity="high", reason="critical area",
    )]
    ctx, result = _make_phase4_result(files, priority_items=priority_items)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/payment/service.ts")
    assert node.risk_color == RiskColor.RED
    assert node.priority_score == 85


def test_critical_area_changed_file_red_with_high_severity() -> None:
    """Critical area with default HIGH severity -> RED, even without findings."""
    files = [_make_file("src/payment/service.ts")]
    critical_areas = [CriticalArea(name="payments", kind="payments", files=["src/payment/service.ts"])]
    ctx, result = _make_phase4_result(files, critical_areas=critical_areas)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/payment/service.ts")
    assert node.is_critical_area is True
    # CriticalArea defaults to HIGH severity -> RED
    assert node.risk_color == RiskColor.RED
    assert node.severity.value == "high"


# --- Finding association tests ---

def test_finding_ids_associated_with_nodes() -> None:
    files = [_make_file("src/auth/config.ts")]
    findings = [
        Finding(id="sec-1", category="security", severity="high", title="A", file="src/auth/config.ts"),
        Finding(id="sec-2", category="security", severity="medium", title="B", file="src/auth/config.ts"),
    ]
    ctx, result = _make_phase4_result(files, findings=findings)
    imap = ImpactMapBuilder().build(ctx, result)
    node = next(n for n in imap.nodes if n.id == "src/auth/config.ts")
    assert node.finding_count == 2
    assert "sec-1" in node.finding_ids
    assert "sec-2" in node.finding_ids


def test_findings_not_associated_with_wrong_file() -> None:
    files = [_make_file("src/auth/config.ts"), _make_file("src/utils/helpers.ts")]
    findings = [Finding(id="sec-1", category="security", severity="high", title="A", file="src/auth/config.ts")]
    ctx, result = _make_phase4_result(files, findings=findings)
    imap = ImpactMapBuilder().build(ctx, result)
    helper_node = next(n for n in imap.nodes if n.id == "src/utils/helpers.ts")
    assert helper_node.finding_count == 0
    assert len(helper_node.finding_ids) == 0


# --- Determinism tests ---

def test_graph_output_deterministic() -> None:
    files = [_make_file("src/payment/service.ts"), _make_file("src/auth/session.ts")]
    dep_graph = DependencyGraph(
        nodes=["src/payment/service.ts", "src/auth/session.ts"],
        edges=[ImportEdge(
            source_file="src/payment/service.ts",
            raw_specifier="./auth/session",
            resolved_path="src/auth/session.ts",
            is_external=False,
            import_kind="import",
        )],
    )
    ctx, result = _make_phase4_result(files, dep_graph=dep_graph)
    builder = ImpactMapBuilder()
    m1 = builder.build(ctx, result)
    m2 = builder.build(ctx, result)
    assert [n.id for n in m1.nodes] == [n.id for n in m2.nodes]
    assert [(e.source, e.target, e.kind) for e in m1.edges] == [(e.source, e.target, e.kind) for e in m2.edges]


def test_stats_populated_correctly() -> None:
    files = [
        _make_file("src/payment/service.ts"),
        _make_file("src/payment/service.test.ts", is_source=False, is_test=True, category=FileCategory.TEST),
    ]
    areas = [FunctionalArea(name="payments", files=["src/payment/service.ts"], detected_by="path")]
    ctx, result = _make_phase4_result(files, functional_areas=areas)
    imap = ImpactMapBuilder().build(ctx, result)
    assert imap.stats["total_nodes"] == len(imap.nodes)
    assert imap.stats["total_edges"] == len(imap.edges)
    assert imap.stats["changed_files"] == 2
    assert imap.stats["area_nodes"] == 1
    assert imap.stats["green_nodes"] >= 1


def test_legend_present() -> None:
    ctx, result = _make_phase4_result([])
    imap = ImpactMapBuilder().build(ctx, result)
    assert "red" in imap.legend
    assert "orange" in imap.legend
    assert "yellow" in imap.legend
    assert "green" in imap.legend


def test_small_pr_with_single_file() -> None:
    files = [_make_file("src/utils/helpers.ts", additions=3, deletions=1)]
    ctx, result = _make_phase4_result(files)
    imap = ImpactMapBuilder().build(ctx, result)
    assert len(imap.nodes) == 1
    assert imap.nodes[0].changed is True
    assert imap.nodes[0].type == NodeType.SOURCE
    assert imap.nodes[0].additions == 3
    assert imap.nodes[0].deletions == 1
