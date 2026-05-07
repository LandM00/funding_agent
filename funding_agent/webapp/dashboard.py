import json
from datetime import datetime

import pandas as pd
import streamlit as st

from funding_agent.db import FundingDB
from funding_agent.config import load_config
from funding_agent.models import FundingCall
from funding_agent.rules.visibility import should_show_call
from funding_agent.classifiers.call_evaluator import evaluate_call


# ---------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------
def get_secret_value(key: str, default=None):
    try:
        value = st.secrets.get(key, default)
        return value
    except Exception:
        return default


def check_password() -> bool:
    """
    Login semplice per proteggere la dashboard online.
    In locale/cloud legge APP_PASSWORD da Streamlit secrets.
    """
    expected_password = get_secret_value("APP_PASSWORD", "")

    # Se non è impostata APP_PASSWORD, blocchiamo l'accesso in modo esplicito.
    if not expected_password:
        st.error(
            "APP_PASSWORD non configurata. Imposta una password nei secrets "
            "prima di pubblicare la dashboard."
        )
        return False

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.title("Funding Agent")
    st.subheader("Accesso riservato")
    st.caption("Dashboard privata per il monitoraggio delle opportunità di finanziamento NEX / Neura GrowTech.")

    password = st.text_input("Password", type="password")

    col1, col2 = st.columns([1, 4])
    with col1:
        login_clicked = st.button("Accedi", use_container_width=True)

    if login_clicked:
        if password == expected_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Password non corretta.")

    return False


# ---------------------------------------------------------------------
# UTILS
# ---------------------------------------------------------------------
def row_value(row, key: str, default=""):
    try:
        if hasattr(row, "keys") and key in row.keys():
            value = row[key]
            return value if value is not None else default
    except Exception:
        pass

    try:
        value = row.get(key, default)
        return value if value is not None else default
    except Exception:
        return default


def safe_json_list(value):
    if isinstance(value, list):
        return value

    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def row_to_call(row) -> FundingCall:
    return FundingCall(
        source=row_value(row, "source"),
        source_url=row_value(row, "source_url"),
        call_id=row_value(row, "call_id"),
        title=row_value(row, "title"),
        summary=row_value(row, "summary"),
        program=row_value(row, "program"),
        opening_date=row_value(row, "opening_date", None),
        deadline_date=row_value(row, "deadline_date", None),
        budget_total=row_value(row, "budget_total", None),
        funding_type=row_value(row, "funding_type"),
        record_type=row_value(row, "record_type", "call"),
        why_relevant=safe_json_list(row_value(row, "why_relevant", "[]")),
        eligible_entities=safe_json_list(row_value(row, "eligible_entities", "[]")),
        countries=safe_json_list(row_value(row, "countries", "[]")),
        topics=safe_json_list(row_value(row, "topics", "[]")),
        raw_text=row_value(row, "raw_text"),
        relevance_score=float(row_value(row, "relevance_score", 0.0) or 0.0),
    )


def is_postgres_config(config: dict) -> bool:
    db_path = str(config.get("database", {}).get("path", ""))
    backend = str(config.get("database", {}).get("backend", ""))
    return backend == "postgres" or db_path.startswith("postgres")


# ---------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def load_calls():
    config = load_config("config.yaml")

    db = FundingDB(config["database"]["path"])
    rows = db.get_all_real_calls()
    db.close()

    visible = []
    for row in rows:
        call = row_to_call(row)
        if should_show_call(call):
            visible.append(dict(row))

    loaded_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    return visible, config, loaded_at


# ---------------------------------------------------------------------
# LABELS
# ---------------------------------------------------------------------
def fit_label(score: float) -> str:
    if score >= 8.0:
        return "🔥 ALTO FIT"
    if score >= 6.0:
        return "⚡ MEDIO FIT"
    if score >= 4.0:
        return "➖ BASSO FIT"
    return "· DEBOLE"


def priority_label(priority: str) -> str:
    mapping = {
        "HIGH": "🔥 Alta",
        "MEDIUM": "⚡ Media",
        "LOW": "💤 Bassa",
    }
    return mapping.get(priority, priority or "N/D")


def decision_label(decision: str) -> str:
    mapping = {
        "APPLY_NOW": "✅ Apply now",
        "EVALUATE": "🔎 Valutare",
        "MONITOR": "👀 Monitorare",
        "MONITOR_STRATEGIC": "🧭 Monitor strategico",
        "MONITOR_LOW": "🕓 Monitor basso",
        "IGNORE": "⛔ Ignorare",
    }
    return mapping.get(decision, decision or "N/D")


