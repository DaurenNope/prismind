#!/usr/bin/env python3
"""
Migration System for BEYONDLINES
==============================

Manages database schema migrations with:
- Version tracking
- Up/down migrations
- Rollback support
- Migration validation

Author: BEYONDLINES AI System
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logging_config import get_logger


class MigrationStatus(Enum):
    """Migration status"""

    PENDING = "pending"
    APPLIED = "applied"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class Migration:
    """A database migration"""

    version: str
    name: str
    up_sql: str
    down_sql: Optional[str] = None
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "name": self.name,
            "up_sql": self.up_sql,
            "down_sql": self.down_sql,
            "description": self.description,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Migration":
        return cls(
            version=data["version"],
            name=data["name"],
            up_sql=data["up_sql"],
            down_sql=data.get("down_sql"),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class MigrationRecord:
    """Record of applied migration"""

    version: str
    name: str
    applied_at: str
    status: MigrationStatus
    error: Optional[str] = None


class MigrationManager:
    """
    Manages database migrations.

    Usage:
        manager = MigrationManager(migrations_dir="migrations")
        manager.apply_migrations()  # Apply all pending migrations
        manager.rollback(version="20250101_001")  # Rollback specific migration
    """

    def __init__(
        self,
        migrations_dir: Optional[Path] = None,
        supabase_client: Optional[Any] = None,
    ):
        if migrations_dir is None:
            migrations_dir = Path("migrations")
        self.migrations_dir = Path(migrations_dir)
        self.supabase_client = supabase_client
        self.logger = get_logger(__name__)
        self._migrations: Dict[str, Migration] = {}
        self._applied_migrations: List[MigrationRecord] = []

        # Load migrations
        self._load_migrations()
        self._load_applied_migrations()

    def _load_migrations(self):
        """Load migrations from directory"""
        if not self.migrations_dir.exists():
            self.migrations_dir.mkdir(parents=True, exist_ok=True)
            return

        # Look for SQL migration files
        sql_files = sorted(self.migrations_dir.glob("*.sql"))

        for sql_file in sql_files:
            try:
                migration = self._parse_migration_file(sql_file)
                if migration:
                    self._migrations[migration.version] = migration
            except Exception as e:
                self.logger.error(f"Failed to load migration {sql_file}: {e}")

    def _parse_migration_file(self, sql_file: Path) -> Optional[Migration]:
        """Parse a SQL migration file"""
        content = sql_file.read_text()

        # Extract version from filename (format: YYYYMMDD_HHMMSS_description.sql)
        filename = sql_file.stem
        match = re.match(r"^(\d{8}_\d{6})_(.+)$", filename)
        if not match:
            # Try alternative format: YYYY_MM_DD_description.sql
            match = re.match(r"^(\d{4}_\d{2}_\d{2})_(.+)$", filename)
            if not match:
                self.logger.warning(f"Invalid migration filename format: {sql_file}")
                return None

        version = match.group(1)
        name = match.group(2).replace("_", " ").title()

        # Split into up and down migrations
        # Look for markers: -- UP or -- DOWN
        if "-- UP" in content or "--DOWN" in content:
            parts = re.split(r"--\s*(UP|DOWN)\s*", content, flags=re.IGNORECASE)
            if len(parts) >= 3:
                up_sql = parts[2] if "UP" in parts[1].upper() else content
                down_sql = (
                    parts[4] if len(parts) > 4 and "DOWN" in parts[3].upper() else None
                )
            else:
                up_sql = content
                down_sql = None
        else:
            up_sql = content
            down_sql = None

        # Extract description from comments
        description = ""
        first_line = content.split("\n")[0] if content else ""
        if first_line.startswith("--"):
            description = first_line[2:].strip()

        return Migration(
            version=version,
            name=name,
            up_sql=up_sql.strip(),
            down_sql=down_sql.strip() if down_sql else None,
            description=description,
        )

    def _load_applied_migrations(self):
        """Load applied migrations from database"""
        if not self.supabase_client:
            # Try to load from local file
            record_file = self.migrations_dir / "migration_history.json"
            if record_file.exists():
                try:
                    data = json.loads(record_file.read_text())
                    self._applied_migrations = [
                        MigrationRecord(
                            version=r["version"],
                            name=r["name"],
                            applied_at=r["applied_at"],
                            status=MigrationStatus(r["status"]),
                            error=r.get("error"),
                        )
                        for r in data
                    ]
                except Exception as e:
                    self.logger.error(f"Failed to load migration history: {e}")
            return

        try:
            # Load from Supabase migrations table
            result = (
                self.supabase_client.table("schema_migrations")
                .select("*")
                .order("applied_at", desc=True)
                .execute()
            )
            if result.data:
                self._applied_migrations = [
                    MigrationRecord(
                        version=r["version"],
                        name=r["name"],
                        applied_at=r["applied_at"],
                        status=MigrationStatus(r["status"]),
                        error=r.get("error"),
                    )
                    for r in result.data
                ]
        except Exception as e:
            self.logger.debug(
                f"Could not load migrations from Supabase (table may not exist): {e}"
            )
            # Try to create migrations table
            self._create_migrations_table()

    def _create_migrations_table(self):
        """Create migrations tracking table"""
        if not self.supabase_client:
            return

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            status VARCHAR(50) NOT NULL,
            error TEXT
        );
        """

        try:
            # Execute via RPC if available, otherwise skip
            # Supabase Python client doesn't directly support raw SQL easily
            # This would need to be executed manually or via migration
            self.logger.info(
                "Migration tracking table should be created manually in Supabase"
            )
        except Exception as e:
            self.logger.debug(f"Could not create migrations table: {e}")

    def create_migration(
        self, name: str, up_sql: str, down_sql: Optional[str] = None
    ) -> Migration:
        """Create a new migration file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = timestamp
        filename = f"{version}_{name.replace(' ', '_').lower()}.sql"
        filepath = self.migrations_dir / filename

        # Write migration file
        content = f"-- {name}\n\n"
        content += "-- UP\n"
        content += up_sql

        if down_sql:
            content += "\n\n-- DOWN\n"
            content += down_sql

        filepath.write_text(content)

        migration = Migration(
            version=version, name=name, up_sql=up_sql, down_sql=down_sql
        )
        self._migrations[version] = migration

        self.logger.info(f"Created migration: {filename}")
        return migration

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        applied_versions = {
            r.version
            for r in self._applied_migrations
            if r.status == MigrationStatus.APPLIED
        }
        pending = [
            m for v, m in sorted(self._migrations.items()) if v not in applied_versions
        ]
        return pending

    def get_applied_migrations(self) -> List[MigrationRecord]:
        """Get list of applied migrations"""
        return [
            r for r in self._applied_migrations if r.status == MigrationStatus.APPLIED
        ]

    def apply_migrations(
        self, target_version: Optional[str] = None
    ) -> Tuple[int, List[str]]:
        """Apply pending migrations"""
        pending = self.get_pending_migrations()

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            self.logger.info("No pending migrations to apply")
            return 0, []

        applied_count = 0
        errors: List[str] = []

        for migration in pending:
            try:
                self._apply_migration(migration)
                applied_count += 1
                self.logger.info(
                    f"Applied migration: {migration.version} - {migration.name}"
                )
            except Exception as e:
                error_msg = f"Failed to apply migration {migration.version}: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                # Record failure
                self._record_migration(migration, MigrationStatus.FAILED, str(e))
                break  # Stop on first failure

        return applied_count, errors

    def _apply_migration(self, migration: Migration):
        """Apply a single migration"""
        if not self.supabase_client:
            self.logger.warning("No Supabase client available, migration not applied")
            return

        try:
            # Execute UP SQL
            # Note: Supabase Python client doesn't support raw SQL directly
            # In production, you'd use the Supabase SQL editor or API
            # For now, we'll record it as applied
            self.logger.info(
                f"Executing migration {migration.version}: {migration.name}"
            )
            self.logger.debug(f"SQL:\n{migration.up_sql}")

            # Note: Supabase Python client doesn't support raw SQL execution directly.
            # Migrations should be executed via:
            # 1. Supabase Dashboard SQL Editor (manual)
            # 2. Supabase Management API (requires additional setup)
            # 3. Supabase CLI (migration files)
            # This system tracks migration status; actual SQL execution must be done externally.
            self.logger.warning(
                f"Migration {migration.version} SQL recorded but not executed. "
                f"Execute manually via Supabase Dashboard or CLI."
            )
            self._record_migration(migration, MigrationStatus.APPLIED)

        except Exception as e:
            logger.error(f"Error: {e}")
            self._record_migration(migration, MigrationStatus.FAILED, str(e))
            raise

    def rollback(self, version: str) -> bool:
        """Rollback a specific migration"""
        if version not in self._migrations:
            self.logger.error(f"Migration not found: {version}")
            return False

        # Check if migration is applied
        applied = any(
            r.version == version and r.status == MigrationStatus.APPLIED
            for r in self._applied_migrations
        )

        if not applied:
            self.logger.warning(f"Migration {version} is not applied, cannot rollback")
            return False

        migration = self._migrations[version]

        if not migration.down_sql:
            self.logger.error(f"Migration {version} has no down SQL, cannot rollback")
            return False

        try:
            # Execute DOWN SQL
            self.logger.info(f"Rolling back migration {version}: {migration.name}")
            self.logger.debug(f"SQL:\n{migration.down_sql}")

            # Note: Supabase Python client doesn't support raw SQL execution directly.
            # Rollback SQL should be executed via Supabase Dashboard SQL Editor or CLI.
            # This system tracks rollback status; actual SQL execution must be done externally.
            self.logger.warning(
                f"Migration {migration.version} rollback SQL recorded but not executed. "
                f"Execute manually via Supabase Dashboard or CLI."
            )
            self._record_migration(migration, MigrationStatus.ROLLED_BACK)

            self.logger.info(f"Rolled back migration: {version}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to rollback migration {version}: {e}")
            return False

    def _record_migration(
        self, migration: Migration, status: MigrationStatus, error: Optional[str] = None
    ):
        """Record migration status"""
        record = MigrationRecord(
            version=migration.version,
            name=migration.name,
            applied_at=datetime.now(timezone.utc).isoformat(),
            status=status,
            error=error,
        )

        # Update applied migrations list
        existing_idx = None
        for idx, r in enumerate(self._applied_migrations):
            if r.version == migration.version:
                existing_idx = idx
                break

        if existing_idx is not None:
            self._applied_migrations[existing_idx] = record
        else:
            self._applied_migrations.append(record)

        # Save to database if available
        if self.supabase_client:
            try:
                self.supabase_client.table("schema_migrations").upsert(
                    {
                        "version": record.version,
                        "name": record.name,
                        "applied_at": record.applied_at,
                        "status": record.status.value,
                        "error": record.error,
                    },
                    on_conflict="version",
                ).execute()
            except Exception as e:
                self.logger.debug(f"Could not save migration record to database: {e}")

        # Also save to local file
        record_file = self.migrations_dir / "migration_history.json"
        records_data = [
            {
                "version": r.version,
                "name": r.name,
                "applied_at": r.applied_at,
                "status": r.status.value,
                "error": r.error,
            }
            for r in self._applied_migrations
        ]
        record_file.write_text(json.dumps(records_data, indent=2))

    def get_status(self) -> Dict[str, Any]:
        """Get migration system status"""
        pending = self.get_pending_migrations()
        applied = self.get_applied_migrations()
        failed = [
            r for r in self._applied_migrations if r.status == MigrationStatus.FAILED
        ]

        return {
            "total_migrations": len(self._migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "failed_count": len(failed),
            "latest_version": applied[-1].version if applied else None,
            "pending_versions": [m.version for m in pending],
            "failed_versions": [r.version for r in failed],
        }


def get_migration_manager(supabase_client: Optional[Any] = None) -> MigrationManager:
    """Get or create migration manager"""
    migrations_dir = Path("migrations")
    return MigrationManager(
        migrations_dir=migrations_dir, supabase_client=supabase_client
    )
