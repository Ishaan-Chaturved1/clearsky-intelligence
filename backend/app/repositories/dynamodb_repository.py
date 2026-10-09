import json
import os
from typing import List, Optional, Any, Dict
from app.models.domain import Zone, EnvironmentalReading, DecisionRecord, AlertRecord
from app.repositories.base import BaseRepository
from app.core.logging import logger

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
    """
    def __init__(self, region_name: str = "us-east-1", endpoint_url: Optional[str] = None):
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.dynamodb = None
        self._is_available = False
        self.initialize()

    def initialize(self) -> None:
        if boto3 is None:
            logger.warning("boto3 is not available. DynamoDB adapter disabled.")
            return

        try:
            session = boto3.Session(region_name=self.region_name)
            self.dynamodb = session.resource("dynamodb", endpoint_url=self.endpoint_url)
            # Check credentials without crashing
            self.zones_table = self.dynamodb.Table(os.getenv("DYNAMODB_ZONES_TABLE", "clearsky-zones"))
            self.readings_table = self.dynamodb.Table(os.getenv("DYNAMODB_READINGS_TABLE", "clearsky-readings"))
            self.decisions_table = self.dynamodb.Table(os.getenv("DYNAMODB_DECISIONS_TABLE", "clearsky-decisions"))
            self.alerts_table = self.dynamodb.Table(os.getenv("DYNAMODB_ALERTS_TABLE", "clearsky-alerts"))
            self._is_available = True
            logger.info("DynamoDB client initialized successfully")
        except (NoCredentialsError, ClientError) as e:
            logger.warning(f"AWS credentials not available for DynamoDB ({e}). Local fallback recommended.")
            self._is_available = False

    def save_zone(self, zone: Zone) -> None:
        if not self._is_available:
            return
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
            return None
        res = self.zones_table.get_item(Key={"zone_id": zone_id})
        item = res.get("Item")
        if not item:
            return None
        return Zone(
            zone_id=item["zone_id"],
            name=item["name"],
            latitude=float(item["latitude"]),
            longitude=float(item["longitude"]),
            description=item["description"],
            zone_type=item["zone_type"],
            nearby_infrastructure=item["nearby_infrastructure"]
        )

    def list_zones(self) -> List[Zone]:
        if not self._is_available:
            return []
        res = self.zones_table.scan()
        items = res.get("Items", [])
        return [
            Zone(
                zone_id=item["zone_id"],
                name=item["name"],
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
                description=item["description"],
                zone_type=item["zone_type"],
                nearby_infrastructure=item["nearby_infrastructure"]
            ) for item in items
        ]

    def save_reading(self, reading: EnvironmentalReading) -> None:
        if not self._is_available:
            return
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
            return None
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
            return []
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

    def save_decision(self, decision: DecisionRecord) -> None:
        if not self._is_available:
            return
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
            return None
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
        # For DynamoDB, query each zone's latest decision
        zones = self.list_zones()
        results = []
        for z in zones:
            latest = self.get_latest_decision(z.zone_id)
            if latest:
                results.append(latest)
        return results

    def get_decision_history(self, zone_id: Optional[str] = None, limit: int = 100) -> List[DecisionRecord]:
        if not self._is_available:
            return []
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

    def save_alert(self, alert: AlertRecord) -> None:
        if not self._is_available:
            return
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
            return []
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
