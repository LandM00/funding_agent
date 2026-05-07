from __future__ import annotations

import json
import os
import smtplib
from html import escape
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from funding_agent.models import FundingCall
from funding_agent.classifiers.call_evaluator import evaluate_call


def _safe_json_list(value):
    if not value:
        return []

    if isinstance(value, list):
        return value

    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _row_to_call(row) -> FundingCall:
    return FundingCall(
        source=row["source"],
        source_url=row["source_url"],
        call_id=row["call_id"],
        title=row["title"],
        summary=row["summary"] or "",
        program=row["program"],
        opening_date=row["opening_date"],
        deadline_date=row["deadline_date"],
        budget_total=row["budget_total"],
        funding_type=row["funding_type"],
        record_type=row["record_type"] or "call",
        why_relevant=_safe_json_list(row["why_relevant"]),
        eligible_entities=_safe_json_list(row["eligible_entities"]),
        countries=_safe_json_list(row["countries"]),
        topics=_safe_json_list(row["topics"]),
        raw_text=row["raw_text"] or "",
        relevance_score=float(row["relevance_score"] or 0.0),
    )


def _score_label(score: float) -> str:
    if score >= 8:
        return "ALTO FIT"
    if score >= 6:
        return "MEDIO FIT"
    if score >= 4:
        return "BASSO FIT"
    return "DEBOLE"


def _safe(value) -> str:
    if value is None:
        return ""
    return escape(str(value))


def _build_evaluated_rows(rows, config: dict) -> list[dict]:
    evaluated_rows = []

    for row in rows:
        call = _row_to_call(row)
        evaluation = evaluate_call(call, config)

        score = float(row["relevance_score"] or evaluation["score"])

        evaluated_rows.append(
            {
                "row": row,
                "call": call,
                "evaluation": evaluation,
                "score": score,
                "score_label": _score_label(score),
            }
        )

    return evaluated_rows


def build_email_body(rows, config: dict) -> str:
    evaluated_rows = _build_evaluated_rows(rows, config)

    lines = []
    lines.append("Funding Agent - nuove call da valutare")
    lines.append("")
    lines.append(f"Numero call: {len(evaluated_rows)}")
    lines.append("")

    for item in evaluated_rows:
        row = item["row"]
        evaluation = item["evaluation"]
        fit = evaluation["fit"]
        score = item["score"]
        score_label = item["score_label"]
        reasons = evaluation["why_relevant"]

        lines.append("=" * 72)
        lines.append(f"[{evaluation['priority']}] [{evaluation['decision']}] {row['title']}")
        lines.append("")
        lines.append(f"Score: {score}/10 - {score_label}")
        lines.append(f"Fonte: {row['source']}")
        lines.append(f"Programma: {row['program']}")
        lines.append(f"Opportunity type: {evaluation['opportunity_type']}")
        lines.append(f"Strategia: {evaluation['strategy']}")
        lines.append(f"Decisione: {evaluation['decision']}")
        lines.append(f"Priorità: {evaluation['priority']}")
        lines.append(f"Timing: {evaluation['timing']}")
        lines.append(f"Azione consigliata: {evaluation['next_action']}")

        lines.append("")
        lines.append(
            "Fit breakdown: "
            f"tecnico={fit['technical_fit']} | "
            f"business={fit['business_fit']} | "
            f"beneficiario={fit['applicant_fit']} | "
            f"fattibilità={fit['feasibility']} | "
            f"strategico={fit['strategic_value']} | "
            f"timing={fit['timing_score']}"
        )

        if row["opening_date"]:
            lines.append(f"Apertura: {row['opening_date']}")

        if row["deadline_date"]:
            lines.append(f"Scadenza: {row['deadline_date']}")

        if row["call_id"]:
            lines.append(f"Call ID: {row['call_id']}")

        if reasons:
            lines.append("")
            lines.append("Perché è rilevante:")
            for reason in reasons:
                lines.append(f"- {reason}")

        lines.append("")
        lines.append(f"URL: {row['source_url']}")
        lines.append("")

    return "\n".join(lines)


def _badge_style(priority: str) -> str:
    priority = (priority or "").upper()

    if priority == "HIGH":
        return "background:#ffe5e5;color:#9b1c1c;border:1px solid #f5b5b5;"

    if priority == "MEDIUM":
        return "background:#fff4d6;color:#8a5a00;border:1px solid #f0cf7a;"

    return "background:#eef2f7;color:#334155;border:1px solid #cbd5e1;"


