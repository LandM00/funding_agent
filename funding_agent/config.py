import os
import yaml


def _get_streamlit_secret(key: str, default=None):
    """
    Legge secrets da Streamlit Cloud, se disponibili.
    In locale o in GitHub Actions, se Streamlit non è disponibile,
    ritorna il default.
    """
    try:
        import streamlit as st

        value = st.secrets.get(key, default)
        return value
    except Exception:
        return default


def _get_setting(key: str, default=None):
    """
    Priorità:
    1. Variabile ambiente
    2. Streamlit secrets
    3. config.yaml / default
    """
    env_value = os.getenv(key)

    if env_value not in [None, ""]:
        return env_value

    secret_value = _get_streamlit_secret(key, None)

    if secret_value not in [None, ""]:
        return secret_value

    return default


def _parse_bool(value, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"true", "1", "yes", "y", "on"}


def _parse_email_list(value):
    if not value:
        return []

    if isinstance(value, list):
        return [str(email).strip() for email in value if str(email).strip()]

    return [
        email.strip()
        for email in str(value).split(",")
        if email.strip()
    ]


def load_config(path: str = "config.yaml") -> dict:
    config = {}

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # ------------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------------
    config.setdefault("database", {})

    database_url = _get_setting("DATABASE_URL")

    if database_url:
        config["database"]["backend"] = "postgres"
        config["database"]["url"] = database_url
        config["database"]["path"] = database_url
    else:
        config["database"]["backend"] = "sqlite"
        config["database"]["url"] = None
        config["database"]["path"] = _get_setting(
            "DB_PATH",
            config["database"].get("path", "funding_calls.db"),
        )

    # ------------------------------------------------------------------
    # FILTERS
    # ------------------------------------------------------------------
    config.setdefault("filters", {})
    config["filters"].setdefault("keywords_positive", [])
    config["filters"].setdefault("keywords_negative", [])
    config["filters"].setdefault("preferred_domains", [])

    # ------------------------------------------------------------------
    # PROJECT PROFILE
    # ------------------------------------------------------------------
    config.setdefault("project_profile", {})
    config["project_profile"].setdefault("name", "NEX / Neura GrowTech")
    config["project_profile"].setdefault("type", "startup_spinoff")
    config["project_profile"].setdefault("objective", "")
    config["project_profile"].setdefault("target_applicant", [])
    config["project_profile"].setdefault("project_goals", [])

    config["project_profile"].setdefault("keywords", {})
    config["project_profile"]["keywords"].setdefault("high", [])
    config["project_profile"]["keywords"].setdefault("medium", [])
    config["project_profile"]["keywords"].setdefault("low", [])

    config["project_profile"].setdefault("secondary_domains", [])
    config["project_profile"].setdefault("weak_negative_domains", [])
    config["project_profile"].setdefault("hard_negative_domains", [])
    config["project_profile"].setdefault("excluded_intents", [])

    # ------------------------------------------------------------------
    # EMAIL
    # ------------------------------------------------------------------
    config.setdefault("email", {})

    config["email"]["enabled"] = _parse_bool(
        _get_setting(
            "EMAIL_ENABLED",
            config["email"].get("enabled", False),
        )
    )

    config["email"]["smtp_host"] = _get_setting(
        "SMTP_HOST",
        config["email"].get("smtp_host", "smtp.gmail.com"),
    )

    config["email"]["smtp_port"] = int(
        _get_setting(
            "SMTP_PORT",
            config["email"].get("smtp_port", 587),
        )
    )

    config["email"]["smtp_user"] = _get_setting(
        "SMTP_USER",
        config["email"].get("smtp_user", ""),
    )

    config["email"]["smtp_password"] = _get_setting(
        "SMTP_PASSWORD",
        config["email"].get("smtp_password", ""),
    )

    config["email"]["from_email"] = _get_setting(
        "FROM_EMAIL",
        config["email"].get("from_email", ""),
    )

    to_emails_value = _get_setting(
        "TO_EMAILS",
        config["email"].get("to_emails", []),
    )

    config["email"]["to_emails"] = _parse_email_list(to_emails_value)

    # ------------------------------------------------------------------
    # TELEGRAM
    # ------------------------------------------------------------------
    config.setdefault("telegram", {})
    config["telegram"].setdefault("enabled", False)
    config["telegram"].setdefault("bot_token", "")
    config["telegram"].setdefault("chat_id", "")

    return config