from datetime import datetime, timedelta
from funding_agent.models import FundingCall


def classify_call_strategy(call: FundingCall, score: float) -> dict:
    text = " ".join(
        [
            call.title or "",
            call.summary or "",
            call.program or "",
            call.raw_text or "",
        ]
    ).lower()

    strategy = "LOW_PRIORITY"
    priority = "LOW"
    timing = "UNKNOWN"

    # =========================
    # TIMING
    # =========================
    if call.deadline_date == "sportello_aperto":
        timing = "always_open"
    elif call.deadline_date:
        try:
            deadline = datetime.strptime(call.deadline_date, "%d %B %Y")
            today = datetime.today()

            if deadline < today:
                timing = "closed"
            elif deadline <= today + timedelta(days=90):
                timing = "urgent"
            elif deadline <= today + timedelta(days=180):
                timing = "medium_term"
            else:
                timing = "long_term"

        except Exception:
            timing = "unknown"

    # =========================
    # STRATEGY CLASSIFICATION
    # =========================

    # 🚀 QUICK WIN (Invitalia / nazionale)
    if call.source == "Invitalia" or "tasso zero" in text:
        strategy = "QUICK_WIN"
        priority = "HIGH" if score >= 6 else "MEDIUM"

    # 🧪 R&D (Horizon CL6 / CL4)
    elif "horizon" in text and "cluster 6" in text:
        strategy = "R&D"
        priority = "HIGH" if score >= 7 else "MEDIUM"

    # 🏗️ SCALE-UP (EIC)
    elif "eic" in text:
        strategy = "SCALE_UP"
        priority = "HIGH" if score >= 7 else "MEDIUM"

    # 🌍 STRATEGIC EU
    elif "horizon" in text:
        strategy = "STRATEGIC_EU"
        priority = "MEDIUM"

    # fallback
    else:
        strategy = "LOW_PRIORITY"
        priority = "LOW"

    # =========================
    # PRIORITY BOOST BY TIMING
    # =========================
    if timing == "urgent":
        priority = "HIGH"

    if timing == "closed":
        priority = "LOW"

    return {
        "strategy": strategy,
        "priority": priority,
        "timing": timing,
    }