def build_email_html(rows, config: dict) -> str:
    evaluated_rows = _build_evaluated_rows(rows, config)
    cards = []

    for item in evaluated_rows:
        row = item["row"]
        evaluation = item["evaluation"]
        fit = evaluation["fit"]
        score = item["score"]
        score_label = item["score_label"]
        reasons = evaluation["why_relevant"]

        priority = evaluation["priority"]
        decision = evaluation["decision"]
        badge_style = _badge_style(priority)

        reasons_html = ""
        if reasons:
            reasons_html = "<ul style='margin-top:6px;'>" + "".join(
                f"<li>{_safe(reason)}</li>" for reason in reasons
            ) + "</ul>"

        opening_html = (
            f"<p><b>Apertura:</b> {_safe(row['opening_date'])}</p>"
            if row["opening_date"]
            else ""
        )
        deadline_html = (
            f"<p><b>Scadenza:</b> {_safe(row['deadline_date'])}</p>"
            if row["deadline_date"]
            else ""
        )
        call_id_html = (
            f"<p><b>Call ID:</b> {_safe(row['call_id'])}</p>"
            if row["call_id"]
            else ""
        )

        cards.append(
            f"""
            <div style="border:1px solid #ddd;border-radius:12px;padding:18px;margin-bottom:18px;background:#ffffff;">
                <div style="margin-bottom:10px;">
                    <span style="display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:bold;{badge_style}">
                        Priorità: {_safe(priority)}
                    </span>
                    <span style="display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:bold;background:#f5f5f5;color:#333;border:1px solid #ddd;">
                        Decisione: {_safe(decision)}
                    </span>
                    <span style="display:inline-block;padding:5px 9px;border-radius:999px;font-size:12px;font-weight:bold;background:#f5f5f5;color:#333;border:1px solid #ddd;">
                        Fit: {_safe(score_label)} - {_safe(score)}/10
                    </span>
                </div>

                <h2 style="margin-top:0;margin-bottom:8px;font-size:20px;">
                    {_safe(row['title'])}
                </h2>

                <p><b>Fonte:</b> {_safe(row['source'])}</p>
                <p><b>Programma:</b> {_safe(row['program'])}</p>
                <p><b>Opportunity type:</b> {_safe(evaluation['opportunity_type'])}</p>
                <p><b>Strategia:</b> {_safe(evaluation['strategy'])}</p>
                <p><b>Timing:</b> {_safe(evaluation['timing'])}</p>

                <div style="background:#f8fafc;border-left:4px solid #64748b;padding:10px 12px;margin:12px 0;">
                    <p style="margin:0;"><b>Azione consigliata:</b> {_safe(evaluation['next_action'])}</p>
                </div>

                <p>
                    <b>Fit breakdown:</b><br>
                    tecnico={_safe(fit['technical_fit'])} |
                    business={_safe(fit['business_fit'])} |
                    beneficiario={_safe(fit['applicant_fit'])} |
                    fattibilità={_safe(fit['feasibility'])} |
                    strategico={_safe(fit['strategic_value'])} |
                    timing={_safe(fit['timing_score'])}
                </p>

                {opening_html}
                {deadline_html}
                {call_id_html}

                <p><b>Perché è rilevante:</b></p>
                {reasons_html if reasons_html else "<p>Nessuna motivazione disponibile.</p>"}

                <p style="margin-top:14px;">
                    <a href="{_safe(row['source_url'])}" style="display:inline-block;background:#1f2937;color:#ffffff;text-decoration:none;padding:9px 13px;border-radius:8px;">
                        Apri call
                    </a>
                </p>
            </div>
            """
        )

    return f"""
    <html>
        <body style="font-family:Arial, sans-serif; color:#222; background:#f3f4f6; padding:20px;">
            <div style="max-width:900px;margin:0 auto;">
                <h1 style="margin-bottom:4px;">Funding Agent - nuove call da valutare</h1>
                <p style="font-size:15px;">Numero call: <b>{len(evaluated_rows)}</b></p>
                {''.join(cards)}
                <p style="font-size:12px;color:#666;margin-top:24px;">
                    Email generata automaticamente dal Funding Agent NEX / Neura GrowTech.
                </p>
            </div>
        </body>
    </html>
    """


def _get_email_credentials(email_cfg: dict) -> tuple[str | None, str | None, str | None]:
    """
    Supporta sia la nuova configurazione sicura tramite variabili d'ambiente,
    sia la vecchia configurazione con valori diretti nel config.yaml.
    """

    smtp_user = None
    smtp_password = None
    from_email = None

    smtp_user_env = email_cfg.get("smtp_user_env")
    smtp_password_env = email_cfg.get("smtp_password_env")
    from_email_env = email_cfg.get("from_email_env")

    if smtp_user_env:
        smtp_user = os.getenv(smtp_user_env)

    if smtp_password_env:
        smtp_password = os.getenv(smtp_password_env)

    if from_email_env:
        from_email = os.getenv(from_email_env)

    # Fallback vecchio formato, utile solo se non hai ancora migrato il config.
    smtp_user = smtp_user or email_cfg.get("smtp_user")
    smtp_password = smtp_password or email_cfg.get("smtp_password")
    from_email = from_email or email_cfg.get("from_email") or smtp_user

    return smtp_user, smtp_password, from_email


def send_email_notification(config: dict, rows) -> None:
    email_cfg = config.get("email", {})

    if not email_cfg.get("enabled", False):
        print("Email disabilitata in config.yaml")
        return

    smtp_host = email_cfg.get("smtp_host")
    smtp_port = email_cfg.get("smtp_port")
    to_emails = email_cfg.get("to_emails", [])

    smtp_user, smtp_password, from_email = _get_email_credentials(email_cfg)

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_emails]):
        print(
            "Configurazione email incompleta. "
            "Controlla config.yaml e le variabili d'ambiente SMTP_USER, SMTP_PASSWORD e FROM_EMAIL/SMTP_USER."
        )
        return

    subject = f"Funding Agent - {len(rows)} nuove call da valutare"

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    plain_body = build_email_body(rows, config)
    html_body = build_email_html(rows, config)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_emails, msg.as_string())

    print(f"Email inviata a: {', '.join(to_emails)}")