"""
User-defined forecasting plugin management.

Allows analysts to register custom forecasting classes, execute them in a
sandboxed subprocess, and persist lightweight state for future forecasts.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import multiprocessing as mp
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .. import database

LOGGER = logging.getLogger(__name__)

# Timeout (seconds) for sandboxed plugin execution.
DEFAULT_PLUGIN_TIMEOUT = 30


class PluginExecutionError(RuntimeError):
    """Raised when a user plugin fails during sandbox execution."""


class PluginRegistrationError(RuntimeError):
    """Raised when a plugin cannot be registered."""


@dataclass
class ForecastingPlugin:
    """Metadata for a registered forecasting plugin."""

    plugin_id: str
    user_id: str
    name: str
    class_name: str
    module_path: Path
    description: Optional[str]
    metadata: Dict[str, Any]
    state: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    last_trained_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "user_id": self.user_id,
            "name": self.name,
            "class_name": self.class_name,
            "module_path": str(self.module_path),
            "description": self.description,
            "metadata": self.metadata,
            "state": self.state,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_trained_at": self.last_trained_at.isoformat()
            if self.last_trained_at
            else None,
        }


@dataclass
class PluginForecast:
    """Result returned by a plugin forecast."""

    predictions: List[float]
    description: Dict[str, Any]
    confidence: Optional[List[Dict[str, Any]]] = None


def _call_optional(obj: Any, attr: str, *args: Any, **kwargs: Any) -> Optional[Any]:
    """Call optional attribute if callable and return JSON-serialisable result."""
    target = getattr(obj, attr, None)
    if callable(target):
        try:
            return target(*args, **kwargs)
        except Exception:  # pragma: no cover - defensive guard
            LOGGER.exception("Optional method %s failed on %s", attr, obj)
    return None


def _plugin_worker(
    module_path: str,
    class_name: str,
    command: str,
    payload: Dict[str, Any],
    conn: mp.connection.Connection,
) -> None:
    """Execute user plugin command inside isolated process."""
    try:
        spec = importlib.util.spec_from_file_location("user_forecast_plugin", module_path)
        if not spec or not spec.loader:
            raise ImportError(f"Unable to load plugin module from {module_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["user_forecast_plugin"] = module
        spec.loader.exec_module(module)

        plugin_cls = getattr(module, class_name, None)
        if plugin_cls is None:
            raise AttributeError(f"Plugin class '{class_name}' not found in module.")

        data_records = payload.get("data") or []
        df = pd.DataFrame(data_records)
        parameters = payload.get("parameters") or {}
        periods = int(payload.get("periods", 0)) if payload.get("periods") else 0

        if command == "train":
            model = plugin_cls()
            fit_sig = getattr(model, "fit", None)
            if callable(fit_sig):
                model.fit(df, **parameters)
            state = _call_optional(model, "serialize_state")
            description = _call_optional(model, "describe") or {}
            conn.send({"success": True, "state": state, "description": description})

        elif command == "predict":
            state = payload.get("state")
            model: Any
            loader = getattr(plugin_cls, "load_state", None)
            if callable(loader):
                model = loader(state)
            else:
                model = plugin_cls()
                load_method = getattr(model, "load_state", None)
                if callable(load_method) and state is not None:
                    load_method(state)

            # Some plugins may require fit before predict even when state provided.
            if getattr(model, "requires_fit_before_predict", False):
                fit_sig = getattr(model, "fit", None)
                if callable(fit_sig):
                    model.fit(df, **parameters)

            predict_sig = getattr(model, "predict", None)
            if not callable(predict_sig):
                raise AttributeError("Plugin must implement predict(periods: int).")
            if periods <= 0:
                raise ValueError("Prediction periods must be greater than zero.")
            forecast_values = predict_sig(periods)
            if not isinstance(forecast_values, Iterable):
                raise ValueError("Plugin predict() must return an iterable of values.")
            forecast = list(forecast_values)
            description = _call_optional(model, "describe") or {}
            confidence = _call_optional(model, "confidence_intervals")
            conn.send(
                {
                    "success": True,
                    "forecast": forecast,
                    "description": description,
                    "confidence": confidence,
                }
            )
        else:
            raise ValueError(f"Unknown command '{command}' for plugin.")
    except Exception as exc:  # pragma: no cover - defensive, logging happens in parent
        conn.send({"success": False, "error": repr(exc)})
    finally:
        conn.close()


class ForecastingPluginManager:
    """Manages registration and execution of user-defined forecasting plugins."""

    def __init__(
        self,
        database_path: Path,
        *,
        plugins_dir: Optional[Path] = None,
        timeout_seconds: int = DEFAULT_PLUGIN_TIMEOUT,
    ) -> None:
        self.database_path = Path(database_path)
        self.plugins_dir = plugins_dir or self.database_path.parent / "forecasting_plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Registration and lookup
    # ------------------------------------------------------------------

    def register_plugin(
        self,
        user_id: str,
        name: str,
        class_name: str,
        source_code: str,
        *,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ForecastingPlugin:
        """Register a plugin by storing its source code on disk and metadata in the DB."""
        user_id = user_id or "default"
        canonical_name = name.strip()
        if not canonical_name:
            raise PluginRegistrationError("Plugin name cannot be empty.")
        if not class_name.strip():
            raise PluginRegistrationError("Plugin class name cannot be empty.")

        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                """
                SELECT plugin_id FROM user_forecasting_plugins
                WHERE user_id = ? AND LOWER(name) = LOWER(?)
                """,
                (user_id, canonical_name),
            ).fetchone()
            if existing:
                raise PluginRegistrationError(
                    f"A plugin named '{canonical_name}' already exists for user {user_id}."
                )

        plugin_id = str(uuid.uuid4())
        module_path = self.plugins_dir / f"{plugin_id}.py"
        module_path.write_text(source_code, encoding="utf-8")

        now = datetime.now(timezone.utc)
        metadata_payload = metadata or {}

        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                INSERT INTO user_forecasting_plugins (
                    plugin_id,
                    user_id,
                    name,
                    class_name,
                    module_path,
                    description,
                    metadata,
                    state,
                    created_at,
                    updated_at,
                    last_trained_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    plugin_id,
                    user_id,
                    canonical_name,
                    class_name.strip(),
                    str(module_path),
                    description,
                    json.dumps(metadata_payload, default=str),
                    None,
                    now.isoformat(),
                    now.isoformat(),
                    None,
                ),
            )
            conn.commit()

        return ForecastingPlugin(
            plugin_id=plugin_id,
            user_id=user_id,
            name=canonical_name,
            class_name=class_name.strip(),
            module_path=module_path,
            description=description,
            metadata=metadata_payload,
            state=None,
            created_at=now,
            updated_at=now,
            last_trained_at=None,
        )

    def list_plugins(self, user_id: Optional[str] = None) -> List[ForecastingPlugin]:
        """List plugins, optionally scoped to a specific user."""
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            if user_id:
                rows = conn.execute(
                    """
                    SELECT * FROM user_forecasting_plugins
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    """,
                    (user_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM user_forecasting_plugins
                    ORDER BY created_at DESC
                    """
                ).fetchall()

        return [self._row_to_plugin(row) for row in rows]

    def get_plugin(self, plugin_id: str) -> Optional[ForecastingPlugin]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM user_forecasting_plugins
                WHERE plugin_id = ?
                """,
                (plugin_id,),
            ).fetchone()
        return self._row_to_plugin(row) if row else None

    def get_plugin_by_name(self, user_id: str, name: str) -> Optional[ForecastingPlugin]:
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT * FROM user_forecasting_plugins
                WHERE user_id = ? AND LOWER(name) = LOWER(?)
                """,
                (user_id or "default", name),
            ).fetchone()
        return self._row_to_plugin(row) if row else None

    # ------------------------------------------------------------------
    # Training and Forecasting
    # ------------------------------------------------------------------

    def train_plugin(
        self,
        plugin_id: str,
        *,
        ticker: str,
        metric: str,
        parameters: Optional[Dict[str, Any]] = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """Train a plugin on the specified ticker/metric."""
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            raise PluginExecutionError(f"Plugin {plugin_id} not found.")
        series = self._load_metric_series(ticker, metric)
        if len(series) < 2:
            raise PluginExecutionError(
                f"Not enough historical data for {ticker} {metric} to train plugin."
            )
        response = self._execute_plugin(
            plugin=plugin,
            command="train",
            payload={
                "data": series,
                "parameters": parameters or {},
            },
        )
        if not response.get("success"):
            raise PluginExecutionError(response.get("error", "Training failed"))

        state = response.get("state")
        now = datetime.now(timezone.utc)
        with sqlite3.connect(self.database_path) as conn:
            conn.execute(
                """
                UPDATE user_forecasting_plugins
                SET state = ?, updated_at = ?, last_trained_at = ?
                WHERE plugin_id = ?
                """,
                (
                    json.dumps(state, default=str) if state is not None else None,
                    now.isoformat(),
                    now.isoformat(),
                    plugin.plugin_id,
                ),
            )
            conn.commit()

        plugin.state = state if isinstance(state, dict) else None
        plugin.updated_at = now
        plugin.last_trained_at = now
        return {
            "state": state,
            "description": response.get("description") or {},
            "trained_at": now.isoformat(),
        }

    def forecast_with_plugin(
        self,
        plugin_id: str,
        *,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
        retrain: bool = False,
    ) -> PluginForecast:
        """Generate a forecast using a registered plugin."""
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            raise PluginExecutionError(f"Plugin {plugin_id} not found.")

        if retrain or plugin.state is None:
            self.train_plugin(
                plugin_id=plugin_id,
                ticker=ticker,
                metric=metric,
                parameters=parameters,
            )
            plugin = self.get_plugin(plugin_id)  # Reload with persisted state

        series = self._load_metric_series(ticker, metric)
        if len(series) < 2:
            raise PluginExecutionError(
                f"Not enough historical data for {ticker} {metric} to forecast."
            )

        response = self._execute_plugin(
            plugin=plugin,
            command="predict",
            payload={
                "data": series,
                "parameters": parameters or {},
                "state": plugin.state,
                "periods": forecast_years,
            },
        )
        if not response.get("success"):
            raise PluginExecutionError(response.get("error", "Prediction failed"))

        predictions = response.get("forecast") or []
        description = response.get("description") or {}
        confidence = response.get("confidence")
        return PluginForecast(predictions=predictions, description=description, confidence=confidence)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _row_to_plugin(self, row: sqlite3.Row) -> ForecastingPlugin:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}
        state = json.loads(row["state"]) if row["state"] else None
        created = datetime.fromisoformat(row["created_at"])
        updated = datetime.fromisoformat(row["updated_at"])
        last_trained = (
            datetime.fromisoformat(row["last_trained_at"]) if row["last_trained_at"] else None
        )
        return ForecastingPlugin(
            plugin_id=row["plugin_id"],
            user_id=row["user_id"],
            name=row["name"],
            class_name=row["class_name"],
            module_path=Path(row["module_path"]),
            description=row["description"],
            metadata=metadata,
            state=state,
            created_at=created,
            updated_at=updated,
            last_trained_at=last_trained,
        )

    def _execute_plugin(
        self,
        *,
        plugin: ForecastingPlugin,
        command: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute plugin command in sandboxed process."""
        parent_conn, child_conn = mp.Pipe()
        ctx = mp.get_context("spawn")
        process = ctx.Process(
            target=_plugin_worker,
            args=(
                str(plugin.module_path),
                plugin.class_name,
                command,
                payload,
                child_conn,
            ),
        )
        process.start()
        child_conn.close()
        process.join(timeout=self.timeout_seconds)

        if process.is_alive():
            process.terminate()
            process.join()
            raise PluginExecutionError(
                f"Plugin execution timed out after {self.timeout_seconds} seconds."
            )

        if parent_conn.poll():
            response = parent_conn.recv()
        else:
            response = {"success": False, "error": "No response from plugin process."}

        parent_conn.close()
        return response

    def _load_metric_series(self, ticker: str, metric: str) -> List[Dict[str, Any]]:
        """Load historical series for ticker/metric."""
        with sqlite3.connect(self.database_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT period, value, start_year, end_year
                FROM metric_snapshots
                WHERE ticker = ? AND metric = ?
                ORDER BY period ASC
                """,
                (ticker.upper(), metric),
            ).fetchall()

        series: List[Dict[str, Any]] = []
        for row in rows:
            period = row["period"]
            start_year = row["start_year"]
            end_year = row["end_year"]
            fiscal_year = end_year or start_year
            series.append(
                {
                    "period": period,
                    "value": row["value"],
                    "fiscal_year": fiscal_year,
                }
            )
        return series


