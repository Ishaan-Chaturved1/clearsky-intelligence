from abc import ABC, abstractmethod
from typing import List, Optional, Any
from app.models.domain import Zone, EnvironmentalReading, DecisionRecord, AlertRecord

class BaseRepository(ABC):
    @abstractmethod
    def initialize(self) -> None:
        pass

    # Zones
    @abstractmethod
    def save_zone(self, zone: Zone) -> None:
        pass

    @abstractmethod
    def get_zone(self, zone_id: str) -> Optional[Zone]:
        pass

    @abstractmethod
    def list_zones(self) -> List[Zone]:
        pass

    # Readings
    @abstractmethod
    def save_reading(self, reading: EnvironmentalReading) -> None:
        pass

    @abstractmethod
    def get_latest_reading(self, zone_id: str) -> Optional[EnvironmentalReading]:
        pass

    @abstractmethod
    def get_reading_history(self, zone_id: str, limit: int = 50) -> List[EnvironmentalReading]:
        pass

    # Decisions
    @abstractmethod
    def save_decision(self, decision: DecisionRecord) -> None:
        pass

    @abstractmethod
    def get_latest_decision(self, zone_id: str) -> Optional[DecisionRecord]:
        pass

    @abstractmethod
    def list_latest_decisions(self) -> List[DecisionRecord]:
        pass

    @abstractmethod
    def get_decision_history(self, zone_id: Optional[str] = None, limit: int = 100) -> List[DecisionRecord]:
        pass

    # Alerts
    @abstractmethod
    def save_alert(self, alert: AlertRecord) -> None:
        pass

    @abstractmethod
    def list_recent_alerts(self, limit: int = 20) -> List[AlertRecord]:
        pass

    # Citizen Reports
    @abstractmethod
    def save_citizen_report(self, report: Any) -> None:
        pass

    @abstractmethod
    def get_citizen_report(self, report_id: str) -> Optional[Any]:
        pass

    @abstractmethod
    def list_citizen_reports(self, limit: int = 50) -> List[Any]:
        pass

    @abstractmethod
    def update_citizen_report(self, report: Any) -> None:
        pass

    # Rewards
    @abstractmethod
    def list_rewards_catalog(self) -> List[Any]:
        pass

    @abstractmethod
    def get_citizen_points(self, contact: str) -> Any:
        pass

    @abstractmethod
    def redeem_reward(self, contact: str, item_id: str) -> Optional[Any]:
        pass

