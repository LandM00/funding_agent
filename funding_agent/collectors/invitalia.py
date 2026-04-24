from funding_agent.collectors.invitalia_measure import InvitaliaMeasureCollector


class InvitaliaCollector(InvitaliaMeasureCollector):
    def __init__(self, timeout: int = 20):
        super().__init__(
            name="invitalia",
            call_id="INVITALIA-SMARTSTART",
            program="Smart&Start Italia",
            start_urls=[
                "https://www.invitalia.it/incentivi-e-strumenti/smartstart-italia",
                "https://www.invitalia.it/incentivi-e-strumenti/smartstart-italia/cosa-finanzia",
                "https://www.invitalia.it/incentivi-e-strumenti/smartstart-italia/agevolazioni",
                "https://www.invitalia.it/incentivi-e-strumenti/smartstart-italia/chi-si-rivolge",
                "https://www.invitalia.it/incentivi-e-strumenti/smartstart-italia/presenta-la-domanda/come-presentare-la-domanda",
            ],
            funding_type="agevolazione / finanziamento agevolato",
            eligible_entities=[
                "startup innovative",
                "team di persone",
                "micro e piccole imprese innovative",
            ],
            countries=["Italy"],
            timeout=timeout,
        )