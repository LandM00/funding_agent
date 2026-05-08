import argparse
import json

from funding_agent.config import load_config
from funding_agent.db import FundingDB
from funding_agent.models import FundingCall
from funding_agent.rules.visibility import should_show_call
from funding_agent.classifiers.call_evaluator import evaluate_call
from funding_agent.collectors.invitalia import InvitaliaCollector
from funding_agent.collectors.invitalia_on import InvitaliaONCollector
from funding_agent.collectors.regione_er import RegioneERCollector
from funding_agent.collectors.eu_calls_api import EUCallsAPICollector
from funding_agent.collectors.emiliaromagna_startup import EmiliaRomagnaStartupCollector
from funding_agent.collectors.incentivi_gov import IncentiviGovCollector
from funding_agent.collectors.eic_eureka import EICEurekaCollector
from funding_agent.collectors.space_opportunities import SpaceOpportunitiesCollector
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
        EmiliaRomagnaStartupCollector(),
        IncentiviGovCollector(),
        EICEurekaCollector(),
        SpaceOpportunitiesCollector(),
    ]

    total_calls = 0

    for collector in collectors:
        calls = collector.fetch()

        for call in calls:
            evaluation = evaluate_call(call, config)
            call.relevance_score = evaluation["score"]
            call.why_relevant = evaluation["why_relevant"]

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


def _record_type_label(row) -> str:
    record_type = row["record_type"]

    if record_type == "hub":
        return "HUB / pagina indice"
    if record_type == "support_doc":
        return "documento di supporto"

    return "incentivo / call"


def _evaluate_visible_rows(rows, config: dict, only_real_calls: bool = False):
    """
    Converte le righe DB in valutazioni aggiornate.

    Importante:
    - non usa relevance_score salvato nel DB per digest/dashboard CLI;
    - ricalcola score, strategy, decision e priority con il codice corrente;
    - ordina in base allo score aggiornato.
    """
    evaluated_rows = []

    for row in rows:
        call = row_to_call(row)

        if only_real_calls and call.record_type != "call":
            continue

        if only_real_calls:
            if not should_show_call(call):
                continue
        else:
            if call.record_type == "call" and not should_show_call(call):
                continue

        evaluation = evaluate_call(call, config)
        score = float(evaluation["score"])

        evaluated_rows.append(
            {
                "row": row,
                "call": call,
                "evaluation": evaluation,
                "score": score,
            }
        )

    evaluated_rows.sort(
        key=lambda item: (
            item["score"],
            item["evaluation"].get("fit", {}).get("strategic_value", 0),
            item["evaluation"].get("fit", {}).get("technical_fit", 0),
        ),
        reverse=True,
    )

    return evaluated_rows


def _print_evaluated_rows(evaluated_rows, only_calls_label: bool = False) -> None:
    for item in evaluated_rows:
        row = item["row"]
        evaluation = item["evaluation"]
        score = float(item["score"])

        level = _score_label(score, row["record_type"])

        print("\n" + "=" * 80)
        print(f"{level} | Score: {score}")
        print(f"Titolo: {row['title']}")
        print(f"Fonte: {row['source']}")
        print(f"Programma: {row['program']}")

        if only_calls_label:
            print("Tipo: incentivo / call")
        else:
            print(f"Tipo: {_record_type_label(row)}")

        print(f"Opportunity type: {evaluation['opportunity_type']}")
        print(f"Strategia: {evaluation['strategy']}")
        print(f"Decisione: {evaluation['decision']}")
        print(f"Priorità: {evaluation['priority']}")
        print(f"Timing: {evaluation['timing']}")
        print(f"Azione consigliata: {evaluation['next_action']}")

        fit = evaluation["fit"]
        print(
            "Fit breakdown: "
            f"tecnico={fit['technical_fit']} | "
            f"business={fit['business_fit']} | "
            f"beneficiario={fit['applicant_fit']} | "
            f"fattibilità={fit['feasibility']} | "
            f"strategico={fit['strategic_value']} | "
            f"timing={fit['timing_score']}"
        )

        if row["opening_date"]:
            print(f"Apertura: {row['opening_date']}")

        if row["deadline_date"]:
            print(f"Scadenza: {row['deadline_date']}")

        if row["call_id"]:
            print(f"Call ID: {row['call_id']}")

        reasons = evaluation["why_relevant"]
        if reasons:
            print("Perché è rilevante:")
            for reason in reasons:
                print(f" - {reason}")

        print(f"URL: {row['source_url']}")


