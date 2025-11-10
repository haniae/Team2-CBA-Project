"""Generate the Help Center verification tracker skeleton from help content metadata."""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from benchmarkos_chatbot.help_content import DEFAULT_PROMPTS, DEFAULT_SECTIONS  # noqa: E402


OUTPUT_PATH = PROJECT_ROOT / "docs" / "accuracy" / "help_center_verification_tracker.csv"


@dataclass
class TrackerRow:
    """Row to capture verification metadata for a Help Center prompt."""

    prompt_family: str
    prompt_example: str
    fact_claim: str = ""
    metric_definition: str = ""
    time_frame: str = ""
    currency: str = ""
    gaap_basis: str = ""
    status: str = "Unverified"
    source_1: str = ""
    source_2: str = ""
    source_timestamp: str = ""
    discrepancy_notes: str = ""
    updated_text: str = ""
    owner: str = ""

    def as_csv_row(self) -> List[str]:
        """Return the row as an ordered list compatible with CSV writer."""
        return [
            self.prompt_family,
            self.prompt_example,
            self.fact_claim,
            self.metric_definition,
            self.time_frame,
            self.currency,
            self.gaap_basis,
            self.status,
            self.source_1,
            self.source_2,
            self.source_timestamp,
            self.discrepancy_notes,
            self.updated_text,
            self.owner,
        ]


def _normalize_examples(section: dict) -> Sequence[str]:
    """
    Return the list of example prompts for a section.

    Falls back to command or single example where necessary so that every
    section contributes rows to the tracker.
    """
    examples: Iterable[str] | None = section.get("examples")
    if examples:
        return list(examples)

    example = section.get("example")
    if example:
        return [example]

    command = section.get("command")
    if isinstance(command, (list, tuple)):
        return list(command)
    if isinstance(command, str):
        return [command]

    return []


def build_tracker_rows() -> List[TrackerRow]:
    """Create tracker rows for every Help Center prompt family."""
    rows: List[TrackerRow] = []

    for section in DEFAULT_SECTIONS:
        family = section["title"]
        examples = _normalize_examples(section)
        for example in examples:
            rows.append(TrackerRow(prompt_family=family, prompt_example=example))

    # Include the quick-reference prompts so they are tracked as well.
    for prompt in DEFAULT_PROMPTS:
        rows.append(TrackerRow(prompt_family="Quick Reference", prompt_example=prompt))

    # Ensure deterministic ordering.
    rows.sort(key=lambda r: (r.prompt_family.lower(), r.prompt_example.lower()))
    return rows


def write_csv(rows: Sequence[TrackerRow]) -> None:
    """Write the tracker rows to the target CSV file."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    header = [
        "prompt_family",
        "prompt_example",
        "fact_claim",
        "metric_definition",
        "time_frame",
        "currency",
        "gaap_basis",
        "status",
        "source_1",
        "source_2",
        "source_timestamp",
        "discrepancy_notes",
        "updated_text",
        "owner",
    ]

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row.as_csv_row())


def main() -> None:
    """Generate the verification tracker CSV."""
    rows = build_tracker_rows()
    write_csv(rows)
    print(f"Wrote {len(rows)} tracker rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

