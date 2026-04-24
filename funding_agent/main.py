import argparse
import json

from funding_agent.config import load_config
from funding_agent.db import FundingDB
from funding_agent.models import FundingCall
from funding_agent.rules.visibility import should_show_call
from funding_agent.classifiers.scoring import score_call
from funding_agent.classifiers.explainer import build_why_relevant
from funding_agent.collectors.invitalia import InvitaliaCollector
from funding_agent.collectors.invitalia_on import InvitaliaONCollector
from funding_agent.collectors.regione_er import RegioneERCollector
from funding_agent.collectors.eu_calls_api import EUCallsAPICollector
from funding_agent.notifier.email_sender import send_email_notification

def row_to_call(row) -> FundingCall:
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
        why_relevant=json.loads(row["why_relevant"]) if row["why_relevant"] else [],
        eligible_entities=json.loads(row["eligible_entities"]) if row["eligible_entities"] else [],
        countries=json.loads(row["countries"]) if row["countries"] else [],
        topics=json.loads(row["topics"]) if row["topics"] else [],
        raw_text=row["raw_text"] or "",
        relevance_score=float(row["relevance_score"] or 0.0),
    )


def run_crawl(config: dict) -> None:
    db = FundingDB(config["database"]["path"])

    collectors = [
        InvitaliaCollector(),
        InvitaliaONCollector(),
        RegioneERCollector(),
        EUCallsAPICollector(),
    ]

    total_calls = 0

    for collector in collectors:
        calls = collector.fetch()

        for call in calls:
            call.relevance_score = score_call(call, config)
            call.why_relevant = build_why_relevant(call)
            
        db.upsert_calls(calls)
        total_calls += len(calls)

        print(f"[OK] Collector '{collector.name}' -> {len(calls)} record(s)")

    print(f"\nTotale record processati: {total_calls}")
    db.close()


def _score_label(score: float, record_type: str) -> str:
    if record_type == "hub":
        return "🧭 HUB"
    if score >= 8.0:
        return "🔥 ALTO FIT"
    if score >= 6.0:
        return "⚡ MEDIO FIT"
    if score >= 4.0:
        return "➖ BASSO FIT"
    return "· DEBOLE"


def _print_rows(rows, only_calls_label: bool = False) -> None:
    for row in rows:
        print("\n" + "=" * 80)

        score = float(row["relevance_score"])
        level = _score_label(score, row["record_type"])

        print(f"{level} | Score: {score}")
        print(f"Titolo: {row['title']}")
        print(f"Fonte: {row['source']}")
        print(f"Programma: {row['program']}")

        if only_calls_label:
            print("Tipo: incentivo / call")
        else:
            if row["record_type"] == "hub":
                print("Tipo: HUB / pagina indice")
            elif row["record_type"] == "support_doc":
                print("Tipo: documento di supporto")
            else:
                print("Tipo: incentivo / call")

        if row["opening_date"]:
            print(f"Apertura: {row['opening_date']}")

        if row["deadline_date"]:
            print(f"Scadenza: {row['deadline_date']}")

        if row["call_id"]:
            print(f"Call ID: {row['call_id']}")

        if row["why_relevant"]:
            reasons = json.loads(row["why_relevant"])
            if reasons:
                print("Perché è rilevante:")
                for reason in reasons:
                    print(f" - {reason}")

        print(f"URL: {row['source_url']}")


def run_digest(config: dict, limit: int = 100) -> None:
    db = FundingDB(config["database"]["path"])
    rows = db.get_top_calls(limit=limit)

    visible_rows = []
    for row in rows:
        call = row_to_call(row)
        if call.record_type != "call" or should_show_call(call):
            visible_rows.append(row)

    if not visible_rows:
        print("Nessun record presente nel database.")
        db.close()
        return

    _print_rows(visible_rows[:limit], only_calls_label=False)
    db.close()


def run_digest_calls(config: dict, limit: int = 100) -> None:
    db = FundingDB(config["database"]["path"])
    rows = db.get_top_real_calls(limit=limit * 5)

    visible_rows = []
    for row in rows:
        call = row_to_call(row)
        if should_show_call(call):
            visible_rows.append(row)

    if not visible_rows:
        print("Nessuna call reale aperta o in apertura entro 6 mesi presente nel database.")
        db.close()
        return

    _print_rows(visible_rows[:limit], only_calls_label=True)
    db.close()


def run_notify_email(config: dict, min_score: float = 6.0) -> None:
    db = FundingDB(config["database"]["path"])
    rows = db.get_unnotified_real_calls(min_score=min_score)

    visible_rows = []
    for row in rows:
        call = row_to_call(row)
        if should_show_call(call):
            visible_rows.append(row)

    if not visible_rows:
        print("Nessuna nuova call aperta o in apertura entro 6 mesi da notificare.")
        db.close()
        return

    send_email_notification(config, visible_rows)
    db.mark_calls_notified([row["source_url"] for row in visible_rows])
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Funding Agent")
    parser.add_argument(
        "command",
        choices=["crawl", "digest", "digest-calls", "notify-email"],
        nargs="?",
        default="crawl",
        help="Azione da eseguire",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Numero massimo di record nel digest",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=6.0,
        help="Score minimo per le notifiche email",
    )

    args = parser.parse_args()
    config = load_config("config.yaml")

    if args.command == "crawl":
        run_crawl(config)
    elif args.command == "digest":
        run_digest(config, limit=args.limit)
    elif args.command == "digest-calls":
        run_digest_calls(config, limit=args.limit)
    elif args.command == "notify-email":
        run_notify_email(config, min_score=args.min_score)


if __name__ == "__main__":
    main()