"""
Interactive Model Building and Scenario Analysis

Allows users to create custom forecasting models through chat interface,
configure parameters, and run scenario analyses.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable

from . import database
from .predictive_analytics import PredictiveAnalytics, Forecast

LOGGER = logging.getLogger(__name__)


@dataclass
class CustomModel:
    """Represents a user-defined forecasting model."""
    model_id: str
    user_id: str
    name: str
    model_type: str  # "arima", "prophet", "lstm", "linear_regression", "growth_rate"
    parameters: Dict[str, Any]
    metrics: List[str]
    created_at: datetime
    description: Optional[str] = None
    target_metric: Optional[str] = None
    frequency: Optional[str] = None
    forecast_horizon: Optional[int] = None
    status: str = "configured"
    regressors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model_id": self.model_id,
            "user_id": self.user_id,
            "name": self.name,
            "model_type": self.model_type,
            "parameters": self.parameters,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "target_metric": self.target_metric,
            "frequency": self.frequency,
            "forecast_horizon": self.forecast_horizon,
            "status": self.status,
            "regressors": self.regressors,
            "metadata": self.metadata,
        }


@dataclass
class ModelRun:
    """Represents a model run/forecast execution."""
    run_id: str
    model_id: str
    ticker: str
    forecast_periods: List[int]  # Years to forecast
    results: Dict[str, Any]
    created_at: datetime
    assumptions: Dict[str, Any] = field(default_factory=dict)
    driver_explanations: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "ticker": self.ticker,
            "forecast_periods": self.forecast_periods,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "assumptions": self.assumptions,
            "driver_explanations": self.driver_explanations,
            "artifacts": self.artifacts,
        }


@dataclass
class ModelAssumption:
    """Represents a model assumption for scenario analysis."""
    assumption_id: str
    model_id: str
    variable: str
    value: Optional[float]
    scenario: str  # "base", "optimistic", "pessimistic", etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "assumption_id": self.assumption_id,
            "model_id": self.model_id,
            "variable": self.variable,
            "value": self.value,
            "scenario": self.scenario,
        }


class ModelBackendError(RuntimeError):
    """Raised when a backend cannot complete the requested operation."""


class BaseModelBackend:
    """Base interface for model backends."""

    model_type: str = "base"
    display_name: str = "Base Backend"

    def __init__(self, analytics: PredictiveAnalytics):
        self.analytics = analytics

    def train(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Optional training hook."""
        return {"status": "ready"}

    def forecast(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def what_if(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        assumptions: Dict[str, float],
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    def explain(self, model_run: Dict[str, Any]) -> Dict[str, Any]:
        """Return driver explanations for a run result."""
        return model_run.get("driver_summary", {})


class GrowthRateBackend(BaseModelBackend):
    """Default backend relying on historical CAGR and volatility."""

    model_type = "growth_rate"
    display_name = "Compound Growth"

    def forecast(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trend_analysis = self.analytics.analyze_metric_trend(
            ticker, metric, years_history=parameters.get("years_history", 5) if parameters else 5, years_forecast=forecast_years
        )
        if not trend_analysis:
            raise ModelBackendError(f"No historical data available for {ticker} {metric}")

        forecasts = [
            f.to_dict()
            for f in trend_analysis.forecasts
            if f.method in {"growth_rate", "linear_regression"}
        ]
        driver_summary = {
            "trend": trend_analysis.trend,
            "growth_rate": trend_analysis.growth_rate,
            "volatility": trend_analysis.volatility,
            "method": self.model_type,
        }
        driver_explanations = [
            {
                "driver": "trend",
                "narrative": f"The metric exhibits a {trend_analysis.trend} trajectory with {trend_analysis.growth_rate:.2f}% CAGR.",
                "impact": trend_analysis.growth_rate,
            },
            {
                "driver": "volatility",
                "narrative": f"Historical volatility of {trend_analysis.volatility:.2f}% influences the forecast confidence bands.",
                "impact": trend_analysis.volatility,
            },
        ]

        confidence_bands = [
            {
                "year": item["fiscal_year"],
                "low": item["confidence_interval"]["low"],
                "high": item["confidence_interval"]["high"],
                "confidence": item.get("confidence"),
            }
            for item in forecasts
        ]

        return {
            "forecasts": forecasts,
            "historical_data": [{"year": y, "value": v} for y, v in trend_analysis.historical_data],
            "driver_summary": driver_summary,
            "driver_explanations": driver_explanations,
            "confidence_bands": confidence_bands,
            "method": self.model_type,
        }

    def what_if(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        assumptions: Dict[str, float],
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        trend_analysis = self.analytics.analyze_metric_trend(
            ticker, metric, years_history=parameters.get("years_history", 5) if parameters else 5, years_forecast=forecast_years
        )
        if not trend_analysis:
            raise ModelBackendError(f"No historical data available for {ticker} {metric}")

        base_growth = trend_analysis.growth_rate
        scenario_growth = assumptions.get("growth_rate_delta", 0) + base_growth
        current_year = datetime.now().year
        forecast_periods = [current_year + i for i in range(1, forecast_years + 1)]
        last_value = trend_analysis.historical_data[-1][1] if trend_analysis.historical_data else 0

        scenario_forecasts = []
        for year in forecast_periods:
            years_ahead = year - current_year
            growth_multiplier = (1 + scenario_growth / 100) ** years_ahead
            predicted_value = last_value * growth_multiplier
            margin_pct = 0.1 + (years_ahead * 0.05)
            margin = predicted_value * margin_pct
            scenario_forecasts.append({
                "ticker": ticker,
                "metric": metric,
                "fiscal_year": year,
                "predicted_value": predicted_value,
                "confidence_interval": {
                    "low": predicted_value - margin,
                    "high": predicted_value + margin,
                },
                "method": f"scenario_{model.model_type}",
                "confidence": max(0.5, 0.9 - (years_ahead * 0.05)),
            })

        driver_summary = {
            "base_growth_rate": base_growth,
            "scenario_growth_rate": scenario_growth,
            "assumptions": assumptions,
            "method": self.model_type,
        }

        return {
            "forecasts": scenario_forecasts,
            "historical_data": [{"year": y, "value": v} for y, v in trend_analysis.historical_data],
            "driver_summary": driver_summary,
            "driver_explanations": [
                {
                    "driver": "assumption_growth_rate",
                    "narrative": f"Scenario adjusts CAGR from {base_growth:.2f}% to {scenario_growth:.2f}%.",
                    "impact": scenario_growth - base_growth,
                }
            ],
            "method": f"{self.model_type}_scenario",
        }


class LinearRegressionBackend(GrowthRateBackend):
    """Backend focusing on linear regression outputs from trend analysis."""

    model_type = "linear_regression"
    display_name = "Linear Regression"

    def forecast(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        base = super().forecast(model, ticker, metric, forecast_years, parameters)
        base["forecasts"] = [
            item for item in base["forecasts"] if item.get("method") == "linear_regression"
        ]
        if not base["forecasts"]:
            raise ModelBackendError(f"Linear regression forecasts unavailable for {ticker} {metric}")
        base["driver_summary"]["method"] = self.model_type
        return base


class ProphetBackend(GrowthRateBackend):
    """Prophet backend; falls back gracefully if dependency missing."""

    model_type = "prophet"
    display_name = "Prophet"

    def forecast(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            from prophet import Prophet  # type: ignore
            import pandas as pd  # type: ignore
        except Exception:
            fallback = super().forecast(model, ticker, metric, forecast_years, parameters)
            fallback["driver_summary"]["note"] = "Prophet package unavailable; used growth-rate fallback."
            return fallback

        trend_analysis = self.analytics.analyze_metric_trend(
            ticker, metric, years_history=parameters.get("years_history", 12) if parameters else 12, years_forecast=forecast_years
        )
        if not trend_analysis:
            raise ModelBackendError(f"No historical data available for {ticker} {metric}")

        history_df = pd.DataFrame(
            [{"ds": datetime(year=y, month=12, day=31), "y": v} for y, v in trend_analysis.historical_data]
        )
        model_params = parameters.copy() if parameters else {}
        prophet_model = Prophet(**{k: v for k, v in model_params.items() if k not in {"years_history"}})
        prophet_model.fit(history_df)
        future = prophet_model.make_future_dataframe(periods=forecast_years, freq="Y")
        forecast_df = prophet_model.predict(future)

        forecasts = []
        driver_explanations = []
        for _, row in forecast_df.tail(forecast_years).iterrows():
            fiscal_year = row["ds"].year
            forecasts.append({
                "ticker": ticker,
                "metric": metric,
                "fiscal_year": fiscal_year,
                "predicted_value": float(row["yhat"]),
                "confidence_interval": {
                    "low": float(row["yhat_lower"]),
                    "high": float(row["yhat_upper"]),
                },
                "method": self.model_type,
                "confidence": 0.8,
            })
            driver_explanations.append({
                "driver": "trend_component",
                "narrative": f"Prophet trend component projects value of {row['trend']:.2f} for {fiscal_year}.",
                "impact": float(row["trend"]),
            })

        driver_summary = {
            "method": self.model_type,
            "components": ["trend", "seasonality"],
            "note": "Prophet model fitted on annual data.",
        }

        return {
            "forecasts": forecasts,
            "historical_data": [{"year": y, "value": v} for y, v in trend_analysis.historical_data],
            "driver_summary": driver_summary,
            "driver_explanations": driver_explanations,
            "confidence_bands": [
                {
                    "year": item["fiscal_year"],
                    "low": item["confidence_interval"]["low"],
                    "high": item["confidence_interval"]["high"],
                    "confidence": item.get("confidence"),
                }
                for item in forecasts
            ],
            "method": self.model_type,
        }


class ARIMABackend(GrowthRateBackend):
    """ARIMA backend; uses statsmodels if available."""

    model_type = "arima"
    display_name = "ARIMA"

    def forecast(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            import pandas as pd  # type: ignore
            from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore
        except Exception:
            fallback = super().forecast(model, ticker, metric, forecast_years, parameters)
            fallback["driver_summary"]["note"] = "statsmodels not available; used growth-rate fallback."
            return fallback

        trend_analysis = self.analytics.analyze_metric_trend(
            ticker, metric, years_history=parameters.get("years_history", 10) if parameters else 10, years_forecast=forecast_years
        )
        if not trend_analysis:
            raise ModelBackendError(f"No historical data available for {ticker} {metric}")

        series = pd.Series(
            data=[v for _, v in trend_analysis.historical_data],
            index=[datetime(year=y, month=12, day=31) for y, _ in trend_analysis.historical_data],
        )

        order = parameters.get("order", (1, 1, 1)) if parameters else (1, 1, 1)
        seasonal_order = parameters.get("seasonal_order", (0, 0, 0, 0)) if parameters else (0, 0, 0, 0)

        model_fit = SARIMAX(series, order=order, seasonal_order=seasonal_order, enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        forecast_res = model_fit.get_forecast(steps=forecast_years)
        forecast_index = forecast_res.predicted_mean.index

        forecasts = []
        for idx, forecast_value in enumerate(forecast_res.predicted_mean.values):
            year = forecast_index[idx].year
            conf_int = forecast_res.conf_int().iloc[idx]
            forecasts.append({
                "ticker": ticker,
                "metric": metric,
                "fiscal_year": year,
                "predicted_value": float(forecast_value),
                "confidence_interval": {
                    "low": float(conf_int.iloc[0]),
                    "high": float(conf_int.iloc[1]),
                },
                "method": self.model_type,
                "confidence": 0.75,
            })

        driver_summary = {
            "method": self.model_type,
            "order": order,
            "seasonal_order": seasonal_order,
        }

        return {
            "forecasts": forecasts,
            "historical_data": [{"year": y, "value": v} for y, v in trend_analysis.historical_data],
            "driver_summary": driver_summary,
            "driver_explanations": [
                {
                    "driver": "arima_components",
                    "narrative": f"ARIMA{order} captures autocorrelation patterns influencing the forecast.",
                    "impact": float(forecast_res.predicted_mean.values[-1]),
                }
            ],
            "confidence_bands": [
                {
                    "year": item["fiscal_year"],
                    "low": item["confidence_interval"]["low"],
                    "high": item["confidence_interval"]["high"],
                    "confidence": item.get("confidence"),
                }
                for item in forecasts
            ],
            "method": self.model_type,
        }


class LSTMBackend(GrowthRateBackend):
    """Placeholder LSTM backend with graceful degradation."""

    model_type = "lstm"
    display_name = "LSTM"

    def forecast(
        self,
        model: CustomModel,
        ticker: str,
        metric: str,
        forecast_years: int,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            import torch  # type: ignore
        except Exception:
            fallback = super().forecast(model, ticker, metric, forecast_years, parameters)
            fallback["driver_summary"]["note"] = "PyTorch not available; used growth-rate fallback."
            return fallback

        # Placeholder logic until full neural backend is implemented
        fallback = super().forecast(model, ticker, metric, forecast_years, parameters)
        fallback["driver_summary"]["note"] = "LSTM backend placeholder executed with classical fallback."
        return fallback


class ModelBuilder:
    """Builds and manages custom forecasting models."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.predictive_analytics = PredictiveAnalytics(str(db_path))
        self.backends: Dict[str, BaseModelBackend] = {
            "growth_rate": GrowthRateBackend(self.predictive_analytics),
            "linear_regression": LinearRegressionBackend(self.predictive_analytics),
            "prophet": ProphetBackend(self.predictive_analytics),
            "arima": ARIMABackend(self.predictive_analytics),
            "lstm": LSTMBackend(self.predictive_analytics),
        }

    def _get_backend(self, model_type: str) -> BaseModelBackend:
        backend = self.backends.get(model_type.lower())
        return backend or self.backends["growth_rate"]

    @staticmethod
    def _json_dumps(payload: Any) -> str:
        return json.dumps(payload, default=str, separators=(",", ":"))

    def _store_artifacts(
        self,
        conn: sqlite3.Connection,
        model_id: str,
        run_id: str,
        artifacts: List[Dict[str, Any]],
    ) -> List[str]:
        artifact_ids: List[str] = []
        for artifact in artifacts:
            artifact_id = str(uuid.uuid4())
            data_blob = artifact.get("data")
            if isinstance(data_blob, dict):
                data_blob = json.dumps(data_blob)
            conn.execute(
                """
                INSERT INTO model_artifacts (
                    artifact_id,
                    model_id,
                    run_id,
                    artifact_type,
                    location,
                    data,
                    metadata,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    model_id,
                    run_id,
                    artifact.get("type", "blob"),
                    artifact.get("location"),
                    data_blob,
                    self._json_dumps(artifact.get("metadata", {})),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            artifact_ids.append(artifact_id)
        return artifact_ids

    def available_backends(self) -> List[Dict[str, str]]:
        """Return available forecasting backends."""
        return [
            {"model_type": key, "display_name": backend.display_name}
            for key, backend in self.backends.items()
        ]
    
    def create_model(
        self,
        user_id: str,
        name: str,
        model_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[List[str]] = None,
        description: Optional[str] = None,
        target_metric: Optional[str] = None,
        frequency: Optional[str] = None,
        forecast_horizon: Optional[int] = None,
        regressors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CustomModel:
        """Create a new custom model."""
        # Validate model type
        valid_types = set(self.backends.keys())
        model_type_lower = model_type.lower()
        if model_type_lower not in valid_types:
            raise ValueError(f"Invalid model type: {model_type}. Valid types: {sorted(valid_types)}")
        
        model_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        parameters = parameters or {}
        metrics = metrics or []
        regressors = regressors or []
        metadata_payload = metadata or {}
        target_metric = target_metric or (metrics[0] if metrics else None)
        
        model = CustomModel(
            model_id=model_id,
            user_id=user_id,
            name=name,
            model_type=model_type_lower,
            parameters=parameters or {},
            metrics=metrics,
            created_at=now,
            description=description,
            target_metric=target_metric,
            frequency=frequency,
            forecast_horizon=forecast_horizon,
            status="configured",
            regressors=regressors,
            metadata=metadata_payload,
        )
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO custom_models (
                    model_id,
                    user_id,
                    name,
                    model_type,
                    parameters,
                    metrics,
                    created_at,
                    description,
                    target_metric,
                    frequency,
                    forecast_horizon,
                    status,
                    regressors,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model.model_id,
                    model.user_id,
                    model.name,
                    model.model_type,
                    json.dumps(model.parameters),
                    json.dumps(model.metrics),
                    model.created_at.isoformat(),
                    model.description,
                    model.target_metric,
                    model.frequency,
                    model.forecast_horizon,
                    model.status,
                    json.dumps(model.regressors),
                    json.dumps(model.metadata),
                ),
            )
            conn.commit()
        
        return model
    
    def get_model(self, model_id: str) -> Optional[CustomModel]:
        """Get a custom model by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT model_id, user_id, name, model_type, parameters, metrics, created_at,
                       description, target_metric, frequency, forecast_horizon, status, regressors, metadata
                FROM custom_models
                WHERE model_id = ?
                """,
                (model_id,),
            ).fetchone()
            
            if not row:
                return None
            
            return CustomModel(
                model_id=row["model_id"],
                user_id=row["user_id"],
                name=row["name"],
                model_type=row["model_type"],
                parameters=json.loads(row["parameters"]) if row["parameters"] else {},
                metrics=json.loads(row["metrics"]) if row["metrics"] else [],
                created_at=datetime.fromisoformat(row["created_at"]),
                 description=row["description"],
                 target_metric=row["target_metric"],
                 frequency=row["frequency"],
                 forecast_horizon=row["forecast_horizon"],
                 status=row["status"] or "configured",
                 regressors=json.loads(row["regressors"]) if row["regressors"] else [],
                 metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
    
    def list_models(self, user_id: str) -> List[CustomModel]:
        """List all custom models for a user."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT model_id, user_id, name, model_type, parameters, metrics, created_at,
                       description, target_metric, frequency, forecast_horizon, status, regressors, metadata
                FROM custom_models
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            
            return [
                CustomModel(
                    model_id=row["model_id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    model_type=row["model_type"],
                    parameters=json.loads(row["parameters"]) if row["parameters"] else {},
                    metrics=json.loads(row["metrics"]) if row["metrics"] else [],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    description=row["description"],
                    target_metric=row["target_metric"],
                    frequency=row["frequency"],
                    forecast_horizon=row["forecast_horizon"],
                    status=row["status"] or "configured",
                    regressors=json.loads(row["regressors"]) if row["regressors"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]
    
    def list_runs(self, model_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """List recent runs for a model."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT run_id, ticker, forecast_periods, results, created_at, assumptions, driver_explanations, artifacts
                FROM model_runs
                WHERE model_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (model_id, limit),
            ).fetchall()

            history: List[Dict[str, Any]] = []
            for row in rows:
                history.append(
                    {
                        "run_id": row["run_id"],
                        "ticker": row["ticker"],
                        "forecast_periods": json.loads(row["forecast_periods"]) if row["forecast_periods"] else [],
                        "results": json.loads(row["results"]) if row["results"] else {},
                        "created_at": row["created_at"],
                        "assumptions": json.loads(row["assumptions"]) if row["assumptions"] else {},
                        "driver_explanations": json.loads(row["driver_explanations"]) if row["driver_explanations"] else [],
                        "artifacts": json.loads(row["artifacts"]) if row["artifacts"] else [],
                    }
                )
            return history

    def run_forecast(
        self,
        model_id: str,
        ticker: str,
        metric: str,
        forecast_years: int = 3
    ) -> ModelRun:
        """Run a forecast using a custom model."""
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        backend = self._get_backend(model.model_type)

        telemetry = backend.forecast(
            model=model,
            ticker=ticker,
            metric=metric,
            forecast_years=forecast_years,
            parameters=model.parameters,
        )

        forecasts = telemetry.get("forecasts", [])
        if not forecasts:
            raise ModelBackendError(f"Backend {model.model_type} returned no forecasts.")

        forecast_periods = [
            int(item.get("fiscal_year"))
            for item in forecasts
            if item.get("fiscal_year") is not None
        ]
        if not forecast_periods:
            current_year = datetime.now().year
            forecast_periods = [current_year + i for i in range(1, forecast_years + 1)]

        driver_explanations = telemetry.pop("driver_explanations", [])
        artifacts_payload = telemetry.pop("artifacts", [])
        assumptions_payload = telemetry.get("assumptions", {})

        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        model_run = ModelRun(
            run_id=run_id,
            model_id=model_id,
            ticker=ticker,
            forecast_periods=forecast_periods,
            results=telemetry,
            created_at=now,
            assumptions=assumptions_payload if isinstance(assumptions_payload, dict) else {},
            driver_explanations=driver_explanations,
        )
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO model_runs (
                    run_id,
                    model_id,
                    ticker,
                    forecast_periods,
                    results,
                    created_at,
                    assumptions,
                    driver_explanations,
                    artifacts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_run.run_id,
                    model_run.model_id,
                    model_run.ticker,
                    self._json_dumps(model_run.forecast_periods),
                    self._json_dumps(model_run.results),
                    model_run.created_at.isoformat(),
                    self._json_dumps(model_run.assumptions),
                    self._json_dumps(model_run.driver_explanations),
                    "[]",
                ),
            )

            artifact_ids = self._store_artifacts(conn, model_id, run_id, artifacts_payload or [])
            model_run.artifacts = artifact_ids
            if artifact_ids:
                conn.execute(
                    "UPDATE model_runs SET artifacts = ? WHERE run_id = ?",
                    (self._json_dumps(artifact_ids), run_id),
                )

            metadata = dict(model.metadata or {})
            metadata.update(
                {
                    "last_run_id": run_id,
                    "last_run_at": now.isoformat(),
                    "last_ticker": ticker,
                    "last_metric": metric,
                    "backend_method": telemetry.get("method"),
                }
            )

            conn.execute(
                """
                UPDATE custom_models
                SET status = ?, forecast_horizon = COALESCE(?, forecast_horizon), metadata = ?
                WHERE model_id = ?
                """,
                (
                    "trained",
                    max(forecast_periods) - min(forecast_periods) + 1 if forecast_periods else forecast_years,
                    self._json_dumps(metadata),
                    model_id,
                ),
            )
            conn.commit()
        
        return model_run
    
    def run_scenario(
        self,
        model_id: str,
        ticker: str,
        metric: str,
        scenario_name: str,
        assumptions: Dict[str, float],
        forecast_years: int = 3
    ) -> ModelRun:
        """Run a scenario analysis with custom assumptions."""
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # Save assumptions
        now = datetime.now(timezone.utc)
        for variable, value in assumptions.items():
            assumption_id = str(uuid.uuid4())
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO model_assumptions (assumption_id, model_id, variable, value, scenario)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (assumption_id, model_id, variable, value, scenario_name),
                )
                conn.commit()
        backend = self._get_backend(model.model_type)
        telemetry = backend.what_if(
            model=model,
            ticker=ticker,
            metric=metric,
            assumptions=assumptions,
            forecast_years=forecast_years,
            parameters=model.parameters,
        )

        forecasts = telemetry.get("forecasts", [])
        if not forecasts:
            raise ModelBackendError(f"Scenario {scenario_name} produced no forecasts.")

        forecast_periods = [
            int(item.get("fiscal_year"))
            for item in forecasts
            if item.get("fiscal_year") is not None
        ]
        if not forecast_periods:
            current_year = datetime.now().year
            forecast_periods = [current_year + i for i in range(1, forecast_years + 1)]

        driver_explanations = telemetry.pop("driver_explanations", [])
        artifacts_payload = telemetry.pop("artifacts", [])

        run_id = str(uuid.uuid4())
        model_run = ModelRun(
            run_id=run_id,
            model_id=model_id,
            ticker=ticker,
            forecast_periods=forecast_periods,
            results=telemetry,
            created_at=now,
            assumptions={"scenario": scenario_name, **assumptions},
            driver_explanations=driver_explanations,
        )
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO model_runs (
                    run_id,
                    model_id,
                    ticker,
                    forecast_periods,
                    results,
                    created_at,
                    assumptions,
                    driver_explanations,
                    artifacts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_run.run_id,
                    model_run.model_id,
                    model_run.ticker,
                    self._json_dumps(model_run.forecast_periods),
                    self._json_dumps(model_run.results),
                    model_run.created_at.isoformat(),
                    self._json_dumps(model_run.assumptions),
                    self._json_dumps(model_run.driver_explanations),
                    "[]",
                ),
            )

            artifact_ids = self._store_artifacts(conn, model_id, run_id, artifacts_payload or [])
            model_run.artifacts = artifact_ids
            if artifact_ids:
                conn.execute(
                    "UPDATE model_runs SET artifacts = ? WHERE run_id = ?",
                    (self._json_dumps(artifact_ids), run_id),
                )
            conn.commit()
        
        return model_run
    
    def explain_model(self, model_id: str) -> Dict[str, Any]:
        """Get explanation of model assumptions and methodology."""
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model {model_id} not found")
        
        # Get assumptions
        assumptions = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT variable, value, scenario
                FROM model_assumptions
                WHERE model_id = ?
                """,
                (model_id,),
            ).fetchall()
            
            for row in rows:
                assumptions.append({
                    "variable": row["variable"],
                    "value": row["value"],
                    "scenario": row["scenario"],
                })
        
        latest_run: Optional[Dict[str, Any]] = None
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            last = conn.execute(
                """
                SELECT run_id, ticker, forecast_periods, results, created_at, assumptions, driver_explanations, artifacts
                FROM model_runs
                WHERE model_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (model_id,),
            ).fetchone()
            if last:
                latest_run = {
                    "run_id": last["run_id"],
                    "ticker": last["ticker"],
                    "forecast_periods": json.loads(last["forecast_periods"]) if last["forecast_periods"] else [],
                    "results": json.loads(last["results"]) if last["results"] else {},
                    "created_at": last["created_at"],
                    "assumptions": json.loads(last["assumptions"]) if last["assumptions"] else {},
                    "driver_explanations": json.loads(last["driver_explanations"]) if last["driver_explanations"] else [],
                    "artifacts": json.loads(last["artifacts"]) if last["artifacts"] else [],
                }
        
        backend = self._get_backend(model.model_type)
        backend_explanation = backend.explain((latest_run or {}).get("results", {}))
        
        narrative_library = {
            "arima": "ARIMA (AutoRegressive Integrated Moving Average) models autocorrelation structures and differencing to project values.",
            "prophet": "Prophet decomposes the series into trend, seasonality, and holiday effects for robust forecasting.",
            "lstm": "LSTM (Long Short-Term Memory) leverages neural networks to capture long-range temporal dependencies.",
            "linear_regression": "Linear regression extrapolates a fitted trend line, assuming linear continuation of historical patterns.",
            "growth_rate": "Growth rate projection compounds the observed CAGR, bounded by historical volatility for confidence intervals.",
        }
        
        return {
            "model_id": model.model_id,
            "model_name": model.name,
            "model_type": model.model_type,
            "description": model.description,
            "explanation": narrative_library.get(model.model_type, "Custom forecasting model leveraging stored configuration."),
            "parameters": model.parameters,
            "assumptions": assumptions,
            "metrics": model.metrics,
            "regressors": model.regressors,
            "metadata": model.metadata,
            "latest_run": latest_run,
            "driver_explanation": backend_explanation,
        }


