import os
import yaml


def load_config(path: str = "config.yaml") -> dict:
    config = {}

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    config.setdefault("database", {})
    config["database"]["path"] = os.getenv(
        "DB_PATH",
        config["database"].get("path", "funding_calls.db"),
    )

    config.setdefault("filters", {})
    config["filters"].setdefault("keywords_positive", [])
    config["filters"].setdefault("keywords_negative", [])
    config["filters"].setdefault("preferred_domains", [])

    config.setdefault("email", {})
    config["email"]["enabled"] = os.getenv(
        "EMAIL_ENABLED",
        str(config["email"].get("enabled", False)),
    ).lower() == "true"

    config["email"]["smtp_host"] = os.getenv(
        "SMTP_HOST",
        config["email"].get("smtp_host"),
    )
    config["email"]["smtp_port"] = int(
        os.getenv("SMTP_PORT", config["email"].get("smtp_port", 587))
    )
    config["email"]["smtp_user"] = os.getenv(
        "SMTP_USER",
        config["email"].get("smtp_user"),
    )
    config["email"]["smtp_password"] = os.getenv(
        "SMTP_PASSWORD",
        config["email"].get("smtp_password"),
    )
    config["email"]["from_email"] = os.getenv(
        "FROM_EMAIL",
        config["email"].get("from_email"),
    )

    env_to_emails = os.getenv("TO_EMAILS")
    if env_to_emails:
        config["email"]["to_emails"] = [
            email.strip()
            for email in env_to_emails.split(",")
            if email.strip()
        ]
    else:
        config["email"]["to_emails"] = config["email"].get("to_emails", [])

    config.setdefault("telegram", {})
    config["telegram"].setdefault("enabled", False)
    config["telegram"].setdefault("bot_token", "")
    config["telegram"].setdefault("chat_id", "")

    return config