import json
import pandas as pd
import streamlit as st

from funding_agent.db import FundingDB
from funding_agent.config import load_config
from funding_agent.models import FundingCall
from funding_agent.rules.visibility import should_show_call


# -------------------------
# SAFE ROW ACCESS
# -------------------------
def row_value(row, key: str, default=""):
    try:
        if key in row.keys():
            value = row[key]
            return value if value is not None else default
    except Exception:
        pass
    return default


# -------------------------
# MODEL CONVERSION
# -------------------------
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
        why_relevant=json.loads(row_value(row, "why_relevant", "[]") or "[]"),
        eligible_entities=json.loads(row_value(row, "eligible_entities", "[]") or "[]"),
        countries=json.loads(row_value(row, "countries", "[]") or "[]"),
        topics=json.loads(row_value(row, "topics", "[]") or "[]"),
        raw_text=row_value(row, "raw_text"),
        relevance_score=float(row_value(row, "relevance_score", 0.0) or 0.0),
    )


# -------------------------
# LOAD + FILTER
# -------------------------
def load_calls():
    config = load_config("config.yaml")
    db = FundingDB(config["database"]["path"])
    rows = db.get_all_real_calls()
    db.close()

    visible = []
    for row in rows:
        call = row_to_call(row)
        if should_show_call(call):
            visible.append(row)

    return visible


# -------------------------
# PRIORITY LOGIC (UX)
# -------------------------
def compute_priority(score):
    if score >= 8:
        return "🔥 Alta"
    elif score >= 6:
        return "⚡ Media"
    else:
        return "💤 Bassa"


def clean_summary(text, max_len=300):
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


# -------------------------
# DATAFRAME
# -------------------------
def build_dataframe(rows):
    records = []

    for row in rows:
        score = float(row_value(row, "relevance_score", 0.0) or 0.0)

        try:
            why = json.loads(row_value(row, "why_relevant", "[]") or "[]")
        except:
            why = []

        try:
            topics = json.loads(row_value(row, "topics", "[]") or "[]")
        except:
            topics = []

        records.append({
            "Titolo": row_value(row, "title"),
            "Fonte": row_value(row, "source"),
            "Programma": row_value(row, "program"),
            "Score": score,
            "Priority": compute_priority(score),
            "Apertura": row_value(row, "opening_date"),
            "Scadenza": row_value(row, "deadline_date"),
            "Call ID": row_value(row, "call_id"),
            "URL": row_value(row, "source_url"),
            "Topics": ", ".join(topics),
            "WhyRelevant": "; ".join(why),
        })

    df = pd.DataFrame(records)

    if not df.empty:
        df = df.sort_values(by="Score", ascending=False).reset_index(drop=True)

    return df


# -------------------------
# METRICS
# -------------------------
def render_metrics(df):
    total = len(df)
    high = len(df[df["Score"] >= 8])
    medium = len(df[(df["Score"] >= 6) & (df["Score"] < 8)])
    low = len(df[df["Score"] < 6])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Call attive", total)
    c2.metric("🔥 Alta priorità", high)
    c3.metric("⚡ Media", medium)
    c4.metric("💤 Bassa", low)


# -------------------------
# MAIN UI
# -------------------------
def main():
    st.set_page_config(page_title="Funding Agent", layout="wide")

    st.title("Funding Agent Dashboard")
    st.caption("Call aperte o in apertura entro 6 mesi")

    rows = load_calls()

    if not rows:
        st.warning("Nessuna call valida trovata.")
        return

    df = build_dataframe(rows)

    if df.empty:
        st.warning("Nessuna call disponibile.")
        return

    render_metrics(df)

    # -------------------------
    # SIDEBAR
    # -------------------------
    st.sidebar.header("Filtri")

    min_score = st.sidebar.slider("Score minimo", 0.0, 10.0, 0.0, 0.5)

    sources = sorted(df["Fonte"].unique())
    selected_sources = st.sidebar.multiselect("Fonte", sources, default=sources)

    keyword = st.sidebar.text_input("Keyword")

    filtered = df[df["Score"] >= min_score]

    if selected_sources:
        filtered = filtered[filtered["Fonte"].isin(selected_sources)]

    if keyword:
        k = keyword.lower()
        filtered = filtered[
            filtered["Titolo"].str.lower().str.contains(k)
        ]

    # -------------------------
    # TABLE
    # -------------------------
    st.subheader("Call disponibili")

    st.dataframe(
        filtered[["Titolo", "Fonte", "Score", "Priority", "Scadenza"]],
        use_container_width=True,
        hide_index=True
    )

    # -------------------------
    # DETAIL
    # -------------------------
    st.subheader("Dettaglio")

    if filtered.empty:
        return

    selected_title = st.selectbox("Seleziona call", filtered["Titolo"])
    row = filtered[filtered["Titolo"] == selected_title].iloc[0]

    st.markdown(f"### {row['Titolo']}")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(f"**Programma:** {row['Programma']}")
        st.write(f"**Fonte:** {row['Fonte']}")
        st.write(f"**Call ID:** {row['Call ID']}")
        st.markdown(f"[Apri call]({row['URL']})")

    with col2:
        st.metric("Score", row["Score"])
        st.write(f"**Priorità:** {row['Priority']}")
        st.write(f"**Scadenza:** {row['Scadenza'] or 'N/D'}")

    st.markdown("#### Perché è rilevante")
    for r in row["WhyRelevant"].split(";"):
        if r.strip():
            st.write(f"- {r.strip()}")

if __name__ == "__main__":
    main()