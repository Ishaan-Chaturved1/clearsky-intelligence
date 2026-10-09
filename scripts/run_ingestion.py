import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.repositories.local_repository import SQLiteRepository
from app.services.ingestion_service import IngestionService

async def main():
    print("=" * 60)
    print("ClearSky Intelligence — Manual CLI Ingestion & Scoring Cycle")
    print(f"Target Database: {settings.SQLITE_DB_PATH}")
    print("=" * 60)

    repo = SQLiteRepository(settings.SQLITE_DB_PATH)
    ingestion = IngestionService(repo)

    print("Executing full ingestion cycle across all configured zones...")
    decisions = await ingestion.run_full_cycle()

    print(f"\nCycle Complete! Scored {len(decisions)} zones:")
    print("-" * 60)
    for d in decisions:
        p_str = f"P{d.priority}" if d.priority else "N/A"
        print(f"[{d.zone_id:12}] {d.decision.value:28} {p_str:4} ({d.confidence.value}) - Mode: {d.data_mode.value}")
        if d.reasons:
            print(f"  -> Rationale: {d.reasons[0]}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
