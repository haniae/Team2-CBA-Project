"""Debug script to check why ML forecast context is not being built."""

import sys
import os
from pathlib import Path
import logging

# Fix Unicode encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from benchmarkos_chatbot.config import load_settings
from benchmarkos_chatbot.context_builder import _build_ml_forecast_context, _is_forecasting_query, _extract_forecast_metric, _extract_forecast_method
from benchmarkos_chatbot.analytics_engine import AnalyticsEngine

def main():
    print("="*80)
    print("ML FORECAST CONTEXT DEBUG")
    print("="*80)
    
    settings = load_settings()
    analytics_engine = AnalyticsEngine(settings)
    
    query = "Forecast Apple's revenue using LSTM"
    ticker = "AAPL"
    metric = "revenue"
    method = "lstm"
    
    print(f"\nQuery: {query}")
    print(f"Ticker: {ticker}")
    print(f"Metric: {metric}")
    print(f"Method: {method}")
    
    # Check if it's a forecasting query
    is_forecasting = _is_forecasting_query(query)
    print(f"\nIs forecasting query: {is_forecasting}")
    
    # Extract metric and method
    extracted_metric = _extract_forecast_metric(query)
    extracted_method = _extract_forecast_method(query)
    print(f"Extracted metric: {extracted_metric}")
    print(f"Extracted method: {extracted_method}")
    
    # Check if ML forecasting is available
    try:
        from benchmarkos_chatbot.ml_forecasting import get_ml_forecaster
        ml_forecaster = get_ml_forecaster(settings.database_path)
        print(f"\nML Forecaster available: {ml_forecaster is not None}")
        print(f"  - ARIMA: {ml_forecaster.arima_forecaster is not None}")
        print(f"  - Prophet: {ml_forecaster.prophet_forecaster is not None}")
        print(f"  - ETS: {ml_forecaster.ets_forecaster is not None}")
        print(f"  - LSTM: {ml_forecaster.lstm_forecaster is not None}")
        print(f"  - Transformer: {ml_forecaster.transformer_forecaster is not None}")
    except Exception as e:
        print(f"\n[ERROR] Failed to get ML forecaster: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Try to build ML forecast context
    print(f"\n{'='*80}")
    print("Building ML forecast context...")
    print("="*80)
    
    try:
        ml_forecast_context, forecast_result = _build_ml_forecast_context(
            ticker=ticker,
            metric=metric,
            database_path=settings.database_path,
            periods=3,
            method=method
        )
        
        if ml_forecast_context:
            print(f"\n[OK] ML forecast context built successfully!")
            print(f"Context length: {len(ml_forecast_context)} characters")
            print(f"Contains 'ML FORECAST': {'ML FORECAST' in ml_forecast_context or 'CRITICAL: THIS IS THE PRIMARY ANSWER' in ml_forecast_context}")
            print(f"Contains 'MODEL TECHNICAL DETAILS': {'MODEL TECHNICAL DETAILS' in ml_forecast_context or 'FINAL CHECKLIST' in ml_forecast_context}")
            print(f"Contains 'EXPLICIT DATA DUMP': {'EXPLICIT DATA DUMP' in ml_forecast_context or 'FINAL CHECKLIST' in ml_forecast_context}")
            
            # Show first 2000 characters
            print(f"\nContext preview (first 2000 characters):")
            print("-" * 80)
            print(ml_forecast_context[:2000])
            print("-" * 80)
        else:
            print(f"\n[FAIL] ML forecast context is None!")
            print("This means _build_ml_forecast_context returned None")
            
            # Try to generate forecast directly to see what happens
            print(f"\nTrying to generate forecast directly...")
            try:
                forecast = ml_forecaster.forecast(
                    ticker=ticker,
                    metric=metric,
                    periods=3,
                    method=method
                )
                if forecast:
                    print(f"[OK] Forecast generated successfully!")
                    print(f"  - Method: {forecast.method}")
                    print(f"  - Periods: {forecast.periods}")
                    print(f"  - Predicted values: {forecast.predicted_values}")
                    print(f"  - Model details: {forecast.model_details}")
                else:
                    print(f"[FAIL] Forecast is None!")
                    print("This means ml_forecaster.forecast() returned None")
            except Exception as e:
                print(f"[ERROR] Exception during forecast generation: {e}")
                import traceback
                traceback.print_exc()
        
        if forecast_result:
            print(f"\n[OK] Forecast result available!")
            print(f"  - Method: {forecast_result.method}")
            print(f"  - Periods: {forecast_result.periods}")
            print(f"  - Predicted values: {forecast_result.predicted_values}")
        else:
            print(f"\n[WARN] Forecast result is None")
            
    except Exception as e:
        print(f"\n[ERROR] Exception during context building: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

