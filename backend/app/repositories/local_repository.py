import json
import sqlite3
import os
from pathlib import Path
from typing import List, Optional
from app.models.domain import Zone, EnvironmentalReading, DecisionRecord, AlertRecord
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
            conn.commit()
            logger.info(f"SQLite repository initialized at {self.db_path}")

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
