import json
import sqlite3
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.models.domain import (
    Zone,
    EnvironmentalReading,
    DecisionRecord,
    AlertRecord,
    CitizenReport,
    RewardItem,
    ViolationCategory,
    ReportStatus
)
from app.repositories.base import BaseRepository
from app.core.logging import logger

class SQLiteRepository(BaseRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS zones (
                    zone_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    description TEXT,
                    zone_type TEXT,
                    infrastructure_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    reading_id TEXT PRIMARY KEY,
                    zone_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    pm25_json TEXT NOT NULL,
                    pm10_json TEXT NOT NULL,
                    pm_ratio REAL,
                    weather_json TEXT NOT NULL,
                    fire_json TEXT NOT NULL,
                    data_mode TEXT NOT NULL,
                    is_stale INTEGER NOT NULL,
                    FOREIGN KEY(zone_id) REFERENCES zones(zone_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_readings_zone_time ON readings(zone_id, timestamp DESC)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    zone_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    priority INTEGER,
                    confidence TEXT NOT NULL,
                    pollutants_json TEXT NOT NULL,
                    weather_json TEXT NOT NULL,
                    reasons_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    source_status_json TEXT NOT NULL,
                    data_mode TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    scored_at TEXT NOT NULL,
                    FOREIGN KEY(zone_id) REFERENCES zones(zone_id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_zone_time ON decisions(zone_id, scored_at DESC)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    zone_id TEXT NOT NULL,
                    zone_name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    priority INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC)")

            # Citizen Incident Reports Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS citizen_reports (
                    report_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    category TEXT NOT NULL,
                    category_label TEXT NOT NULL,
                    zone_id TEXT,
                    zone_name TEXT,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    location_address TEXT NOT NULL,
                    description TEXT NOT NULL,
                    photo_url TEXT,
                    has_voice_note INTEGER NOT NULL,
                    voice_note_transcript TEXT,
                    reporter_name TEXT NOT NULL,
                    reporter_contact TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    status TEXT NOT NULL,
                    points_awarded INTEGER NOT NULL,
                    evidence_correlation TEXT,
                    verification_notes TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reports_created ON citizen_reports(created_at DESC)")

            # Rewards Catalog Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rewards_catalog (
                    item_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    points_cost INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    sponsor TEXT NOT NULL,
                    in_stock INTEGER NOT NULL,
                    badge_label TEXT
                )
            """)

            # Citizen Redemptions Ledger
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS citizen_redemptions (
                    redemption_id TEXT PRIMARY KEY,
                    contact TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    voucher_code TEXT NOT NULL,
                    redeemed_at TEXT NOT NULL,
                    points_spent INTEGER NOT NULL
                )
            """)
            conn.commit()

            # Seed default rewards catalog if empty
            cursor.execute("SELECT COUNT(*) as count FROM rewards_catalog")
            if cursor.fetchone()["count"] == 0:
                rewards_data = [
                    ("HEPA-ROOM-01", "Certified True HEPA Air Purifier Filter Replacement", "Air Purification", 250, "High-efficiency particulate arrestor capturing 99.97% of fine PM2.5. Compatible with top home purifiers.", "Delhi Clean Air Partner Network", 1, "Popular"),
                    ("N95-PACK-10", "Certified N95 Anti-Pollution Masks (Pack of 10)", "Health & Protection", 80, "Surgical-grade particulate filtering respirator masks for high-smog commutes.", "ClearSky Public Health Fund", 1, "Essential"),
                    ("INDOOR-PLANT-03", "Air-Purifying Green Plant (Areca Palm / Sansevieria)", "Green Living", 120, "NASA Clean Air Study certified natural particulate and VOC absorbing potted indoor plant.", "Urban Forest Initiative NCR", 1, "Eco Living"),
                    ("PM25-SENSOR-MINI", "Pocket Laser PM2.5 Micro-Sensor Device", "Sensors", 500, "Compact optical particle counter syncing real-time micro-climate readings via Bluetooth.", "Quantified Minds Hardware Lab", 1, "Tech Gear"),
                    ("METRO-ECO-PASS", "Delhi Metro Green Commute Pass (₹500 Recharge)", "Transit", 200, "Preloaded smart mobility transit card promoting zero-tailpipe public metro transit across Delhi NCR.", "DMRC Sustainable Transit Alliance", 1, "Commute")
                ]
                cursor.executemany("""
                    INSERT INTO rewards_catalog (item_id, title, category, points_cost, description, sponsor, in_stock, badge_label)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, rewards_data)

            # Seed demo citizen reports if empty
            cursor.execute("SELECT COUNT(*) as count FROM citizen_reports")
            if cursor.fetchone()["count"] == 0:
                demo_reports = [
                    (
                        "REP-2026-101",
                        "2026-10-09T08:15:00Z",
                        "UNCOVERED_CONSTRUCTION",
                        "Uncovered Construction Site",
                        "DL-01",
                        "Anand Vihar",
                        28.647,
                        77.315,
                        "Main Flyover Pillar Site, Anand Vihar Corridor",
                        "Massive dry excavation piles left completely uncovered. Heavy wind blowing particulate plumes across pedestrian footpaths without required water spraying.",
                        "https://images.unsplash.com/photo-1541888946425-d0fbb186156f?auto=format&fit=crop&w=600&q=80",
                        1,
                        "Voice Note (28s): 'Huge dust clouds blowing across the road from uncovered flyover work...'",
                        "Vikram Sharma",
                        "+91 98112 43210",
                        "WHATSAPP",
                        "VERIFIED_VIOLATION",
                        100,
                        "Correlated with proximate 180m Overpass construction site tag and Anand Vihar PM10 surge (385 µg/m³).",
                        "Notice served to site contractor. 100 ClearSky Points awarded to citizen."
                    ),
                    (
                        "REP-2026-102",
                        "2026-10-09T07:40:00Z",
                        "INDUSTRIAL_EMISSION",
                        "Industrial Stack Emissions",
                        "DL-03",
                        "Wazirpur Industrial Area",
                        28.699,
                        77.165,
                        "Block C Metallurgical Foundry, Wazirpur",
                        "Dense black smoke billowing from furnace chimney without electrostatic precipitator scrubber. Strong burning sulfur odor.",
                        "https://images.unsplash.com/photo-1611273426858-450d8e3c9fce?auto=format&fit=crop&w=600&q=80",
                        0,
                        None,
                        "Pooja Malhotra",
                        "+91 98710 99823",
                        "TELEGRAM",
                        "ACTION_DISPATCHED",
                        150,
                        "Correlated with industrial zone cluster; DPCC mobile compliance team dispatched.",
                        "Audit team verified violation. 150 ClearSky Points credited."
                    ),
                    (
                        "REP-2026-103",
                        "2026-10-09T06:20:00Z",
                        "OPEN_WASTE_BURNING",
                        "Open Waste & Biomass Burning",
                        "DL-09",
                        "Mundka Industrial Area",
                        28.683,
                        77.031,
                        "Outer Ring Road vacant plot near Mundka Metro Depot",
                        "Illegal municipal solid waste and rubber scrap burning near perimeter boundary. Acrid smoke spreading toward residential colony.",
                        "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=600&q=80",
                        1,
                        "Voice Note (15s): 'Someone set fire to garbage heaps behind the boundary wall...'",
                        "Arjun Verma",
                        "+91 99580 12345",
                        "EMAIL",
                        "RESOLVED",
                        100,
                        "Correlated with NASA FIRMS active thermal anomaly detection; fire patrol extinguished site.",
                        "Hazard mitigated within 45 minutes. 100 ClearSky Points credited."
                    ),
                    (
                        "REP-2026-104",
                        "2026-10-09T09:05:00Z",
                        "UNPAVED_ROAD_DUST",
                        "Unpaved Road Dust Resuspension",
                        "DL-06",
                        "Punjabi Bagh",
                        28.669,
                        77.126,
                        "Rohtak Road Diversion Service Lane, Punjabi Bagh West",
                        "Heavy commercial multi-axle trucks stirring dense dust clouds along dry unpaved service lane lacking any mechanical sweeping or dust binding.",
                        "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80",
                        0,
                        None,
                        "Sunita Roy",
                        "+91 98101 55432",
                        "WEB",
                        "PENDING_AUDIT",
                        0,
                        "Awaiting secondary satellite and ground patrol confirmation.",
                        "Queued for automated review."
                    )
                ]
                cursor.executemany("""
                    INSERT INTO citizen_reports (
                        report_id, created_at, category, category_label, zone_id, zone_name,
                        latitude, longitude, location_address, description, photo_url,
                        has_voice_note, voice_note_transcript, reporter_name, reporter_contact,
                        channel, status, points_awarded, evidence_correlation, verification_notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, demo_reports)

            conn.commit()
            logger.info(f"SQLite repository initialized with Citizen Reporting Loop at {self.db_path}")

    # Zones
    def save_zone(self, zone: Zone) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO zones (zone_id, name, latitude, longitude, description, zone_type, infrastructure_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                zone.zone_id,
                zone.name,
                zone.latitude,
                zone.longitude,
                zone.description,
                zone.zone_type,
                zone.nearby_infrastructure.model_dump_json()
            ))
            conn.commit()

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM zones WHERE zone_id = ?", (zone_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Zone(
                zone_id=row["zone_id"],
                name=row["name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                description=row["description"],
                zone_type=row["zone_type"],
                nearby_infrastructure=json.loads(row["infrastructure_json"])
            )

    def list_zones(self) -> List[Zone]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM zones ORDER BY zone_id ASC")
            rows = cursor.fetchall()
            return [
                Zone(
                    zone_id=r["zone_id"],
                    name=r["name"],
                    latitude=r["latitude"],
                    longitude=r["longitude"],
                    description=r["description"],
                    zone_type=r["zone_type"],
                    nearby_infrastructure=json.loads(r["infrastructure_json"])
                ) for r in rows
            ]

    # Readings
    def save_reading(self, reading: EnvironmentalReading) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO readings 
                (reading_id, zone_id, timestamp, pm25_json, pm10_json, pm_ratio, weather_json, fire_json, data_mode, is_stale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reading.reading_id,
                reading.zone_id,
                reading.timestamp,
                reading.pm25.model_dump_json(),
                reading.pm10.model_dump_json(),
                reading.pm_ratio,
                reading.weather.model_dump_json(),
                reading.fire_summary.model_dump_json(),
                reading.data_mode.value,
                1 if reading.is_stale else 0
            ))
            conn.commit()

    def get_latest_reading(self, zone_id: str) -> Optional[EnvironmentalReading]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM readings WHERE zone_id = ? ORDER BY timestamp DESC LIMIT 1", (zone_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return EnvironmentalReading(
                reading_id=row["reading_id"],
                zone_id=row["zone_id"],
                timestamp=row["timestamp"],
                pm25=json.loads(row["pm25_json"]),
                pm10=json.loads(row["pm10_json"]),
                pm_ratio=row["pm_ratio"],
                weather=json.loads(row["weather_json"]),
                fire_summary=json.loads(row["fire_json"]),
                data_mode=row["data_mode"],
                is_stale=bool(row["is_stale"])
            )

    def get_reading_history(self, zone_id: str, limit: int = 50) -> List[EnvironmentalReading]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM readings WHERE zone_id = ? ORDER BY timestamp DESC LIMIT ?", (zone_id, limit))
            rows = cursor.fetchall()
            return [
                EnvironmentalReading(
                    reading_id=r["reading_id"],
                    zone_id=r["zone_id"],
                    timestamp=r["timestamp"],
                    pm25=json.loads(r["pm25_json"]),
                    pm10=json.loads(r["pm10_json"]),
                    pm_ratio=r["pm_ratio"],
                    weather=json.loads(r["weather_json"]),
                    fire_summary=json.loads(r["fire_json"]),
                    data_mode=r["data_mode"],
                    is_stale=bool(r["is_stale"])
                ) for r in rows
            ]

    # Decisions
    def save_decision(self, decision: DecisionRecord) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO decisions
                (decision_id, zone_id, decision, priority, confidence, pollutants_json, weather_json, reasons_json, warnings_json, source_status_json, data_mode, observed_at, scored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.decision_id,
                decision.zone_id,
                decision.decision.value,
                decision.priority,
                decision.confidence.value,
                json.dumps({k: v.model_dump() for k, v in decision.pollutants.items()}),
                decision.weather.model_dump_json(),
                json.dumps(decision.reasons),
                json.dumps(decision.warnings),
                json.dumps(decision.source_status),
                decision.data_mode.value,
                decision.observed_at,
                decision.scored_at
            ))
            conn.commit()

    def get_latest_decision(self, zone_id: str) -> Optional[DecisionRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decisions WHERE zone_id = ? ORDER BY scored_at DESC LIMIT 1", (zone_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_decision(row)

    def list_latest_decisions(self) -> List[DecisionRecord]:
        # Distinct latest decision per zone
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.* FROM decisions d
                INNER JOIN (
                    SELECT zone_id, MAX(scored_at) as max_scored
                    FROM decisions
                    GROUP BY zone_id
                ) latest ON d.zone_id = latest.zone_id AND d.scored_at = latest.max_scored
                ORDER BY d.zone_id ASC
            """)
            rows = cursor.fetchall()
            return [self._row_to_decision(r) for r in rows]

    def get_decision_history(self, zone_id: Optional[str] = None, limit: int = 100) -> List[DecisionRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if zone_id:
                cursor.execute("SELECT * FROM decisions WHERE zone_id = ? ORDER BY scored_at DESC LIMIT ?", (zone_id, limit))
            else:
                cursor.execute("SELECT * FROM decisions ORDER BY scored_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_decision(r) for r in rows]

    def _row_to_decision(self, row: sqlite3.Row) -> DecisionRecord:
        return DecisionRecord(
            decision_id=row["decision_id"],
            zone_id=row["zone_id"],
            decision=row["decision"],
            priority=row["priority"],
            confidence=row["confidence"],
            pollutants=json.loads(row["pollutants_json"]),
            weather=json.loads(row["weather_json"]),
            reasons=json.loads(row["reasons_json"]),
            warnings=json.loads(row["warnings_json"]),
            source_status=json.loads(row["source_status_json"]),
            data_mode=row["data_mode"],
            observed_at=row["observed_at"],
            scored_at=row["scored_at"]
        )

    # Alerts
    def save_alert(self, alert: AlertRecord) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO alerts
                (alert_id, zone_id, zone_name, severity, alert_type, message, decision, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_id,
                alert.zone_id,
                alert.zone_name,
                alert.severity,
                alert.alert_type,
                alert.message,
                alert.decision.value,
                alert.priority,
                alert.created_at
            ))
            conn.commit()

    def list_recent_alerts(self, limit: int = 20) -> List[AlertRecord]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [
                AlertRecord(
                    alert_id=r["alert_id"],
                    zone_id=r["zone_id"],
                    zone_name=r["zone_name"],
                    severity=r["severity"],
                    alert_type=r["alert_type"],
                    message=r["message"],
                    decision=r["decision"],
                    priority=r["priority"],
                    created_at=r["created_at"]
                ) for r in rows
            ]

    # Citizen Incident Reports
    def save_citizen_report(self, report: CitizenReport) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO citizen_reports
                (report_id, created_at, category, category_label, zone_id, zone_name,
                 latitude, longitude, location_address, description, photo_url,
                 has_voice_note, voice_note_transcript, reporter_name, reporter_contact,
                 channel, status, points_awarded, evidence_correlation, verification_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_id,
                report.created_at,
                report.category.value if hasattr(report.category, "value") else str(report.category),
                report.category_label,
                report.zone_id,
                report.zone_name,
                report.latitude,
                report.longitude,
                report.location_address,
                report.description,
                report.photo_url,
                1 if report.has_voice_note else 0,
                report.voice_note_transcript,
                report.reporter_name,
                report.reporter_contact,
                report.channel,
                report.status.value if hasattr(report.status, "value") else str(report.status),
                report.points_awarded,
                report.evidence_correlation,
                report.verification_notes
            ))
            conn.commit()

    def get_citizen_report(self, report_id: str) -> Optional[CitizenReport]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM citizen_reports WHERE report_id = ?", (report_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_citizen_report(row)

    def list_citizen_reports(self, limit: int = 50) -> List[CitizenReport]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM citizen_reports ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_citizen_report(r) for r in rows]

    def update_citizen_report(self, report: CitizenReport) -> None:
        self.save_citizen_report(report)

    def _row_to_citizen_report(self, r: sqlite3.Row) -> CitizenReport:
        return CitizenReport(
            report_id=r["report_id"],
            created_at=r["created_at"],
            category=r["category"],
            category_label=r["category_label"],
            zone_id=r["zone_id"],
            zone_name=r["zone_name"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            location_address=r["location_address"],
            description=r["description"],
            photo_url=r["photo_url"],
            has_voice_note=bool(r["has_voice_note"]),
            voice_note_transcript=r["voice_note_transcript"],
            reporter_name=r["reporter_name"],
            reporter_contact=r["reporter_contact"],
            channel=r["channel"],
            status=r["status"],
            points_awarded=r["points_awarded"],
            evidence_correlation=r["evidence_correlation"],
            verification_notes=r["verification_notes"]
        )

    # Rewards & Eco-Points Ledger
    def list_rewards_catalog(self) -> List[RewardItem]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rewards_catalog ORDER BY points_cost ASC")
            rows = cursor.fetchall()
            return [
                RewardItem(
                    item_id=r["item_id"],
                    title=r["title"],
                    category=r["category"],
                    points_cost=r["points_cost"],
                    description=r["description"],
                    sponsor=r["sponsor"],
                    in_stock=bool(r["in_stock"]),
                    badge_label=r["badge_label"]
                ) for r in rows
            ]

    def get_citizen_points(self, contact: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT SUM(points_awarded) as total, COUNT(*) as count, reporter_name
                FROM citizen_reports
                WHERE reporter_contact = ? AND points_awarded > 0
            """, (contact,))
            row = cursor.fetchone()
            total_earned = row["total"] or 0
            verified_count = row["count"] or 0
            name = (row["reporter_name"] if row and row["reporter_name"] else None) or "Citizen Contributor"

            cursor.execute("SELECT SUM(points_spent) as spent FROM citizen_redemptions WHERE contact = ?", (contact,))
            spent_row = cursor.fetchone()
            total_spent = (spent_row["spent"] if spent_row and spent_row["spent"] else 0) or 0

            cursor.execute("SELECT * FROM citizen_reports WHERE reporter_contact = ? ORDER BY created_at DESC", (contact,))
            report_rows = cursor.fetchall()
            reports = [dict(self._row_to_citizen_report(r)) for r in report_rows]

            cursor.execute("SELECT * FROM citizen_redemptions WHERE contact = ? ORDER BY redeemed_at DESC", (contact,))
            redemption_rows = cursor.fetchall()
            redemptions = [dict(r) for r in redemption_rows]

            return {
                "reporter_contact": contact,
                "reporter_name": name,
                "total_points": max(0, total_earned - total_spent),
                "lifetime_points": total_earned,
                "verified_reports_count": verified_count,
                "reports": reports,
                "redeemed_vouchers": redemptions
            }

    def redeem_reward(self, contact: str, item_id: str) -> Optional[Dict[str, Any]]:
        points_info = self.get_citizen_points(contact)
        available_pts = points_info["total_points"]

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rewards_catalog WHERE item_id = ?", (item_id,))
            item_row = cursor.fetchone()
            if not item_row:
                return None
            cost = item_row["points_cost"]
            if available_pts < cost:
                return None

            voucher_code = f"CS-{uuid.uuid4().hex[:6].upper()}-{item_id[:4]}"
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            redemption_id = f"RED-{uuid.uuid4().hex[:8]}"

            cursor.execute("""
                INSERT INTO citizen_redemptions (redemption_id, contact, item_id, voucher_code, redeemed_at, points_spent)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (redemption_id, contact, item_id, voucher_code, now_iso, cost))
            conn.commit()

            return {
                "success": True,
                "voucher_code": voucher_code,
                "item_title": item_row["title"],
                "points_spent": cost,
                "remaining_points": available_pts - cost,
                "instructions": f"Present this code at any {item_row['sponsor']} distribution center or partner portal."
            }

