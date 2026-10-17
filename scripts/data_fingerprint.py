"""Record or verify checksums of existing database values using read-only queries.

Keep the manifest with your private backups. Verification ignores new columns so
additive migrations can be checked without exposing measurement or account data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from sqlalchemy import create_engine, text

from sports_tracker.settings.settings import settings

TABLES = (
    "users", "user_settings", "muscles", "exercises", "exercise_muscle",
    "sessions", "workout_sets", "measurements",
)


def fingerprints(baseline: dict | None = None) -> dict:
    engine = create_engine(settings.DATABASE_URL)
    isolation = "REPEATABLE READ" if engine.dialect.name == "postgresql" else "SERIALIZABLE"
    result = {}
    with engine.connect().execution_options(isolation_level=isolation) as connection:
        for table in TABLES:
            query = connection.execute(text(f"SELECT * FROM {table}"))
            columns = baseline[table]["columns"] if baseline else sorted(query.keys())
            rows = [{key: row[key] for key in columns} for row in query.mappings()]
            serialized = sorted(json.dumps(row, sort_keys=True, default=str) for row in rows)
            result[table] = {
                "count": len(rows), "columns": columns,
                "sha256": hashlib.sha256(json.dumps(serialized).encode()).hexdigest(),
            }
    engine.dispose()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--record", type=Path, help="Create a new baseline manifest; existing files are preserved")
    group.add_argument("--verify", type=Path, help="Verify against a previously recorded baseline")
    args = parser.parse_args()
    if args.verify:
        baseline = json.loads(args.verify.read_text())
        current = fingerprints(baseline)
        differences = [table for table in TABLES if current[table] != baseline[table]]
        if differences:
            parser.exit(1, "Data differs from baseline in: " + ", ".join(differences) + "\n")
        print("All existing table values match the pre-change baseline.")
    else:
        result = fingerprints()
        with args.record.open("x") as output:
            json.dump(result, output, indent=2)
        args.record.chmod(0o600)
        print("Saved baseline:", {table: value["count"] for table, value in result.items()})


if __name__ == "__main__":
    main()
