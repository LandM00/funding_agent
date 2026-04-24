import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def _safe_json_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _priority_label(score: float) -> str:
    if score >= 8:
        return "ALTA"
    if score >= 6:
        return "MEDIA"
    return "BASSA"


def build_email_body(rows) -> str:
    lines = []
    lines.append("Funding Agent - nuove call da valutare")
    lines.append("")
    lines.append(f"Numero call: {len(rows)}")
    lines.append("")

    for row in rows:
        score = float(row["relevance_score"] or 0.0)
        priority = _priority_label(score)
        reasons = _safe_json_list(row["why_relevant"])

        lines.append("=" * 72)
        lines.append(f"[{priority}] {row['title']}")
        lines.append("")
        lines.append(f"Fonte: {row['source']}")
        lines.append(f"Programma: {row['program']}")
        lines.append(f"Score: {score}/10")

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


def build_email_html(rows) -> str:
    cards = []

    for row in rows:
        score = float(row["relevance_score"] or 0.0)
        priority = _priority_label(score)
        reasons = _safe_json_list(row["why_relevant"])

        reasons_html = ""
        if reasons:
            reasons_html = "<ul>" + "".join(f"<li>{r}</li>" for r in reasons) + "</ul>"

        opening_html = f"<p><b>Apertura:</b> {row['opening_date']}</p>" if row["opening_date"] else ""
        deadline_html = f"<p><b>Scadenza:</b> {row['deadline_date']}</p>" if row["deadline_date"] else ""
        call_id_html = f"<p><b>Call ID:</b> {row['call_id']}</p>" if row["call_id"] else ""

        cards.append(
            f"""
            <div style="border:1px solid #ddd;border-radius:10px;padding:16px;margin-bottom:16px;">
                <h2 style="margin-top:0;">{row['title']}</h2>
                <p><b>Priorità:</b> {priority} &nbsp; | &nbsp; <b>Score:</b> {score}/10</p>
                <p><b>Fonte:</b> {row['source']}</p>
                <p><b>Programma:</b> {row['program']}</p>
                {opening_html}
                {deadline_html}
                {call_id_html}
                <p><b>Perché è rilevante:</b></p>
                {reasons_html if reasons_html else "<p>Nessuna motivazione disponibile.</p>"}
                <p><a href="{row['source_url']}">Apri call</a></p>
            </div>
            """
        )

    return f"""
    <html>
        <body style="font-family:Arial, sans-serif; color:#222;">
            <h1>Funding Agent - nuove call da valutare</h1>
            <p>Numero call: <b>{len(rows)}</b></p>
            {''.join(cards)}
        </body>
    </html>
    """


def send_email_notification(config: dict, rows) -> None:
    email_cfg = config.get("email", {})

    if not email_cfg.get("enabled", False):
        print("Email disabilitata in config.yaml")
        return

    smtp_host = email_cfg.get("smtp_host")
    smtp_port = email_cfg.get("smtp_port")
    smtp_user = email_cfg.get("smtp_user")
    smtp_password = email_cfg.get("smtp_password")
    from_email = email_cfg.get("from_email")
    to_emails = email_cfg.get("to_emails", [])

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_emails]):
        print("Configurazione email incompleta in config.yaml")
        return

    subject = f"Funding Agent - {len(rows)} nuove call da valutare"

    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject

    plain_body = build_email_body(rows)
    html_body = build_email_html(rows)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, to_emails, msg.as_string())

    print(f"Email inviata a: {', '.join(to_emails)}")