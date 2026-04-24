import streamlit as st

from funding_agent.config import load_config
from funding_agent.main import run_crawl
from funding_agent.webapp.dashboard import main


@st.cache_data(ttl=3600, show_spinner="Aggiornamento call in corso...")
def refresh_data():
    config = load_config()
    run_crawl(config)
    return True


refresh_data()

if __name__ == "__main__":
    main()