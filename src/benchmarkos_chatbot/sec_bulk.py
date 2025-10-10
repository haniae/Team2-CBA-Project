"""Helpers for downloading and reading SEC companyfacts bulk datasets."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Optional
from zipfile import BadZipFile, ZipFile

import requests

LOGGER = logging.getLogger(__name__)


class CompanyFactsBulkCache:
    """Download-once cache for the SEC companyfacts bulk archive.

    The SEC publishes a zipped bundle of ``CIK*.json`` payloads that mirror the
    per-company ``/api/xbrl/companyfacts`` endpoint.  Downloading the archive
    once lets us serve repeated fact lookups from disk instead of hammering the
    HTTP API for every ticker and fiscal year.
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        url: str,
        refresh_hours: int,
        user_agent: str,
        timeout: float = 120.0,
    ) -> None:
        self.cache_dir = cache_dir
        self.url = url
        self.refresh_interval = timedelta(hours=max(refresh_hours, 1))
        self.user_agent = user_agent
        self.timeout = timeout

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.zip_path = self.cache_dir / "companyfacts.zip"
        self.meta_path = self.cache_dir / "metadata.json"

    # ------------------------------------------------------------------ public
    def load_company_facts(self, cik: str) -> Optional[dict[str, Any]]:
        """Return the companyfacts payload for ``cik`` if present locally."""
        if not self._ensure_fresh_copy():
            return None

        padded = cik.zfill(10)
        candidates = (
            f"companyfacts/CIK{padded}.json",
            f"CIK{padded}.json",
            f"{padded}.json",
        )

        try:
            with ZipFile(self.zip_path) as archive:
                for member in candidates:
                    try:
                        with archive.open(member) as handle:
                            return json.load(TextIOWrapper(handle, encoding="utf-8"))
                    except KeyError:
                        continue
        except BadZipFile:
            LOGGER.warning("Companyfacts bulk cache is corrupted; purging %s", self.zip_path)
            self._purge()
        except Exception:
            LOGGER.exception("Failed to read companyfacts bulk entry for CIK %s", cik)
        return None

    # ----------------------------------------------------------------- helpers
    def _ensure_fresh_copy(self) -> bool:
        """Download the archive if missing or older than the refresh interval."""
        if self.zip_path.exists() and self._is_recent():
            return True
        return self._download()

    def _is_recent(self) -> bool:
        """Return True when the cached archive is still within the refresh TTL."""
        try:
            metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            downloaded_at = metadata.get("downloaded_at")
            if not downloaded_at:
                return False
            timestamp = datetime.fromisoformat(downloaded_at)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) - timestamp < self.refresh_interval
        except FileNotFoundError:
            return False
        except Exception:
            LOGGER.debug("Unable to parse companyfacts cache metadata", exc_info=True)
            return False

    def _download(self) -> bool:
        """Download the bulk archive into the cache directory."""
        LOGGER.info("Fetching SEC companyfacts bulk archive from %s", self.url)
        tmp_path = self.zip_path.with_suffix(".tmp")
        try:
            response = requests.get(
                self.url,
                headers={"User-Agent": self.user_agent, "Accept": "application/zip"},
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            with tmp_path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            tmp_path.replace(self.zip_path)
            metadata = {
                "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "url": self.url,
            }
            self.meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            LOGGER.info("Companyfacts bulk archive cached at %s", self.zip_path)
            return True
        except Exception:
            LOGGER.warning("Failed to download companyfacts bulk data", exc_info=True)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)  # type: ignore[arg-type]
            return False

    def _purge(self) -> None:
        """Delete the corrupted archive and metadata."""
        try:
            self.zip_path.unlink(missing_ok=True)  # type: ignore[arg-type]
        finally:
            self.meta_path.unlink(missing_ok=True)  # type: ignore[arg-type]
