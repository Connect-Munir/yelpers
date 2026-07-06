"""Scrape-job manager.

Runs ``scraper.py`` as a subprocess (the same mechanism gui.py uses), streams
its console output for live status, and on completion ingests the per-job CSV
into MySQL. The scraper itself is untouched — it still opens a real Chrome window
and may prompt for a CAPTCHA, which must be solved on the machine running the
server.
"""

from __future__ import annotations

import csv
import re
import signal
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .config import JOBS_DIR, SCRAPER_PATH
from .database import SessionLocal
from . import crud

# Parses the scraper's per-business summary line, e.g.
#   "    -> Joe's Diner | (512) 555-0101 | web: joesdiner.com"
_PREVIEW_RE = re.compile(r"^\s*->\s*(?P<name>.*?)\s*\|\s*(?P<phone>.*?)\s*\|\s*web:\s*(?P<web>.*?)\s*$")
_MAX_LOG_LINES = 400


class Job:
    def __init__(self, term: str, location: str, max_results: int, max_all: bool, headless: bool):
        self.id = uuid.uuid4().hex[:12]
        self.term = term
        self.location = location
        self.max_results = max_results
        self.max_all = max_all
        self.headless = headless

        self.status = "queued"  # queued | running | done | error | stopped
        self.started_at: datetime | None = None
        self.finished_at: datetime | None = None
        self.scraped = 0
        self.imported = 0
        self.return_code: int | None = None
        self.message = ""
        self.log: list[str] = []
        self.previews: list[dict] = []

        self.csv_path = JOBS_DIR / f"{self.id}.csv"
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    # -- serialization ----------------------------------------------------- #
    def to_dict(self) -> dict:
        with self._lock:
            return {
                "id": self.id,
                "status": self.status,
                "term": self.term,
                "location": self.location,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "scraped": self.scraped,
                "imported": self.imported,
                "return_code": self.return_code,
                "message": self.message,
                "log": list(self.log[-120:]),
                "previews": list(self.previews),
            }

    # -- logging helpers --------------------------------------------------- #
    def _add_log(self, line: str) -> None:
        with self._lock:
            self.log.append(line)
            if len(self.log) > _MAX_LOG_LINES:
                self.log = self.log[-_MAX_LOG_LINES:]
            m = _PREVIEW_RE.match(line)
            if m:
                self.scraped += 1
                self.previews.append(
                    {
                        "name": m.group("name") or "(no name)",
                        "phone": m.group("phone") or "",
                        "website": m.group("web") or "",
                    }
                )

    # -- lifecycle --------------------------------------------------------- #
    def build_command(self) -> list[str]:
        cmd = [
            sys.executable, "-u", str(SCRAPER_PATH),
            "--term", self.term,
            "--location", self.location,
            "--out", str(self.csv_path),
            "--no-append",  # fresh per-job file; dedup happens in MySQL on ingest
        ]
        if self.max_all:
            cmd.append("--max-all")
        else:
            cmd += ["--max", str(self.max_results)]
        if self.headless:
            cmd.append("--headless")
        return cmd

    def run(self) -> None:
        """Blocking run — intended to be called inside a worker thread."""
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        self.status = "running"
        self.started_at = datetime.utcnow()
        cmd = self.build_command()
        self._add_log(f"[job {self.id}] launching: {' '.join(cmd)}")

        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(SCRAPER_PATH.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
        except OSError as exc:
            self.status = "error"
            self.message = f"Failed to launch scraper: {exc}"
            self._add_log(self.message)
            self.finished_at = datetime.utcnow()
            return

        if self._proc.stdout is not None:
            for line in self._proc.stdout:
                self._add_log(line.rstrip("\n"))

        self.return_code = self._proc.wait()
        self._ingest_csv()

        with self._lock:
            if self.status == "stopped":
                self.message = f"Stopped — imported {self.imported} lead(s) collected before stop."
            elif self.return_code == 0:
                self.status = "done"
                self.message = f"Done — imported {self.imported} lead(s) into MySQL."
            else:
                self.status = "error"
                self.message = f"Scraper exited with code {self.return_code}."
            self.finished_at = datetime.utcnow()
        self._add_log(f"[job {self.id}] {self.message}")

    def _ingest_csv(self) -> None:
        """Read the per-job CSV the scraper produced and upsert into MySQL."""
        path = Path(self.csv_path)
        if not path.exists():
            self._add_log(f"[job {self.id}] no CSV produced — nothing to import.")
            return
        db = SessionLocal()
        imported = 0
        try:
            with path.open("r", newline="", encoding="utf-8-sig") as fh:
                for row in csv.DictReader(fh):
                    if not (row.get("Yelp URL") or "").strip():
                        continue
                    try:
                        crud.upsert_business(db, row)
                        imported += 1
                    except ValueError:
                        continue
            db.commit()
        except Exception as exc:  # noqa: BLE001 - surface ingest failures to the user
            db.rollback()
            self._add_log(f"[job {self.id}] DB import error: {exc}")
        finally:
            db.close()
        with self._lock:
            self.imported = imported
        self._add_log(f"[job {self.id}] imported {imported} row(s) into MySQL.")

    def stop(self) -> bool:
        """Ask the scraper to stop gracefully (it saves rows collected so far)."""
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return False
        with self._lock:
            self.status = "stopped"
        try:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.send_signal(signal.SIGINT)
            return True
        except (OSError, ValueError):
            try:
                proc.kill()
                return True
            except OSError:
                return False


class JobManager:
    """Tracks scrape jobs in memory and runs each in a daemon thread."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, *, term: str, location: str, max_results: int, max_all: bool, headless: bool) -> Job:
        job = Job(term, location, max_results, max_all, headless)
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=job.run, name=f"scrape-{job.id}", daemon=True).start()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.started_at or datetime.min,
                reverse=True,
            )

    def stop(self, job_id: str) -> bool:
        job = self.get(job_id)
        return bool(job and job.stop())


manager = JobManager()
