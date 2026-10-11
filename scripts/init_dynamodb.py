#!/usr/bin/env python3
"""
AWS DynamoDB Table Initialization & Seeding Script for ClearSky Intelligence.
Creates tables if they don't exist and seeds initial data from data/*.json.
"""
import sys
import os
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
for p in (BACKEND_DIR, ROOT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from app.core.config import settings
from app.core.logging import logger
from app.models.domain import Zone, NearbyInfrastructure
from app.repositories.dynamodb_repository import DynamoDBRepository

try:
    import boto3
except ImportError:
    logger.error("boto3 must be installed to run init_dynamodb.py")
    sys.exit(1)


def create_table_if_not_exists(dynamodb, table_name, key_schema, attribute_definitions):
    existing_tables = [t.name for t in dynamodb.tables.all()]
    if table_name in existing_tables:
        print(f"  [✓] Table '{table_name}' already exists.")
        return dynamodb.Table(table_name)

    print(f"  [*] Creating table '{table_name}'...")
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=key_schema,
        AttributeDefinitions=attribute_definitions,
        BillingMode="PAY_PER_REQUEST"
    )
    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
    print(f"  [✓] Table '{table_name}' created successfully.")
    return table


def main():
    print("=" * 60)
    print("  ClearSky Intelligence — DynamoDB Table Setup")
    print(f"  Region: {settings.AWS_REGION}")
    print("=" * 60)

    session = boto3.Session(region_name=settings.AWS_REGION)
    dynamodb = session.resource("dynamodb", endpoint_url=settings.DYNAMODB_ENDPOINT_URL)

    # 1. clearsky-zones (PK: zone_id)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_ZONES_TABLE,
        [{"AttributeName": "zone_id", "KeyType": "HASH"}],
        [{"AttributeName": "zone_id", "AttributeType": "S"}]
    )

    # 2. clearsky-readings (PK: zone_id, SK: timestamp)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_READINGS_TABLE,
        [{"AttributeName": "zone_id", "KeyType": "HASH"}, {"AttributeName": "timestamp", "KeyType": "RANGE"}],
        [{"AttributeName": "zone_id", "AttributeType": "S"}, {"AttributeName": "timestamp", "AttributeType": "S"}]
    )

    # 3. clearsky-decisions (PK: zone_id, SK: scored_at)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_DECISIONS_TABLE,
        [{"AttributeName": "zone_id", "KeyType": "HASH"}, {"AttributeName": "scored_at", "KeyType": "RANGE"}],
        [{"AttributeName": "zone_id", "AttributeType": "S"}, {"AttributeName": "scored_at", "AttributeType": "S"}]
    )

    # 4. clearsky-alerts (PK: alert_type, SK: created_at)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_ALERTS_TABLE,
        [{"AttributeName": "alert_type", "KeyType": "HASH"}, {"AttributeName": "created_at", "KeyType": "RANGE"}],
        [{"AttributeName": "alert_type", "AttributeType": "S"}, {"AttributeName": "created_at", "AttributeType": "S"}]
    )

    # 5. clearsky-citizen-reports (PK: report_id)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_REPORTS_TABLE,
        [{"AttributeName": "report_id", "KeyType": "HASH"}],
        [{"AttributeName": "report_id", "AttributeType": "S"}]
    )

    # 6. clearsky-rewards (PK: item_id)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_REWARDS_TABLE,
        [{"AttributeName": "item_id", "KeyType": "HASH"}],
        [{"AttributeName": "item_id", "AttributeType": "S"}]
    )

    # 7. clearsky-redemptions (PK: redemption_id)
    create_table_if_not_exists(
        dynamodb,
        settings.DYNAMODB_REDEMPTIONS_TABLE,
        [{"AttributeName": "redemption_id", "KeyType": "HASH"}],
        [{"AttributeName": "redemption_id", "AttributeType": "S"}]
    )

    print("\n[*] Seeding initial data into DynamoDB...")
    repo = DynamoDBRepository(region_name=settings.AWS_REGION, endpoint_url=settings.DYNAMODB_ENDPOINT_URL)
    
    # Seed zones from data/zones.json
    zones_path = ROOT_DIR / "data" / "zones.json"
    if zones_path.exists():
        with open(zones_path, "r", encoding="utf-8") as f:
            zones_data = json.load(f)
        for zd in zones_data:
            repo.save_zone(Zone(
                zone_id=zd["zone_id"],
                name=zd["name"],
                latitude=zd["latitude"],
                longitude=zd["longitude"],
                description=zd.get("description", ""),
                zone_type=zd.get("zone_type", "Urban"),
                nearby_infrastructure=NearbyInfrastructure(**zd.get("nearby_infrastructure", {}))
            ))
        print(f"  [✓] Seeded {len(zones_data)} zones into DynamoDB.")

    print("\n[✓] DynamoDB initialization and seeding complete.")


if __name__ == "__main__":
    main()
