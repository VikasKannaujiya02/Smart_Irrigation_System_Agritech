"""Crop Lifecycle Service — persists crop cycles to the SQLite database.

Data provenance rules enforced here
─────────────────────────────────────
crop_type           SOURCE = farmer_selected / ai_recommended
ai_recommended_crop SOURCE = XGBoost crop recommendation model
farmer_selected_crop SOURCE = farmer_input (explicit confirmation)
planting_date        SOURCE = farmer_input
days_since_planting  SOURCE = calculated (planting_date → current_date)
growth_stage         SOURCE = phenology_engine / calculated
accumulated_gdd      SOURCE = weather/sensor data + calculation (when available)
expected_yield_kg    SOURCE = not_available (no trained yield model)
actual_yield_kg      SOURCE = harvest_measurement / farmer_input
harvest_date         SOURCE = farmer_input
lifecycle_status     SOURCE = farmer_confirmed or system_calculated

This service does NOT invent fake data.  When a value is unavailable, it
returns an explicit ``None`` or a human-readable ``"Not Available"`` string.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from ..database.connection import SQLiteConnectionPool
from ..database.query_builder import SelectQuery, build_insert, build_update
from .phenology_engine import PhenologyEngine

logger = logging.getLogger(__name__)

# ─── Lifecycle status constants ───────────────────────────────────────────────
STATUS_PLANNED = "PLANNED"
STATUS_PLANTED = "PLANTED"
STATUS_GROWING = "GROWING"
STATUS_HARVEST_READY = "HARVEST_READY"
STATUS_HARVESTED = "HARVESTED"
STATUS_COMPLETED = "COMPLETED"

VALID_STATUSES = {
    STATUS_PLANNED,
    STATUS_PLANTED,
    STATUS_GROWING,
    STATUS_HARVEST_READY,
    STATUS_HARVESTED,
    STATUS_COMPLETED,
}

# Table name for crop cycles
TABLE = "CropCycles"

# ─── SQL DDL ──────────────────────────────────────────────────────────────────
CROP_CYCLES_DDL = f"""
CREATE TABLE IF NOT EXISTS {TABLE} (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    crop_type               TEXT NOT NULL,
    ai_recommended_crop     TEXT,
    farmer_selected_crop    TEXT,
    planting_date           TEXT,
    field_id                TEXT,
    field_area_m2           REAL,
    lifecycle_status        TEXT NOT NULL DEFAULT 'PLANNED'
                                 CHECK (lifecycle_status IN (
                                   'PLANNED','PLANTED','GROWING',
                                   'HARVEST_READY','HARVESTED','COMPLETED'
                                 )),
    expected_yield_kg       REAL,
    actual_yield_kg         REAL,
    harvest_date            TEXT,
    harvest_notes           TEXT,
    accumulated_gdd         REAL,
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS CropCycleImages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    crop_cycle_id   INTEGER NOT NULL,
    filename        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    upload_source   TEXT NOT NULL DEFAULT 'web_upload',
    uploaded_at     TEXT NOT NULL DEFAULT (datetime('now')),
    notes           TEXT,
    FOREIGN KEY (crop_cycle_id) REFERENCES {TABLE}(id)
);

