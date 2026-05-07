from __future__ import annotations

from funding_agent.models import FundingCall
from funding_agent.classifiers.fit_analyzer import analyze_fit


def score_call(call: FundingCall, config: dict) -> float:
    """
    Scoring robusto basato su analisi multidimensionale.

    Il punteggio finale non deriva più da semplici keyword,
    ma da:
    - technical_fit
    - business_fit
    - applicant_fit
    - feasibility
    - strategic_value
    - timing_score
    """
    fit = analyze_fit(call, config)
    return float(fit["final_score"])