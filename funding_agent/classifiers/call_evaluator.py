from __future__ import annotations

from funding_agent.models import FundingCall
from funding_agent.classifiers.fit_analyzer import analyze_fit
from funding_agent.classifiers.strategic_classifier import classify_call_strategy
from funding_agent.classifiers.explainer import build_why_relevant


def evaluate_call(call: FundingCall, config: dict) -> dict:
    """
    Valutazione completa di una FundingCall.

    Centralizza:
    - score multidimensionale
    - classificazione strategica
    - motivazioni leggibili

    In questo modo main.py, email e dashboard possono usare una sola funzione.
    """

    fit = analyze_fit(call, config)
    score = float(fit["final_score"])

    strategy = classify_call_strategy(call, score)
    why_relevant = build_why_relevant(call)

    return {
        "score": score,
        "fit": fit,
        "opportunity_type": fit.get("opportunity_type"),
        "strategy": strategy.get("strategy"),
        "decision": strategy.get("decision"),
        "priority": strategy.get("priority"),
        "timing": strategy.get("timing"),
        "next_action": strategy.get("next_action"),
        "nex_core_matches": strategy.get("nex_core_matches"),
        "why_relevant": why_relevant,
    }