def run_digest(config: dict, limit: int = 100) -> None:
    db = FundingDB(config["database"]["path"])

    # Prendiamo più righe del limite perché poi riordiniamo con lo score aggiornato.
    rows = db.get_top_calls(limit=limit * 5)
    evaluated_rows = _evaluate_visible_rows(rows, config, only_real_calls=False)

    if not evaluated_rows:
        print("Nessun record presente nel database.")
        db.close()
        return

    _print_evaluated_rows(evaluated_rows[:limit], only_calls_label=False)
    db.close()


def run_digest_calls(config: dict, limit: int = 100) -> None:
    db = FundingDB(config["database"]["path"])

    # Prendiamo più righe del limite perché poi riordiniamo con lo score aggiornato.
    rows = db.get_top_real_calls(limit=limit * 5)
    evaluated_rows = _evaluate_visible_rows(rows, config, only_real_calls=True)

    if not evaluated_rows:
        print("Nessuna call reale aperta o in apertura entro 6 mesi presente nel database.")
        db.close()
        return

    _print_evaluated_rows(evaluated_rows[:limit], only_calls_label=True)
    db.close()


def run_notify_email(config: dict, min_score: float = 6.0) -> None:
    """
    Invia solo nuove call non ancora notificate.
    Dopo l'invio, marca le call come notificate.
    Questo comando è per uso operativo reale.

    Nota:
    - dopo ogni crawl, il DB viene aggiornato con lo score corrente;
    - qui ricalcoliamo comunque lo score per filtrare in modo coerente.
    """
    db = FundingDB(config["database"]["path"])
    rows = db.get_unnotified_real_calls(min_score=0.0)

    evaluated_rows = _evaluate_visible_rows(rows, config, only_real_calls=True)
    rows_to_send = [
        item["row"]
        for item in evaluated_rows
        if item["score"] >= min_score
    ]

    if not rows_to_send:
        print("Nessuna nuova call aperta o in apertura entro 6 mesi da notificare.")
        db.close()
        return

    send_email_notification(config, rows_to_send)
    db.mark_calls_notified([row["source_url"] for row in rows_to_send])
    db.close()


def run_test_email(config: dict, limit: int = 5) -> None:
    """
    Invia una email di test usando le migliori call già presenti nel database.
    Non marca le call come notificate.
    Serve per testare layout, contenuto e credenziali email.
    """
    db = FundingDB(config["database"]["path"])
    rows = db.get_top_real_calls(limit=limit * 5)

    evaluated_rows = _evaluate_visible_rows(rows, config, only_real_calls=True)

    if not evaluated_rows:
        print("Nessuna call disponibile per testare l'email.")
        db.close()
        return

    rows_to_send = [item["row"] for item in evaluated_rows[:limit]]

    send_email_notification(config, rows_to_send)

    print(
        f"Email di test inviata con {len(rows_to_send)} call. "
        "Le call NON sono state marcate come notificate."
    )

    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Funding Agent")
    parser.add_argument(
        "command",
        choices=["crawl", "digest", "digest-calls", "notify-email", "test-email"],
        nargs="?",
        default="crawl",
        help="Azione da eseguire",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Numero massimo di record nel digest o nella email di test",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=6.0,
        help="Score minimo per le notifiche email operative",
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
    elif args.command == "test-email":
        run_test_email(config, limit=args.limit)


if __name__ == "__main__":
    main()