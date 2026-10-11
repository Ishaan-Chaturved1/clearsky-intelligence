import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
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
from app.core.logging import logger
from app.core.config import settings
from app.services.s3_service import S3Service


class JSONRepository(BaseRepository):
    """
    Enterprise-ready JSON repository.
    Persists data in structured JSON documents locally and/or in AWS S3.
    """
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = Path(data_dir or settings.JSON_STORAGE_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.s3 = S3Service()
        self.initialize()

    def initialize(self) -> None:
        """Ensure required JSON files exist and are synced."""
        self._ensure_file("zones.json", default=[])
        self._ensure_file("readings.json", default=[])
        self._ensure_file("decisions.json", default=[])
        self._ensure_file("alerts.json", default=[])
        self._ensure_file("citizen_reports.json", default=[])
        self._ensure_file("rewards.json", default=[])
        self._ensure_file("redemptions.json", default=[])
        logger.info(f"JSONRepository initialized at {self.data_dir} (S3 synced: {self.s3.is_available})")

    def _get_path(self, filename: str) -> Path:
        return self.data_dir / filename

    def _ensure_file(self, filename: str, default: Any):
        file_path = self._get_path(filename)
        # If S3 is available, try pulling from S3 if local is missing
        if not file_path.exists():
            if self.s3.is_available:
                s3_data = self.s3.get_json(f"data/{filename}")
                if s3_data is not None:
                    self._write_local(filename, s3_data)
                    return
            self._write_local(filename, default)

    def _read(self, filename: str) -> Any:
        file_path = self._get_path(filename)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error reading local {filename}: {e}")

        # Fallback to S3
        if self.s3.is_available:
            s3_data = self.s3.get_json(f"data/{filename}")
            if s3_data is not None:
                self._write_local(filename, s3_data)
                return s3_data

        return []

    def _write_local(self, filename: str, data: Any):
        file_path = self._get_path(filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error writing local {filename}: {e}")

    def _write(self, filename: str, data: Any):
        self._write_local(filename, data)
        # Sync to S3 in background if available
        if self.s3.is_available:
            try:
                self.s3.put_json(f"data/{filename}", data)
            except Exception as e:
                logger.warning(f"Failed to sync {filename} to S3: {e}")

    # ==================== Zones ====================
    def save_zone(self, zone: Zone) -> None:
        zones = self._read("zones.json")
        dump = zone.model_dump()
        for idx, z in enumerate(zones):
            if z.get("zone_id") == zone.zone_id:
                zones[idx] = dump
                self._write("zones.json", zones)
                return
        zones.append(dump)
        self._write("zones.json", zones)

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        zones = self._read("zones.json")
        for z in zones:
            if z.get("zone_id") == zone_id:
                return Zone(
                    zone_id=z["zone_id"],
                    name=z["name"],
                    latitude=float(z["latitude"]),
                    longitude=float(z["longitude"]),
                    description=z.get("description", ""),
                    zone_type=z.get("zone_type", "Urban"),
                    nearby_infrastructure=NearbyInfrastructure(**z.get("nearby_infrastructure", {}))
                )
        return None

    def list_zones(self) -> List[Zone]:
        raw_zones = self._read("zones.json")
        return [
            Zone(
                zone_id=z["zone_id"],
                name=z["name"],
                latitude=float(z["latitude"]),
                longitude=float(z["longitude"]),
                description=z.get("description", ""),
                zone_type=z.get("zone_type", "Urban"),
                nearby_infrastructure=NearbyInfrastructure(**z.get("nearby_infrastructure", {}))
            )
            for z in raw_zones
        ]

    # ==================== Readings ====================
    def save_reading(self, reading: EnvironmentalReading) -> None:
        readings = self._read("readings.json")
        readings.append(reading.model_dump())
        # Keep last 5000 readings
        if len(readings) > 5000:
            readings = readings[-5000:]
        self._write("readings.json", readings)

    def get_latest_reading(self, zone_id: str) -> Optional[EnvironmentalReading]:
        readings = self._read("readings.json")
        zone_readings = [r for r in readings if r.get("zone_id") == zone_id]
        if not zone_readings:
            return None
        zone_readings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return EnvironmentalReading(**zone_readings[0])

    def get_reading_history(self, zone_id: str, limit: int = 50) -> List[EnvironmentalReading]:
        readings = self._read("readings.json")
        zone_readings = [r for r in readings if r.get("zone_id") == zone_id]
        zone_readings.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return [EnvironmentalReading(**r) for r in zone_readings[:limit]]

    # ==================== Decisions ====================
    def save_decision(self, decision: DecisionRecord) -> None:
        decisions = self._read("decisions.json")
        decisions.append(decision.model_dump())
        if len(decisions) > 5000:
            decisions = decisions[-5000:]
        self._write("decisions.json", decisions)

    def get_latest_decision(self, zone_id: str) -> Optional[DecisionRecord]:
        decisions = self._read("decisions.json")
        zone_decisions = [d for d in decisions if d.get("zone_id") == zone_id]
        if not zone_decisions:
            return None
        zone_decisions.sort(key=lambda x: x.get("scored_at", ""), reverse=True)
        return DecisionRecord(**zone_decisions[0])

    def list_latest_decisions(self) -> List[DecisionRecord]:
        zones = self.list_zones()
        results = []
        for z in zones:
            latest = self.get_latest_decision(z.zone_id)
            if latest:
                results.append(latest)
        return results

    def get_decision_history(self, zone_id: Optional[str] = None, limit: int = 100) -> List[DecisionRecord]:
        decisions = self._read("decisions.json")
        if zone_id:
            decisions = [d for d in decisions if d.get("zone_id") == zone_id]
        decisions.sort(key=lambda x: x.get("scored_at", ""), reverse=True)
        return [DecisionRecord(**d) for d in decisions[:limit]]

    # ==================== Alerts ====================
    def save_alert(self, alert: AlertRecord) -> None:
        alerts = self._read("alerts.json")
        alerts.append(alert.model_dump())
        if len(alerts) > 500:
            alerts = alerts[-500:]
        self._write("alerts.json", alerts)

    def list_recent_alerts(self, limit: int = 20) -> List[AlertRecord]:
        alerts = self._read("alerts.json")
        alerts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [AlertRecord(**a) for a in alerts[:limit]]

    # ==================== Citizen Reports ====================
    def save_citizen_report(self, report: CitizenReport) -> None:
        reports = self._read("citizen_reports.json")
        dump = report.model_dump()
        for idx, r in enumerate(reports):
            if r.get("report_id") == report.report_id:
                reports[idx] = dump
                self._write("citizen_reports.json", reports)
                return
        reports.insert(0, dump)
        self._write("citizen_reports.json", reports)

    def get_citizen_report(self, report_id: str) -> Optional[CitizenReport]:
        reports = self._read("citizen_reports.json")
        for r in reports:
            if r.get("report_id") == report_id:
                return CitizenReport(**r)
        return None

    def list_citizen_reports(self, limit: int = 50) -> List[CitizenReport]:
        reports = self._read("citizen_reports.json")
        reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [CitizenReport(**r) for r in reports[:limit]]

    def update_citizen_report(self, report: CitizenReport) -> None:
        self.save_citizen_report(report)

    # ==================== Rewards & Eco-Points ====================
    def list_rewards_catalog(self) -> List[RewardItem]:
        rewards = self._read("rewards.json")
        return [RewardItem(**r) for r in rewards]

    def get_citizen_points(self, contact: str) -> Dict[str, Any]:
        reports = self._read("citizen_reports.json")
        redemptions = self._read("redemptions.json")

        citizen_reports = [r for r in reports if r.get("reporter_contact") == contact]
        total_earned = sum(r.get("points_awarded", 0) for r in citizen_reports if r.get("points_awarded", 0) > 0)
        verified_count = sum(1 for r in citizen_reports if r.get("points_awarded", 0) > 0)
        reporter_name = citizen_reports[0].get("reporter_name") if citizen_reports else "Citizen Contributor"

        citizen_redemptions = [red for red in redemptions if red.get("contact") == contact]
        total_spent = sum(red.get("points_spent", 0) for red in citizen_redemptions)

        return {
            "reporter_contact": contact,
            "reporter_name": reporter_name or "Citizen Contributor",
            "total_points": max(0, total_earned - total_spent),
            "lifetime_points": total_earned,
            "verified_reports_count": verified_count,
            "reports": citizen_reports,
            "redeemed_vouchers": citizen_redemptions
        }

    def redeem_reward(self, contact: str, item_id: str) -> Optional[Dict[str, Any]]:
        points_info = self.get_citizen_points(contact)
        available_pts = points_info["total_points"]

        catalog = self.list_rewards_catalog()
        target_item = next((item for item in catalog if item.item_id == item_id), None)
        if not target_item or available_pts < target_item.points_cost:
            return None

        voucher_code = f"CS-{uuid.uuid4().hex[:6].upper()}-{item_id[:4]}"
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        redemption_id = f"RED-{uuid.uuid4().hex[:8]}"

        redemptions = self._read("redemptions.json")
        redemption_entry = {
            "redemption_id": redemption_id,
            "contact": contact,
            "item_id": item_id,
            "voucher_code": voucher_code,
            "redeemed_at": now_iso,
            "points_spent": target_item.points_cost,
            "item_title": target_item.title,
            "sponsor": target_item.sponsor
        }
        redemptions.insert(0, redemption_entry)
        self._write("redemptions.json", redemptions)

        return {
            "success": True,
            "voucher_code": voucher_code,
            "item_title": target_item.title,
            "points_spent": target_item.points_cost,
            "remaining_points": available_pts - target_item.points_cost,
            "instructions": f"Present this code at any {target_item.sponsor} distribution center or partner portal."
        }
