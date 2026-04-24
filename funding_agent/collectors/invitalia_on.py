from funding_agent.collectors.invitalia_measure import InvitaliaMeasureCollector


class InvitaliaONCollector(InvitaliaMeasureCollector):
    def __init__(self, timeout: int = 20):
        super().__init__(
            name="invitalia_on",
            call_id="INVITALIA-ON",
            program="ON - Oltre Nuove imprese a tasso zero",
            start_urls=[
                "https://www.invitalia.it/incentivi-e-strumenti/ON-nuove-imprese-tasso-zero",
                "https://www.invitalia.it/incentivi-e-strumenti/nuove-imprese-tasso-zero/cosa-si-puo-fare",
                "https://www.invitalia.it/incentivi-e-strumenti/nuove-imprese-tasso-zero/faq/presentazione-della-domanda",
            ],
            funding_type="contributo a fondo perduto + finanziamento a tasso zero",
            eligible_entities=[
                "imprese a prevalente partecipazione giovanile",
                "imprese a prevalente partecipazione femminile",
                "società costituende",
                "micro e piccole imprese",
            ],
            countries=["Italy"],
            timeout=timeout,
        )