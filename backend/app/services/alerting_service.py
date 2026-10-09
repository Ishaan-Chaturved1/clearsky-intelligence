import time
from typing import Optional, Dict
from datetime import datetime, timezone
from app.models.domain import AlertRecord, DecisionRecord, DecisionType, Zone
from app.repositories.base import BaseRepository
from app.core.logging import logger

class AlertingService:
    def __init__(self, repository: BaseRepository, cooldown_seconds: int = 3600):
        self.repository = repository
        self.cooldown_seconds = cooldown_seconds
        # In-memory tracking of zone_id -> (last_decision, last_alert_time)
        self._last_emitted: Dict[str, float] = {}

    def check_and_emit(
        self,
        zone: Zone,
        current_decision: DecisionRecord,
        previous_decision: Optional[DecisionRecord] = None
    ) -> Optional[AlertRecord]:
        now_ts = time.time()
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        last_alert_time = self._last_emitted.get(zone.zone_id, 0)
        in_cooldown = (now_ts - last_alert_time) < self.cooldown_seconds

        # Condition 1: High Priority Intervention (Priority 4 or 5)
        if current_decision.decision == DecisionType.INTERVENTION_RECOMMENDED and (current_decision.priority or 0) >= 4:
            if not in_cooldown or (previous_decision and previous_decision.decision != DecisionType.INTERVENTION_RECOMMENDED):
                alert = AlertRecord(
                    alert_id=f"ALT-{zone.zone_id}-{int(now_ts)}",
                    zone_id=zone.zone_id,
                    zone_name=zone.name,
                    severity="HIGH",
                    alert_type="HIGH_PRIORITY_INTERVENTION",
                    message=f"Critical dust hotspot: Priority {current_decision.priority} intervention recommended at {zone.name}.",
                    decision=current_decision.decision,
                    priority=current_decision.priority,
                    created_at=now_iso
                )
                self.repository.save_alert(alert)
                self._last_emitted[zone.zone_id] = now_ts
                logger.info(f"Emitted high-priority alert for zone {zone.zone_id}")
                return alert

        # Condition 2: Significant Decision Change (e.g. Recommended -> Not Recommended due to smoke/humidity)
        if previous_decision and previous_decision.decision != current_decision.decision:
            if current_decision.decision == DecisionType.INTERVENTION_NOT_RECOMMENDED and previous_decision.decision == DecisionType.INTERVENTION_RECOMMENDED:
                alert = AlertRecord(
                    alert_id=f"ALT-{zone.zone_id}-{int(now_ts)}",
                    zone_id=zone.zone_id,
                    zone_name=zone.name,
                    severity="MEDIUM",
                    alert_type="DECISION_CHANGE",
                    message=f"Status update at {zone.name}: Intervention ceased due to shifting atmospheric/smoke conditions.",
                    decision=current_decision.decision,
                    priority=current_decision.priority,
                    created_at=now_iso
                )
                self.repository.save_alert(alert)
                self._last_emitted[zone.zone_id] = now_ts
                return alert

        return None
