"""Impact Map Builder: constructs a visual graph from Phase 2-4 data.

Reuses:
  - Phase 2 DependencyGraph (import edges) — does NOT create a second dependency system
  - Phase 2 TestMappings (source-to-test relationships)
  - Phase 3 AnalysisResult (findings, functional areas, critical areas)
  - Phase 4 RiskResult + ReviewPriority (risk colors, priority scores)

The graph is limited to PR-relevant context:
  - Changed source files
  - Connected source files (via dependency graph, 1-hop neighbors)
  - Relevant test files (from test mappings)
  - Functional area grouping nodes (when areas are detected)

No full repository visualization. No invented relationships.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Set, Tuple

from models.analysis import AnalysisResult, Finding, Severity
from models.context import AnalysisContext, NormalizedFile
from models.impact_map import ImpactEdge, ImpactMap, ImpactNode, NodeType, RiskColor
from models.phase4 import Phase4Result
from models.priority import ReviewPriority
from models.risk import RiskResult


# Severity -> risk color mapping
_SEVERITY_COLOR = {
    Severity.CRITICAL: RiskColor.RED,
    Severity.HIGH: RiskColor.RED,
    Severity.MEDIUM: RiskColor.ORANGE,
    Severity.LOW: RiskColor.YELLOW,
    Severity.INFO: RiskColor.GREEN,
}


class ImpactMapBuilder:
    """Builds an ImpactMap from Phase 2 context + Phase 4 result."""

    def build(
        self,
        ctx: AnalysisContext,
        result: Phase4Result,
    ) -> ImpactMap:
        analysis = result.analysis
        risk = result.risk
        priority = result.priority

        # Index findings by file
        findings_by_file: Dict[str, List[Finding]] = {}
        for f in analysis.all_findings:
            if f.file:
                findings_by_file.setdefault(f.file, [])
                findings_by_file[f.file].append(f)

        # Index priority items by file
        priority_by_file: Dict[str, int] = {}
        for item in priority.items:
            priority_by_file[item.file] = item.score

        # Index critical area files
        critical_files: Set[str] = set()
        for area in analysis.critical.areas:
            for fn in area.files:
                critical_files.add(fn)

        # Index functional areas by file
        area_by_file: Dict[str, str] = {}
        for fa in analysis.change.functional_areas:
            for fn in fa.files:
                area_by_file[fn] = fa.name

        # Changed files from context
        changed_files = {f.filename for f in ctx.normalized_files}
        normalized_by_name = {f.filename: f for f in ctx.normalized_files}

        # Collect candidate file nodes
        candidate_files: Set[str] = set(changed_files)

        # Add 1-hop dependency neighbors (files that changed files import, or that import them)
        dep_graph = ctx.dependency_graph
        for edge in dep_graph.edges:
            if edge.is_external or not edge.resolved_path:
                continue
            src = edge.source_file
            tgt = edge.resolved_path
            if src in changed_files:
                candidate_files.add(tgt)
            if tgt in changed_files:
                candidate_files.add(src)

        # Add test files from test mappings
        test_files: Set[str] = set()
        for tm in ctx.test_mappings:
            for t in tm.related_tests:
                test_files.add(t)
                candidate_files.add(t)

        # Build nodes
        nodes: List[ImpactNode] = []
        node_ids: Set[str] = set()

        for fn in sorted(candidate_files):
            node = self._build_file_node(
                fn,
                normalized_by_name,
                findings_by_file,
                priority_by_file,
                critical_files,
                area_by_file,
                changed_files,
            )
            nodes.append(node)
            node_ids.add(node.id)

        # Build functional area nodes
        area_nodes: Dict[str, ImpactNode] = {}
        for fa in analysis.change.functional_areas:
            area_id = f"area:{fa.name}"
            if area_id in node_ids:
                continue
            node = ImpactNode(
                id=area_id,
                type=NodeType.AREA,
                label=fa.name,
                functional_area=fa.name,
                changed=False,
                risk_color=RiskColor.GREEN,
            )
            area_nodes[fa.name] = node
            nodes.append(node)
            node_ids.add(area_id)

        # Build edges
        edges: List[ImpactEdge] = []
        seen_edges: Set[Tuple[str, str, str]] = set()

        # Import/dependency edges
        for edge in dep_graph.edges:
            if edge.is_external or not edge.resolved_path:
                continue
            src = edge.source_file
            tgt = edge.resolved_path
            if src in node_ids and tgt in node_ids:
                key = (src, tgt, "import")
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append(ImpactEdge(
                        id=f"e:{src}->{tgt}:import",
                        source=src,
                        target=tgt,
                        kind="import",
                    ))

        # Test relationship edges (source -> test)
        for tm in ctx.test_mappings:
            if tm.source_file in node_ids:
                for t in tm.related_tests:
                    if t in node_ids:
                        key = (tm.source_file, t, "test")
                        if key not in seen_edges:
                            seen_edges.add(key)
                            edges.append(ImpactEdge(
                                id=f"e:{tm.source_file}->{t}:test",
                                source=tm.source_file,
                                target=t,
                                kind="test",
                            ))

        # Functional area edges (area -> file)
        for fa in analysis.change.functional_areas:
            area_id = f"area:{fa.name}"
            for fn in fa.files:
                if fn in node_ids and area_id in node_ids:
                    key = (area_id, fn, "area")
                    if key not in seen_edges:
                        seen_edges.add(key)
                        edges.append(ImpactEdge(
                            id=f"e:{area_id}->{fn}:area",
                            source=area_id,
                            target=fn,
                            kind="area",
                        ))

        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "changed_files": sum(1 for n in nodes if n.changed),
            "file_nodes": sum(1 for n in nodes if n.type in (NodeType.SOURCE, NodeType.TEST, NodeType.CONFIG)),
            "area_nodes": sum(1 for n in nodes if n.type == NodeType.AREA),
            "red_nodes": sum(1 for n in nodes if n.risk_color == RiskColor.RED),
            "orange_nodes": sum(1 for n in nodes if n.risk_color == RiskColor.ORANGE),
            "yellow_nodes": sum(1 for n in nodes if n.risk_color == RiskColor.YELLOW),
            "green_nodes": sum(1 for n in nodes if n.risk_color == RiskColor.GREEN),
        }

        return ImpactMap(nodes=nodes, edges=edges, stats=stats)

    def _build_file_node(
        self,
        filename: str,
        normalized_by_name: Dict[str, NormalizedFile],
        findings_by_file: Dict[str, List[Finding]],
        priority_by_file: Dict[str, int],
        critical_files: Set[str],
        area_by_file: Dict[str, str],
        changed_files: Set[str],
    ) -> ImpactNode:
        nf = normalized_by_name.get(filename)
        changed = filename in changed_files
        findings = findings_by_file.get(filename, [])
        finding_ids = [f.id for f in findings]
        finding_count = len(findings)
        is_critical = filename in critical_files
        area = area_by_file.get(filename)
        priority_score = priority_by_file.get(filename)

        # Determine node type
        if nf:
            if nf.is_test:
                node_type = NodeType.TEST
            elif nf.category.value == "config":
                node_type = NodeType.CONFIG
            else:
                node_type = NodeType.SOURCE
        else:
            # Connected file not in the PR — infer from path
            if "test" in filename.lower() or ".test." in filename or ".spec." in filename:
                node_type = NodeType.TEST
            else:
                node_type = NodeType.SOURCE

        # Determine severity (max of findings)
        severity: Optional[Severity] = None
        if findings:
            severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
            for sev in severity_order:
                if any(f.severity == sev for f in findings):
                    severity = sev
                    break
        elif is_critical:
            severity = Severity.HIGH

        # Determine risk color
        risk_color = self._compute_risk_color(
            severity, is_critical, finding_count, changed, priority_score
        )

        # Short label
        label = os.path.basename(filename)
        if node_type == NodeType.AREA:
            label = filename

        return ImpactNode(
            id=filename,
            type=node_type,
            label=label,
            file_path=filename,
            functional_area=area,
            changed=changed,
            risk_color=risk_color,
            severity=severity,
            finding_count=finding_count,
            finding_ids=finding_ids,
            priority_score=priority_score,
            is_critical_area=is_critical,
            additions=nf.additions if nf else 0,
            deletions=nf.deletions if nf else 0,
        )

    def _compute_risk_color(
        self,
        severity: Optional[Severity],
        is_critical: bool,
        finding_count: int,
        changed: bool,
        priority_score: Optional[int],
    ) -> RiskColor:
        # Priority score is the strongest signal if available
        if priority_score is not None:
            if priority_score >= 70:
                return RiskColor.RED
            if priority_score >= 40:
                return RiskColor.ORANGE
            if priority_score >= 20:
                return RiskColor.YELLOW
            return RiskColor.GREEN

        # Fall back to severity
        if severity:
            return _SEVERITY_COLOR.get(severity, RiskColor.GREEN)

        # Critical area but no findings
        if is_critical and changed:
            return RiskColor.ORANGE

        if is_critical:
            return RiskColor.YELLOW

        if changed and finding_count > 0:
            return RiskColor.YELLOW

        if changed:
            return RiskColor.GREEN

        # Unchanged connected file
        return RiskColor.GREEN