# ---------------------------------------------------------------------
# DATAFRAME
# ---------------------------------------------------------------------
def build_dataframe(rows, config):
    records = []

    for row in rows:
        call = row_to_call(row)
        evaluation = evaluate_call(call, config)
        fit = evaluation["fit"]

        score = float(evaluation["score"])
        why = evaluation["why_relevant"]
        topics = safe_json_list(row_value(row, "topics", "[]"))

        records.append(
            {
                "Titolo": row_value(row, "title"),
                "Fonte": row_value(row, "source"),
                "Programma": row_value(row, "program"),
                "Score": score,
                "Fit": fit_label(score),
                "Opportunity type": evaluation["opportunity_type"],
                "Decision": decision_label(evaluation["decision"]),
                "DecisionRaw": evaluation["decision"],
                "Priority": priority_label(evaluation["priority"]),
                "PriorityRaw": evaluation["priority"],
                "Strategy": evaluation["strategy"],
                "Timing": evaluation["timing"],
                "NEX match": evaluation["nex_core_matches"],
                "Next Action": evaluation["next_action"],
                "Technical fit": fit["technical_fit"],
                "Business fit": fit["business_fit"],
                "Applicant fit": fit["applicant_fit"],
                "Feasibility": fit["feasibility"],
                "Strategic value": fit["strategic_value"],
                "Timing score": fit["timing_score"],
                "Apertura": row_value(row, "opening_date"),
                "Scadenza": row_value(row, "deadline_date"),
                "Call ID": row_value(row, "call_id"),
                "URL": row_value(row, "source_url"),
                "Topics": ", ".join(topics),
                "WhyRelevant": "; ".join(why),
                "Summary": row_value(row, "summary"),
            }
        )

    df = pd.DataFrame(records)

    if not df.empty:
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        decision_order = {
            "APPLY_NOW": 0,
            "EVALUATE": 1,
            "MONITOR": 2,
            "MONITOR_STRATEGIC": 3,
            "MONITOR_LOW": 4,
            "IGNORE": 5,
        }

        df["_priority_order"] = df["PriorityRaw"].map(priority_order).fillna(9)
        df["_decision_order"] = df["DecisionRaw"].map(decision_order).fillna(9)

        df = df.sort_values(
            by=["_priority_order", "_decision_order", "Score", "Titolo"],
            ascending=[True, True, False, True],
        ).reset_index(drop=True)

    return df


# ---------------------------------------------------------------------
# RENDER
# ---------------------------------------------------------------------
def render_metrics(df):
    total = len(df)
    high = len(df[df["PriorityRaw"] == "HIGH"])
    medium = len(df[df["PriorityRaw"] == "MEDIUM"])
    evaluate = len(df[df["DecisionRaw"] == "EVALUATE"])
    monitor = len(df[df["DecisionRaw"].isin(["MONITOR", "MONITOR_STRATEGIC"])])
    ignore = len(df[df["DecisionRaw"] == "IGNORE"])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Call visibili", total)
    c2.metric("🔥 Priorità alta", high)
    c3.metric("⚡ Priorità media", medium)
    c4.metric("🔎 Valutare", evaluate)
    c5.metric("👀 Monitorare", monitor)
    c6.metric("⛔ Ignorare", ignore)


def render_fit_breakdown(row):
    st.markdown("#### Fit breakdown (0-5)")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Tecnico", row["Technical fit"])
    c2.metric("Business", row["Business fit"])
    c3.metric("Beneficiario", row["Applicant fit"])
    c4.metric("Fattibilità", row["Feasibility"])
    c5.metric("Strategico", row["Strategic value"])
    c6.metric("Timing", row["Timing score"])


def render_sidebar_status(config: dict, loaded_at: str, df: pd.DataFrame):
    st.sidebar.header("Stato sistema")

    if is_postgres_config(config):
        st.sidebar.success("Database: Supabase/PostgreSQL")
    else:
        st.sidebar.warning("Database: SQLite locale")

    st.sidebar.caption(f"Ultimo caricamento dashboard: {loaded_at}")
    st.sidebar.caption(f"Record visibili: {len(df)}")

    if st.sidebar.button("Aggiorna vista"):
        st.cache_data.clear()
        st.rerun()

    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()


