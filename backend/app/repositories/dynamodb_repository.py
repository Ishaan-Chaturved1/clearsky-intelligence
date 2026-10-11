import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from app.models.domain import (
    Zone,
    EnvironmentalReading,
    DecisionRecord,
    AlertRecord,
    CitizenReport,
    RewardItem,
    NearbyInfrastructure
)
from app.repositories.base import BaseRepository
from app.repositories.json_repository import JSONRepository
from app.core.logging import logger
from app.core.config import settings

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception


class DynamoDBRepository(BaseRepository):
    """
    Production AWS DynamoDB adapter.
    Uses tables:
      - clearsky-zones (PK: zone_id)
      - clearsky-readings (PK: zone_id, SK: timestamp)
      - clearsky-decisions (PK: zone_id, SK: scored_at)
      - clearsky-alerts (PK: alert_type, SK: created_at)
      - clearsky-citizen-reports (PK: report_id)
      - clearsky-rewards (PK: item_id)
      - clearsky-redemptions (PK: redemption_id)
    Falls back gracefully to local JSONRepository if credentials are absent.
    """
    def __init__(self, region_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        self.region_name = region_name or settings.AWS_REGION
        self.endpoint_url = endpoint_url or settings.DYNAMODB_ENDPOINT_URL
        self.dynamodb = None
        self._is_available = False
        self._fallback_repo = None
        self.initialize()

    def initialize(self) -> None:
        if boto3 is None:
            logger.warning("boto3 is not available. DynamoDB adapter disabled, using JSON fallback.")
            self._fallback_repo = JSONRepository()
            return

        try:
            session = boto3.Session(region_name=self.region_name)
            self.dynamodb = session.resource("dynamodb", endpoint_url=self.endpoint_url)
            self.zones_table = self.dynamodb.Table(os.getenv("DYNAMODB_ZONES_TABLE", "clearsky-zones"))
            self.readings_table = self.dynamodb.Table(os.getenv("DYNAMODB_READINGS_TABLE", "clearsky-readings"))
            self.decisions_table = self.dynamodb.Table(os.getenv("DYNAMODB_DECISIONS_TABLE", "clearsky-decisions"))
            self.alerts_table = self.dynamodb.Table(os.getenv("DYNAMODB_ALERTS_TABLE", "clearsky-alerts"))
            self.reports_table = self.dynamodb.Table(os.getenv("DYNAMODB_REPORTS_TABLE", "clearsky-citizen-reports"))
            self.rewards_table = self.dynamodb.Table(os.getenv("DYNAMODB_REWARDS_TABLE", "clearsky-rewards"))
            self.redemptions_table = self.dynamodb.Table(os.getenv("DYNAMODB_REDEMPTIONS_TABLE", "clearsky-redemptions"))
            
            # Simple probe to verify access
            self.zones_table.load()
            self._is_available = True
            logger.info("DynamoDB client connected and verified tables successfully.")
        except Exception as e:
            logger.warning(f"DynamoDB credentials/tables unavailable ({e}). Activating JSON fallback.")
            self._is_available = False
            self._fallback_repo = JSONRepository()

    # ==================== Zones ====================
    def save_zone(self, zone: Zone) -> None:
        if not self._is_available:
            return self._fallback_repo.save_zone(zone)
        item = {
            "zone_id": zone.zone_id,
            "name": zone.name,
            "latitude": str(zone.latitude),
            "longitude": str(zone.longitude),
            "description": zone.description,
            "zone_type": zone.zone_type,
            "nearby_infrastructure": zone.nearby_infrastructure.model_dump()
        }
        self.zones_table.put_item(Item=item)

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        if not self._is_available:
            return self._fallback_repo.get_zone(zone_id)
        res = self.zones_table.get_item(Key={"zone_id": zone_id})
        item = res.get("Item")
        if not item:
            return None
        return Zone(
            zone_id=item["zone_id"],
            name=item["name"],
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            description=item.get("description", ""),
            zone_type=item.get("zone_type", "Urban"),
            nearby_infrastructure=NearbyInfrastructure(**item.get("nearby_infrastructure", {}))
        )

    def list_zones(self) -> List[Zone]:
        if not self._is_available:
            return self._fallback_repo.list_zones()
        res = self.zones_table.scan()
        items = res.get("Items", [])
        return [
            Zone(
                zone_id=item["zone_id"],
                name=item["name"],
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
                description=item.get("description", ""),
                zone_type=item.get("zone_type", "Urban"),
                nearby_infrastructure=NearbyInfrastructure(**item.get("nearby_infrastructure", {}))
            ) for item in items
        ]

    # ==================== Readings ====================
    def save_reading(self, reading: EnvironmentalReading) -> None:
        if not self._is_available:
            return self._fallback_repo.save_reading(reading)
        item = {
            "zone_id": reading.zone_id,
            "timestamp": reading.timestamp,
            "reading_id": reading.reading_id,
            "pm25": reading.pm25.model_dump(),
            "pm10": reading.pm10.model_dump(),
            "pm_ratio": str(reading.pm_ratio) if reading.pm_ratio is not None else None,
            "weather": reading.weather.model_dump(),
            "fire_summary": reading.fire_summary.model_dump(),
            "data_mode": reading.data_mode.value,
            "is_stale": reading.is_stale
        }
        self.readings_table.put_item(Item=item)

    def get_latest_reading(self, zone_id: str) -> Optional[EnvironmentalReading]:
        if not self._is_available:
            return self._fallback_repo.get_latest_reading(zone_id)
        res = self.readings_table.query(
            KeyConditionExpression="zone_id = :zid",
            ExpressionAttributeValues={":zid": zone_id},
            ScanIndexForward=False,
            Limit=1
        )
        items = res.get("Items", [])
        if not items:
            return None
        item = items[0]
        return EnvironmentalReading(
            reading_id=item["reading_id"],
            zone_id=item["zone_id"],
            timestamp=item["timestamp"],
            pm25=item["pm25"],
            pm10=item["pm10"],
            pm_ratio=float(item["pm_ratio"]) if item.get("pm_ratio") is not None else None,
            weather=item["weather"],
            fire_summary=item["fire_summary"],
            data_mode=item["data_mode"],
            is_stale=item["is_stale"]
        )

    def get_reading_history(self, zone_id: str, limit: int = 50) -> List[EnvironmentalReading]:
        if not self._is_available:
            return self._fallback_repo.get_reading_history(zone_id, limit)
        res = self.readings_table.query(
            KeyConditionExpression="zone_id = :zid",
            ExpressionAttributeValues={":zid": zone_id},
            ScanIndexForward=False,
            Limit=limit
        )
        return [
            EnvironmentalReading(
                reading_id=item["reading_id"],
                zone_id=item["zone_id"],
                timestamp=item["timestamp"],
                pm25=item["pm25"],
                pm10=item["pm10"],
                pm_ratio=float(item["pm_ratio"]) if item.get("pm_ratio") is not None else None,
                weather=item["weather"],
                fire_summary=item["fire_summary"],
                data_mode=item["data_mode"],
                is_stale=item["is_stale"]
            ) for item in res.get("Items", [])
        ]

    # ==================== Decisions ====================
    def save_decision(self, decision: DecisionRecord) -> None:
        if not self._is_available:
            return self._fallback_repo.save_decision(decision)
        item = {
            "zone_id": decision.zone_id,
            "scored_at": decision.scored_at,
            "decision_id": decision.decision_id,
            "decision": decision.decision.value,
            "priority": decision.priority,
            "confidence": decision.confidence.value,
            "pollutants": {k: v.model_dump() for k, v in decision.pollutants.items()},
            "weather": decision.weather.model_dump(),
            "reasons": decision.reasons,
            "warnings": decision.warnings,
            "source_status": decision.source_status,
            "data_mode": decision.data_mode.value,
            "observed_at": decision.observed_at
        }
        self.decisions_table.put_item(Item=item)

    def get_latest_decision(self, zone_id: str) -> Optional[DecisionRecord]:
        if not self._is_available:
            return self._fallback_repo.get_latest_decision(zone_id)
        res = self.decisions_table.query(
            KeyConditionExpression="zone_id = :zid",
            ExpressionAttributeValues={":zid": zone_id},
            ScanIndexForward=False,
            Limit=1
        )
        items = res.get("Items", [])
        if not items:
            return None
        item = items[0]
        return DecisionRecord(
            decision_id=item["decision_id"],
            zone_id=item["zone_id"],
            decision=item["decision"],
            priority=item.get("priority"),
            confidence=item["confidence"],
            pollutants=item["pollutants"],
            weather=item["weather"],
            reasons=item["reasons"],
            warnings=item["warnings"],
            source_status=item["source_status"],
            data_mode=item["data_mode"],
            observed_at=item["observed_at"],
            scored_at=item["scored_at"]
        )

    def list_latest_decisions(self) -> List[DecisionRecord]:
        if not self._is_available:
            return self._fallback_repo.list_latest_decisions()
        zones = self.list_zones()
        results = []
        for z in zones:
            latest = self.get_latest_decision(z.zone_id)
            if latest:
                results.append(latest)
        return results

    def get_decision_history(self, zone_id: Optional[str] = None, limit: int = 100) -> List[DecisionRecord]:
        if not self._is_available:
            return self._fallback_repo.get_decision_history(zone_id, limit)
        if zone_id:
            res = self.decisions_table.query(
                KeyConditionExpression="zone_id = :zid",
                ExpressionAttributeValues={":zid": zone_id},
                ScanIndexForward=False,
                Limit=limit
            )
            items = res.get("Items", [])
        else:
            res = self.decisions_table.scan(Limit=limit)
            items = res.get("Items", [])
        return [
            DecisionRecord(
                decision_id=item["decision_id"],
                zone_id=item["zone_id"],
                decision=item["decision"],
                priority=item.get("priority"),
                confidence=item["confidence"],
                pollutants=item["pollutants"],
                weather=item["weather"],
                reasons=item["reasons"],
                warnings=item["warnings"],
                source_status=item["source_status"],
                data_mode=item["data_mode"],
                observed_at=item["observed_at"],
                scored_at=item["scored_at"]
            ) for item in items
        ]

    # ==================== Alerts ====================
    def save_alert(self, alert: AlertRecord) -> None:
        if not self._is_available:
            return self._fallback_repo.save_alert(alert)
        item = {
            "alert_type": alert.alert_type,
            "created_at": alert.created_at,
            "alert_id": alert.alert_id,
            "zone_id": alert.zone_id,
            "zone_name": alert.zone_name,
            "severity": alert.severity,
            "message": alert.message,
            "decision": alert.decision.value,
            "priority": alert.priority
        }
        self.alerts_table.put_item(Item=item)

    def list_recent_alerts(self, limit: int = 20) -> List[AlertRecord]:
        if not self._is_available:
            return self._fallback_repo.list_recent_alerts(limit)
        res = self.alerts_table.scan(Limit=limit)
        items = res.get("Items", [])
        return [
            AlertRecord(
                alert_id=item["alert_id"],
                zone_id=item["zone_id"],
                zone_name=item["zone_name"],
                severity=item["severity"],
                alert_type=item["alert_type"],
                message=item["message"],
                decision=item["decision"],
                priority=item.get("priority"),
                created_at=item["created_at"]
            ) for item in items
        ]

    # ==================== Citizen Reports ====================
    def save_citizen_report(self, report: CitizenReport) -> None:
        if not self._is_available:
            return self._fallback_repo.save_citizen_report(report)
        item = report.model_dump()
        self.reports_table.put_item(Item=item)

    def get_citizen_report(self, report_id: str) -> Optional[CitizenReport]:
        if not self._is_available:
            return self._fallback_repo.get_citizen_report(report_id)
        res = self.reports_table.get_item(Key={"report_id": report_id})
        item = res.get("Item")
        if not item:
            return None
        return CitizenReport(**item)

    def list_citizen_reports(self, limit: int = 50) -> List[CitizenReport]:
        if not self._is_available:
            return self._fallback_repo.list_citizen_reports(limit)
        res = self.reports_table.scan(Limit=limit)
        items = res.get("Items", [])
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [CitizenReport(**i) for i in items[:limit]]

    def update_citizen_report(self, report: CitizenReport) -> None:
        self.save_citizen_report(report)

    # ==================== Rewards & Eco-Points ====================
    def list_rewards_catalog(self) -> List[RewardItem]:
        if not self._is_available:
            return self._fallback_repo.list_rewards_catalog()
        res = self.rewards_table.scan()
        items = res.get("Items", [])
        return [RewardItem(**i) for i in items]

    def get_citizen_points(self, contact: str) -> Dict[str, Any]:
        if not self._is_available:
            return self._fallback_repo.get_citizen_points(contact)
        
        reports_res = self.reports_table.scan(
            FilterExpression="reporter_contact = :c",
            ExpressionAttributeValues={":c": contact}
        )
        reports = reports_res.get("Items", [])
        total_earned = sum(r.get("points_awarded", 0) for r in reports if r.get("points_awarded", 0) > 0)
        verified_count = sum(1 for r in reports if r.get("points_awarded", 0) > 0)
        reporter_name = reports[0].get("reporter_name") if reports else "Citizen Contributor"

        redemptions_res = self.redemptions_table.scan(
            FilterExpression="contact = :c",
            ExpressionAttributeValues={":c": contact}
        )
        redemptions = redemptions_res.get("Items", [])
        total_spent = sum(red.get("points_spent", 0) for red in redemptions)

        return {
            "reporter_contact": contact,
            "reporter_name": reporter_name or "Citizen Contributor",
            "total_points": max(0, total_earned - total_spent),
            "lifetime_points": total_earned,
            "verified_reports_count": verified_count,
            "reports": reports,
            "redeemed_vouchers": redemptions
        }

    def redeem_reward(self, contact: str, item_id: str) -> Optional[Dict[str, Any]]:
        if not self._is_available:
            return self._fallback_repo.redeem_reward(contact, item_id)
        
        points_info = self.get_citizen_points(contact)
        available_pts = points_info["total_points"]

        catalog = self.list_rewards_catalog()
        target_item = next((item for item in catalog if item.item_id == item_id), None)
        if not target_item or available_pts < target_item.points_cost:
            return None

        voucher_code = f"CS-{uuid.uuid4().hex[:6].upper()}-{item_id[:4]}"
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        redemption_id = f"RED-{uuid.uuid4().hex[:8]}"

        entry = {
            "redemption_id": redemption_id,
            "contact": contact,
            "item_id": item_id,
            "voucher_code": voucher_code,
            "redeemed_at": now_iso,
            "points_spent": target_item.points_cost,
            "item_title": target_item.title,
            "sponsor": target_item.sponsor
        }
        self.redemptions_table.put_item(Item=entry)

        return {
            "success": True,
            "voucher_code": voucher_code,
            "item_title": target_item.title,
            "points_spent": target_item.points_cost,
            "remaining_points": available_pts - target_item.points_cost,
            "instructions": f"Present this code at any {target_item.sponsor} distribution center or partner portal."
        }
