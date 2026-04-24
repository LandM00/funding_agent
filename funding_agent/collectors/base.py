from abc import ABC, abstractmethod
from typing import List

from funding_agent.models import FundingCall


class BaseCollector(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self) -> List[FundingCall]:
        raise NotImplementedError