def render_filters(df):
    st.sidebar.header("Filtri")

    min_score = st.sidebar.slider("Score minimo", 0.0, 10.0, 0.0, 0.5)

    sources = sorted(df["Fonte"].dropna().unique().tolist())
    selected_sources = st.sidebar.multiselect("Fonte", sources, default=sources)

    decisions = sorted(df["Decision"].dropna().unique().tolist())
    selected_decisions = st.sidebar.multiselect("Decisione", decisions, default=decisions)

    priorities = sorted(df["Priority"].dropna().unique().tolist())
    selected_priorities = st.sidebar.multiselect("Priorità", priorities, default=priorities)

    opportunity_types = sorted(df["Opportunity type"].dropna().unique().tolist())
    selected_types = st.sidebar.multiselect("Opportunity type", opportunity_types, default=opportunity_types)

    keyword = st.sidebar.text_input("Keyword")

    filtered = df[df["Score"] >= min_score].copy()

    if selected_sources:
        filtered = filtered[filtered["Fonte"].isin(selected_sources)]

    if selected_decisions:
        filtered = filtered[filtered["Decision"].isin(selected_decisions)]

    if selected_priorities:
        filtered = filtered[filtered["Priority"].isin(selected_priorities)]

    if selected_types:
        filtered = filtered[filtered["Opportunity type"].isin(selected_types)]

    if keyword.strip():
        k = keyword.strip().lower()
        filtered = filtered[
            filtered["Titolo"].str.lower().str.contains(k, na=False)
            | filtered["Programma"].str.lower().str.contains(k, na=False)
            | filtered["Call ID"].str.lower().str.contains(k, na=False)
            | filtered["Topics"].str.lower().str.contains(k, na=False)
            | filtered["WhyRelevant"].str.lower().str.contains(k, na=False)
            | filtered["Opportunity type"].str.lower().str.contains(k, na=False)
            | filtered["Next Action"].str.lower().str.contains(k, na=False)
        ]

    return filtered


def render_detail(row):
    st.subheader("Dettaglio call")
    st.markdown(f"### {row['Titolo']}")

    top1, top2, top3, top4 = st.columns(4)
    top1.metric("Score (0-10)", row["Score"])
    top2.metric("Fit", row["Fit"])
    top3.metric("Decisione", row["Decision"])
    top4.metric("Priorità", row["Priority"])

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(f"**Programma:** {row['Programma']}")
        st.write(f"**Fonte:** {row['Fonte']}")
        st.write(f"**Call ID:** {row['Call ID']}")
        st.write(f"**Opportunity type:** {row['Opportunity type']}")
        st.write(f"**Strategia:** {row['Strategy']}")
        st.write(f"**Topics:** {row['Topics'] or 'N/D'}")

        if row["Summary"]:
            st.markdown("#### Sintesi")
            st.write(row["Summary"])

        if row["URL"]:
            st.markdown(f"[Apri call ufficiale]({row['URL']})")

    with col2:
        st.write(f"**Timing:** {row['Timing']}")
        st.write(f"**NEX match:** {row['NEX match']}/6")
        st.write(f"**Apertura:** {row['Apertura'] or 'N/D'}")
        st.write(f"**Scadenza:** {row['Scadenza'] or 'N/D'}")

    st.markdown("#### Azione consigliata")
    st.info(row["Next Action"])

    render_fit_breakdown(row)

    st.markdown("#### Perché è rilevante")
    if row["WhyRelevant"]:
        for reason in row["WhyRelevant"].split(";"):
            if reason.strip():
                st.write(f"- {reason.strip()}")
    else:
        st.write("Nessuna motivazione disponibile.")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Funding Agent", layout="wide")

    if not check_password():
        return

    st.title("Funding Agent Dashboard")
    st.caption(
        "Call aperte o in apertura entro 6 mesi — ranking decisionale per NEX / Neura GrowTech"
    )

    try:
        rows, config, loaded_at = load_calls()
    except Exception as e:
        st.error("Errore durante il caricamento dei dati.")
        st.exception(e)
        st.stop()

    if not rows:
        st.warning(
            "Nessuna call valida trovata. Verifica che il database cloud sia configurato "
            "e che il workflow di aggiornamento abbia eseguito almeno un crawl."
        )
        st.stop()

    df = build_dataframe(rows, config)

    if df.empty:
        st.warning("Nessuna call disponibile dopo la valutazione.")
        st.stop()

    render_sidebar_status(config, loaded_at, df)
    render_metrics(df)

    filtered = render_filters(df)

    st.subheader("Call disponibili")

    if filtered.empty:
        st.info("Nessuna call corrisponde ai filtri selezionati.")
        st.stop()

    st.dataframe(
        filtered[
            [
                "Titolo",
                "Fonte",
                "Score",
                "Fit",
                "Decision",
                "Priority",
                "Timing",
                "Opportunity type",
                "NEX match",
                "Scadenza",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    options = [
        f"{row['Titolo']} | {row['Fonte']} | {row['Decision']} | score={row['Score']}"
        for _, row in filtered.iterrows()
    ]

    selected_option = st.selectbox("Seleziona una call da analizzare", options)
    selected_index = options.index(selected_option)
    selected_row = filtered.iloc[selected_index]

    render_detail(selected_row)

    csv_data = filtered.drop(
        columns=["_priority_order", "_decision_order"],
        errors="ignore",
    ).to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Scarica CSV filtrato",
        data=csv_data,
        file_name="funding_calls_filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()