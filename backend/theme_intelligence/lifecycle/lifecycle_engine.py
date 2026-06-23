from __future__ import annotations

import json
from typing import Any

from theme_intelligence.discovery.discovery_models import THEME_ZH, theme_id
from theme_intelligence.lifecycle.lifecycle_explainer import LifecycleExplainer
from theme_intelligence.lifecycle.lifecycle_history import parse_score_history
from theme_intelligence.lifecycle.lifecycle_models import LifecycleInput, LifecycleResult
from theme_intelligence.lifecycle.lifecycle_rules import classify_stage, compute_expected_next_stage, compute_lifecycle_confidence, time_window_for_stage
from theme_intelligence.models import clamp_score
from theme_intelligence.storage.theme_repository import ThemeRepository


class LifecycleEngine:
    def __init__(self, repository: ThemeRepository | None = None, explainer: LifecycleExplainer | None = None) -> None:
        self.repository = repository or ThemeRepository()
        self.explainer = explainer or LifecycleExplainer()

    def classify(self, data: LifecycleInput) -> LifecycleResult:
        decision = classify_stage(data)
        confidence = compute_lifecycle_confidence(data)
        next_stage = compute_expected_next_stage(decision.stage, decision.deteriorating)
        explanation = self.explainer.explain(data, decision)
        return LifecycleResult(
            theme_name=data.theme_name,
            lifecycle_stage=decision.stage,
            lifecycle_confidence=confidence,
            expected_next_stage=next_stage,
            time_window=time_window_for_stage(decision.stage),
            final_ai_score=clamp_score(data.final_ai_score),
            emerging_score=clamp_score(data.emerging_score),
            catalyst_score=clamp_score(data.catalyst_score),
            entity_strength_score=clamp_score(data.entity_strength_score),
            crowding_proxy=clamp_score(data.crowding_proxy),
            explanation=explanation,
            history=data.history[-120:],
        )

    def lifecycle_summary(self, limit: int = 50) -> dict[str, Any]:
        self.repository.initialize()
        discovery_rows = self.repository.get_discovery_scores(limit)
        bottlenecks = self.repository.get_bottlenecks()
        bottleneck_map: dict[str, list[dict[str, Any]]] = {}
        for bottleneck in bottlenecks:
            bottleneck_map.setdefault(bottleneck.theme_name, []).append(bottleneck.to_api())
        for row in discovery_rows:
            rows = sorted(
                bottleneck_map.get(row["name"], []),
                key=lambda item: float(item.get("bottleneck_strength", 0.0)),
                reverse=True,
            )
            row["key_bottlenecks"] = rows[:5]
        rows = [self._row_from_discovery(row) for row in discovery_rows]
        return {"themes": rows}

    def lifecycle_detail(self, theme_id_value: str) -> dict[str, Any]:
        rows = self.lifecycle_summary(limit=100)["themes"]
        normalized = theme_id_value.strip().lower()
        for row in rows:
            if row["theme_id"] == normalized or row["name"].strip().lower() == normalized.replace("_", " "):
                return row
        return {
            "theme_id": normalized,
            "name": normalized.replace("_", " ").title(),
            "name_zh": normalized.replace("_", " ").title(),
            "lifecycle_stage": None,
            "lifecycle_confidence": None,
            "expected_next_stage": None,
            "time_window": None,
            "final_ai_score": None,
            "emerging_score": None,
            "catalyst_score": None,
            "entity_strength_score": None,
            "crowding_proxy": None,
            "stage_reason": None,
            "positive_signals": [],
            "negative_signals": [],
            "stage_risks": [],
            "next_stage_triggers": [],
            "top_catalysts": [],
            "future_catalysts": [],
            "key_blockers": [],
            "primary_bottleneck": None,
            "bottleneck_risks": [],
            "top_beneficiaries": [],
            "history": [],
        }

    def _row_from_discovery(self, row: dict[str, Any]) -> dict[str, Any]:
        history = self._history_from_row(row)
        data = LifecycleInput(
            theme_name=row["name"],
            discovery_score=row.get("discovery_score", 0.0),
            emerging_score=row.get("emerging_score", 0.0),
            catalyst_score=row.get("catalyst_score", 0.0),
            entity_strength_score=row.get("entity_strength_score", 0.0),
            confidence_score=row.get("confidence_score", 0.0),
            crowding_proxy=row.get("crowding_proxy", 0.0),
            final_ai_score=row.get("ai_score", 0.0),
            key_catalysts=row.get("key_catalysts", []),
            key_bottlenecks=row.get("key_bottlenecks", []),
            top_beneficiaries=row.get("top_beneficiaries", []),
            beneficiaries=row.get("beneficiaries", []),
            source_count=len({item.get("source") for item in row.get("key_catalysts", []) if item.get("source")}),
            history=history,
        )
        result = self.classify(data)
        payload = lifecycle_result_to_api(result)
        if row.get("lifecycle_stage"):
            payload["lifecycle_stage"] = row["lifecycle_stage"]
        if row.get("lifecycle_confidence") is not None:
            payload["lifecycle_confidence"] = row["lifecycle_confidence"]
        if row.get("expected_next_stage"):
            payload["expected_next_stage"] = row["expected_next_stage"]
        if row.get("time_window"):
            payload["time_window"] = row["time_window"]
        if row.get("lifecycle_reason"):
            payload["stage_reason"] = row["lifecycle_reason"]
        return payload

    @staticmethod
    def _history_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
        raw = row.get("history") or row.get("score_history_json")
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, str):
            return parse_score_history(raw)
        return []


def lifecycle_result_to_api(result: LifecycleResult) -> dict[str, Any]:
    explanation = result.explanation
    return {
        "theme_id": theme_id(result.theme_name),
        "name": result.theme_name,
        "name_zh": THEME_ZH.get(result.theme_name, result.theme_name),
        "lifecycle_stage": result.lifecycle_stage,
        "lifecycle_confidence": result.lifecycle_confidence,
        "expected_next_stage": result.expected_next_stage,
        "time_window": result.time_window,
        "final_ai_score": result.final_ai_score,
        "emerging_score": result.emerging_score,
        "catalyst_score": result.catalyst_score,
        "entity_strength_score": result.entity_strength_score,
        "crowding_proxy": result.crowding_proxy,
        "stage_reason": explanation.stage_reason,
        "positive_signals": explanation.positive_signals,
        "negative_signals": explanation.negative_signals,
        "stage_risks": explanation.stage_risks,
        "next_stage_triggers": explanation.next_stage_triggers,
        "top_catalysts": explanation.top_catalysts,
        "future_catalysts": explanation.future_catalysts,
        "key_blockers": explanation.key_blockers,
        "primary_bottleneck": explanation.primary_bottleneck,
        "bottleneck_risks": explanation.bottleneck_risks,
        "top_beneficiaries": explanation.top_beneficiaries,
        "history": result.history,
    }


def get_theme_lifecycle() -> dict[str, Any]:
    return LifecycleEngine().lifecycle_summary()


def get_theme_lifecycle_detail(theme_id: str) -> dict[str, Any]:
    return LifecycleEngine().lifecycle_detail(theme_id)