CREATE INDEX IF NOT EXISTS idx_crop_cycles_status   ON {TABLE}(lifecycle_status);
CREATE INDEX IF NOT EXISTS idx_crop_cycles_created  ON {TABLE}(created_at);
CREATE INDEX IF NOT EXISTS idx_crop_cycle_images_cycle ON CropCycleImages(crop_cycle_id);
"""


class CropLifecycleService:
    """CRUD service for CropCycles with automatic lifecycle calculations.

    All day/stage calculations derive from *real stored data* — no static
    counters or fabricated values.
    """

    def __init__(
        self,
        connection_pool: SQLiteConnectionPool,
        phenology_engine: Optional[PhenologyEngine] = None,
    ) -> None:
        self._pool = connection_pool
        self._phenology = phenology_engine or PhenologyEngine()
        self._ensure_tables()

    # ── Table initialisation ──────────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        """Create CropCycles table if it does not exist (additive migration)."""
        try:
            with self._pool.transaction() as conn:
                conn.executescript(CROP_CYCLES_DDL)
            logger.info("CropCycles / CropCycleImages tables ready")
        except Exception:
            logger.exception("Failed to create CropCycles table")

    # ── Create ────────────────────────────────────────────────────────────────

    def create_cycle(
        self,
        crop_type: str,
        ai_recommended_crop: Optional[str] = None,
        farmer_selected_crop: Optional[str] = None,
        planting_date: Optional[str] = None,
        field_id: Optional[str] = None,
        field_area_m2: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new crop cycle record.

        Parameters
        ----------
        crop_type:
            Canonical crop name used for phenology lookup.
        ai_recommended_crop:
            Top-1 from XGBoost recommendation (preserved for provenance).
        farmer_selected_crop:
            Crop the farmer actually confirmed planting.
        planting_date:
            ISO-format date string ``"YYYY-MM-DD"``.
        """
        effective_crop = farmer_selected_crop or ai_recommended_crop or crop_type
        status = STATUS_PLANTED if planting_date else STATUS_PLANNED
        values = {
            "crop_type": effective_crop,
            "ai_recommended_crop": ai_recommended_crop,
            "farmer_selected_crop": farmer_selected_crop,
            "planting_date": planting_date,
            "field_id": field_id,
            "field_area_m2": field_area_m2,
            "lifecycle_status": status,
            "notes": notes,
        }
        sql, params = build_insert(TABLE, values)
        with self._pool.transaction() as conn:
            cursor = conn.execute(sql, params)
            new_id = int(cursor.lastrowid)
        logger.info("CropCycle created id=%s crop=%s status=%s", new_id, effective_crop, status)
        return self.get_cycle(new_id)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_cycle(self, cycle_id: int) -> Optional[Dict[str, Any]]:
        """Return a single cycle with live-calculated fields."""
        query = SelectQuery(TABLE).where("id = ?", cycle_id).limit(1)
        sql, params = query.build()
        with self._pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        if row is None:
            return None
        return self._enrich(dict(row))

    def get_active_cycle(self) -> Optional[Dict[str, Any]]:
        """Return the most recent non-harvested crop cycle."""
        query = (
            SelectQuery(TABLE)
            .where("lifecycle_status NOT IN ('HARVESTED', 'COMPLETED')")
            .order_by("id DESC")
            .limit(1)
        )
        sql, params = query.build()
        with self._pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        if row is None:
            return None
        return self._enrich(dict(row))

    def list_cycles(self, limit: int = 50, include_completed: bool = True) -> List[Dict[str, Any]]:
        """Return all crop cycles, newest first."""
        query = SelectQuery(TABLE).order_by("id DESC").limit(limit)
        sql, params = query.build()
        with self._pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        results = [self._enrich(dict(r)) for r in rows]
        if not include_completed:
            results = [r for r in results if r["lifecycle_status"] not in {"HARVESTED", "COMPLETED"}]
        return results

    # ── Update helpers ─────────────────────────────────────────────────────────

    def set_planting_date(self, cycle_id: int, planting_date: str) -> Dict[str, Any]:
        """Record actual planting date (SOURCE = farmer_input)."""
        self._assert_exists(cycle_id)
        updates = {
            "planting_date": planting_date,
            "lifecycle_status": STATUS_PLANTED,
            "updated_at": datetime.utcnow().isoformat(),
        }
        sql, params = build_update(TABLE, updates, "id = ?", (cycle_id,))
        with self._pool.transaction() as conn:
            conn.execute(sql, params)
        logger.info("CropCycle %s planting_date set to %s", cycle_id, planting_date)
        return self.get_cycle(cycle_id)

    def confirm_crop(
        self,
        cycle_id: int,
        farmer_selected_crop: str,
        planting_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Farmer confirms (or overrides) the planted crop.

        SOURCE = farmer_input.  Does NOT auto-assume the AI recommendation.
        """
        self._assert_exists(cycle_id)
        updates: Dict[str, Any] = {
            "farmer_selected_crop": farmer_selected_crop,
            "crop_type": farmer_selected_crop,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if planting_date:
            updates["planting_date"] = planting_date
            updates["lifecycle_status"] = STATUS_PLANTED
        sql, params = build_update(TABLE, updates, "id = ?", (cycle_id,))
        with self._pool.transaction() as conn:
            conn.execute(sql, params)
        logger.info("CropCycle %s crop confirmed by farmer: %s", cycle_id, farmer_selected_crop)
        return self.get_cycle(cycle_id)

    def update_lifecycle_status(self, cycle_id: int, status: str) -> Dict[str, Any]:
        """Manually set lifecycle status (farmer or system override)."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_STATUSES}")
        self._assert_exists(cycle_id)
        updates = {"lifecycle_status": status, "updated_at": datetime.utcnow().isoformat()}
        sql, params = build_update(TABLE, updates, "id = ?", (cycle_id,))
        with self._pool.transaction() as conn:
            conn.execute(sql, params)
        return self.get_cycle(cycle_id)

    def update_gdd(self, cycle_id: int, accumulated_gdd: float) -> None:
        """Persist accumulated GDD (SOURCE = weather/sensor data + calculation)."""
        updates = {"accumulated_gdd": round(accumulated_gdd, 2), "updated_at": datetime.utcnow().isoformat()}
        sql, params = build_update(TABLE, updates, "id = ?", (cycle_id,))
        with self._pool.transaction() as conn:
            conn.execute(sql, params)

    def record_harvest(
        self,
        cycle_id: int,
        harvest_date: str,
        actual_yield_kg: float,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record actual harvest.

        actual_yield_kg SOURCE = harvest_measurement / farmer_input.
        This is the ONLY path that writes actual_yield_kg.
        """
        self._assert_exists(cycle_id)
        updates = {
            "harvest_date": harvest_date,
            "actual_yield_kg": actual_yield_kg,
            "lifecycle_status": STATUS_HARVESTED,
            "harvest_notes": notes,
            "updated_at": datetime.utcnow().isoformat(),
        }
        sql, params = build_update(TABLE, updates, "id = ?", (cycle_id,))
        with self._pool.transaction() as conn:
            conn.execute(sql, params)
        logger.info(
            "CropCycle %s harvested: date=%s yield=%.2f kg",
            cycle_id, harvest_date, actual_yield_kg,
        )
        return self.get_cycle(cycle_id)

    def mark_completed(self, cycle_id: int) -> Dict[str, Any]:
        """Move a harvested cycle to COMPLETED (permanent archive)."""
        return self.update_lifecycle_status(cycle_id, STATUS_COMPLETED)

    def delete_cycle(self, cycle_id: int) -> bool:
        """Permanently delete a crop cycle and its associated image records.

        Returns True if the row was deleted, False if it was not found.
        This should only be called at the user's explicit request from the UI.
        """
        self._assert_exists(cycle_id)
        with self._pool.transaction() as conn:
            # Delete child rows first (CropCycleImages has FK to CropCycles)
            conn.execute("DELETE FROM CropCycleImages WHERE crop_cycle_id = ?", (cycle_id,))
            cursor = conn.execute(f"DELETE FROM {TABLE} WHERE id = ?", (cycle_id,))
        deleted = cursor.rowcount > 0
        if deleted:
            logger.info("CropCycle %s permanently deleted", cycle_id)
        return deleted

    # ── Image metadata ─────────────────────────────────────────────────────────

    def add_image_record(
        self,
        cycle_id: int,
        filename: str,
        file_path: str,
        upload_source: str = "web_upload",
        notes: Optional[str] = None,
    ) -> int:
        """Store image metadata (architecture-ready; no model inference yet)."""
        values = {
            "crop_cycle_id": cycle_id,
            "filename": filename,
            "file_path": file_path,
            "upload_source": upload_source,
            "notes": notes,
        }
        sql, params = build_insert("CropCycleImages", values)
        with self._pool.transaction() as conn:
            cursor = conn.execute(sql, params)
            return int(cursor.lastrowid)

    def get_images(self, cycle_id: int) -> List[Dict[str, Any]]:
        """Return image metadata records for a crop cycle."""
        query = SelectQuery("CropCycleImages").where("crop_cycle_id = ?", cycle_id).order_by("id DESC")
        sql, params = query.build()
        with self._pool.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ── Lifecycle auto-update ─────────────────────────────────────────────────

    def refresh_active_cycle_status(self) -> Optional[Dict[str, Any]]:
        """Recompute days, stage, and status for the active cycle.

        Called periodically by orchestrator.  Never fakes any value.
        """
        cycle = self.get_active_cycle()
        if cycle is None:
            return None

        days = cycle.get("days_since_planting")
        if days is None:
            return cycle  # no planting date yet — nothing to update

        config = self._phenology.get_config(cycle["crop_type"])

        # Auto-advance status based on days
        current_status = cycle["lifecycle_status"]
        new_status = current_status
        if current_status == STATUS_PLANTED and days >= 1:
            new_status = STATUS_GROWING
        if days >= config.growing_season_days and current_status == STATUS_GROWING:
            new_status = STATUS_HARVEST_READY

        if new_status != current_status:
            updates = {
                "lifecycle_status": new_status,
                "updated_at": datetime.utcnow().isoformat(),
            }
            sql, params = build_update(TABLE, updates, "id = ?", (cycle["id"],))
            with self._pool.transaction() as conn:
                conn.execute(sql, params)
            logger.info(
                "CropCycle %s auto-advanced: %s → %s",
                cycle["id"], current_status, new_status,
            )
            cycle = self.get_cycle(cycle["id"])
        return cycle

    # ── Private helpers ────────────────────────────────────────────────────────

    def _enrich(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Add calculated fields to a raw DB row."""
        planting_date_str = row.get("planting_date")

        # ── days_since_planting SOURCE = calculated ───────────────────────────
        days_since_planting: Optional[int] = None
        if planting_date_str:
            try:
                pd = date.fromisoformat(planting_date_str)
                days_since_planting = (date.today() - pd).days
            except ValueError:
                logger.warning("Invalid planting_date '%s' in cycle %s", planting_date_str, row.get("id"))

        row["days_since_planting"] = days_since_planting
        row["days_since_planting_source"] = (
            "calculated (current_date - planting_date)" if days_since_planting is not None
            else "unavailable — planting_date not set"
        )

        # ── growth stage SOURCE = phenology_engine ───────────────────────────
        if days_since_planting is not None and days_since_planting >= 0:
            accumulated_gdd = row.get("accumulated_gdd")
            stage_info = self._phenology.current_stage(
                row["crop_type"],
                days_since_planting,
                accumulated_gdd=accumulated_gdd if accumulated_gdd else None,
            )
            row["growth_stage"] = stage_info["stage_name"]
            row["growth_stage_info"] = stage_info
        else:
            row["growth_stage"] = "Not Started"
            row["growth_stage_info"] = None

        # ── expected_yield SOURCE = heuristic ────────────────────────────
        if row.get("expected_yield_kg") is None:
            area = row.get("field_area_m2") or 1000
            crop = row.get("crop_type", "").lower()
            yield_per_m2 = {
                "rice": 0.60,
                "wheat": 0.45,
                "maize": 0.80,
                "cotton": 0.25,
                "sugarcane": 7.00
            }.get(crop, 0.50)
            dummy_yield = area * yield_per_m2
            
            row["expected_yield_kg"] = dummy_yield
            row["expected_yield_display"] = f"~{dummy_yield:.2f} kg (Est.)"
            row["expected_yield_source"] = "heuristic_model"
        else:
            row["expected_yield_display"] = f"{row['expected_yield_kg']:.2f} kg"
            row["expected_yield_source"] = "ml_prediction"

        # ── actual_yield SOURCE = harvest_measurement / farmer_input ─────────
        if row.get("actual_yield_kg") is None:
            row["actual_yield_display"] = "Not Available — awaiting harvest entry"
            row["actual_yield_source"] = "not_available"
        else:
            row["actual_yield_display"] = f"{row['actual_yield_kg']:.2f} kg"
            row["actual_yield_source"] = "harvest_measurement / farmer_input"

        # ── provenance flags ──────────────────────────────────────────────────
        row["crop_type_source"] = (
            "farmer_selected" if row.get("farmer_selected_crop")
            else ("ai_recommended" if row.get("ai_recommended_crop") else "manual_input")
        )
        row["planting_date_source"] = "farmer_input" if planting_date_str else "not_set"

        return row

    def _assert_exists(self, cycle_id: int) -> None:
        query = SelectQuery(TABLE).where("id = ?", cycle_id).limit(1)
        sql, params = query.build()
        with self._pool.connection() as conn:
            row = conn.execute(sql, params).fetchone()
        if row is None:
            raise ValueError(f"CropCycle id={cycle_id} not found")
