from datetime import datetime, timezone

import pytest

from finanlyzeos_chatbot import database
from main import _try_table_command


class StubEngine:
    def __init__(self, records, benchmark=None, benchmark_label="S&P 500 Avg"):
        self._records = records
        self._benchmark = benchmark
        self._benchmark_label = benchmark_label

    def get_metrics(self, ticker, period_filters=None):
        return self._records.get(ticker, [])

    def compute_benchmark_metrics(self, metrics, period_filters=None):
        return self._benchmark or {}

    def benchmark_label(self):
        return self._benchmark_label


def _record(ticker: str, metric: str, period: str, value: float, year: int):
    return database.MetricRecord(
        ticker=ticker,
        metric=metric,
        period=period,
        value=value,
        source="edgar",
        updated_at=datetime.now(timezone.utc),
        start_year=year,
        end_year=year,
    )


def test_table_command_formats_rows():
    engine = StubEngine(
        {
            "AAPL": [_record("AAPL", "revenue", "FY2024", 100.0, 2024)],
            "MSFT": [_record("MSFT", "revenue", "FY2023", 90.0, 2023)],
        }
    )
    output = _try_table_command("table AAPL MSFT metrics revenue", engine)
    assert output is not None
    assert "AAPL" in output and "MSFT" in output
    assert "FY2024" in output


def test_table_command_usage_error():
    engine = StubEngine({})
    message = _try_table_command("table", engine)
    assert "Usage" in message


def test_table_command_invalid_year():
    engine = StubEngine({})
    message = _try_table_command("table AAPL metrics revenue year=abcd", engine)
    assert "Invalid" in message


def test_table_command_metrics_layout():
    engine = StubEngine(
        {
            "AAPL": [
                _record("AAPL", "revenue", "FY2024", 100.0, 2024),
                _record("AAPL", "net_income", "FY2024", 20.0, 2024),
            ],
            "MSFT": [
                _record("MSFT", "revenue", "FY2024", 90.0, 2024),
                _record("MSFT", "net_income", "FY2024", 18.0, 2024),
            ],
        }
    )
    output = _try_table_command("table AAPL MSFT metrics revenue net_income layout=metrics", engine)
    assert output is not None
    assert "Metric" in output and "AAPL" in output and "MSFT" in output
    assert "Rev" in output



def test_compare_command_defaults():
    engine = StubEngine({
        "AAPL": [
            _record("AAPL", "revenue", "FY2024", 100.0, 2024),
            _record("AAPL", "return_on_equity", "FY2024", 0.2, 2024),
        ],
        "MSFT": [
            _record("MSFT", "revenue", "FY2024", 90.0, 2024),
            _record("MSFT", "return_on_equity", "FY2024", 0.18, 2024),
        ],
    })
    output = _try_table_command("compare AAPL MSFT", engine)
    assert output is not None
    assert "Metric" in output
    assert "AAPL" in output and "MSFT" in output


def test_compare_command_adds_benchmark_column_when_available():
    benchmark = {
        "revenue": _record("S&P 500 Avg", "revenue", "FY2024", 95.0, 2024),
    }
    engine = StubEngine(
        {
            "AAPL": [_record("AAPL", "revenue", "FY2024", 100.0, 2024)],
            "MSFT": [_record("MSFT", "revenue", "FY2024", 90.0, 2024)],
        },
        benchmark=benchmark,
    )
    output = _try_table_command("compare AAPL MSFT metrics revenue", engine)
    assert output is not None
    assert "S&P 500 Avg" in output

