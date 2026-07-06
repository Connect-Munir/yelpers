"""
Simple GUI for the Yelp scraper.

Lets you type the search term, location and max-results, then runs the existing
``scraper.py`` as a subprocess with the matching ``--term/--location/--max``
flags. The scraper's console output is streamed live into the log pane, so the
CAPTCHA prompts and progress lines you'd normally see in the terminal show up
here too.

Run:
    python gui.py

Nothing about the scraping logic changes — this is just a front-end that builds
the same command line you'd otherwise type by hand.
"""

from __future__ import annotations

import json
import queue
import signal
import subprocess
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import scrolledtext, ttk

HERE = Path(__file__).resolve().parent
SCRAPER = HERE / "scraper.py"
CONFIG_PATH = HERE / "config.json"


def load_defaults() -> dict:
    """Pre-fill the form from config.json when it exists."""
    defaults = {
        "search_term": "restaurants",
        "location": "San Francisco, CA",
        "max_results": 10,
        "headless": False,
        "append": True,
    }
    if CONFIG_PATH.exists():
        try:
            defaults.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


class ScraperGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.proc: subprocess.Popen | None = None
        self.log_queue: "queue.Queue[str]" = queue.Queue()

        cfg = load_defaults()

        root.title("Yelp Scraper")
        root.geometry("720x520")
        root.minsize(560, 420)

        # --- input form ---------------------------------------------------- #
        form = ttk.Frame(root, padding=12)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)

        self.term_var = tk.StringVar(value=str(cfg.get("search_term", "")))
        self.loc_var = tk.StringVar(value=str(cfg.get("location", "")))
        self.max_var = tk.StringVar(value=str(cfg.get("max_results", 10)))
        self.headless_var = tk.BooleanVar(value=bool(cfg.get("headless", False)))
        self.append_var = tk.BooleanVar(value=bool(cfg.get("append", True)))

        ttk.Label(form, text="Search term (--term):").grid(
            row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(form, textvariable=self.term_var).grid(
            row=0, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Location (--location):").grid(
            row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Entry(form, textvariable=self.loc_var).grid(
            row=1, column=1, sticky="ew", pady=4)

        ttk.Label(form, text="Max results (--max):").grid(
            row=2, column=0, sticky="w", pady=4, padx=(0, 8))
        ttk.Spinbox(form, from_=1, to=1000, textvariable=self.max_var, width=10).grid(
            row=2, column=1, sticky="w", pady=4)

        opts = ttk.Frame(form)
        opts.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Checkbutton(
            opts, text="Headless (no window — can't solve CAPTCHAs)",
            variable=self.headless_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(
            opts, text="Append / merge into existing CSV",
            variable=self.append_var).pack(side="left")

        # --- buttons ------------------------------------------------------- #
        buttons = ttk.Frame(root, padding=(12, 0))
        buttons.pack(fill="x")
        self.run_btn = ttk.Button(buttons, text="Run scraper", command=self.start)
        self.run_btn.pack(side="left")
        self.max_btn = ttk.Button(
            buttons, text="Get MAX leads", command=self.start_max)
        self.max_btn.pack(side="left", padx=8)
        self.stop_btn = ttk.Button(
            buttons, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        self.status = ttk.Label(buttons, text="Idle")
        self.status.pack(side="left", padx=12)

        # --- log pane ------------------------------------------------------ #
        self.log = scrolledtext.ScrolledText(
            root, height=18, state="disabled", wrap="word",
            font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=12, pady=12)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(100, self._drain_log)

    # ----------------------------------------------------------------------- #
    def _append(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_log(self) -> None:
        try:
            while True:
                self._append(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(100, self._drain_log)

    # ----------------------------------------------------------------------- #
    def start_max(self) -> None:
        """Scrape every result Yelp returns, ignoring the Max-results field."""
        self.start(max_all=True)

    def start(self, max_all: bool = False) -> None:
        if self.proc is not None:
            return

        term = self.term_var.get().strip()
        location = self.loc_var.get().strip()
        max_raw = self.max_var.get().strip()

        if not term or not location:
            self._append("[gui] Please fill in both a search term and a location.\n")
            return

        cmd = [
            sys.executable, "-u", str(SCRAPER),
            "--term", term,
            "--location", location,
        ]
        if max_all:
            cmd.append("--max-all")
        else:
            try:
                max_results = int(max_raw)
                if max_results < 1:
                    raise ValueError
            except ValueError:
                self._append("[gui] Max results must be a whole number >= 1.\n")
                return
            cmd += ["--max", str(max_results)]
        if self.headless_var.get():
            cmd.append("--headless")
        if not self.append_var.get():
            cmd.append("--no-append")

        self._append(f"[gui] Running: {' '.join(cmd)}\n\n")
        self.run_btn.configure(state="disabled")
        self.max_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status.configure(text="Running...")

        # On Windows, put the scraper in its own process group so we can send it
        # a CTRL_BREAK_EVENT (a graceful, CSV-saving stop) without killing the GUI.
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=str(HERE),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
        except OSError as exc:
            self._append(f"[gui] Failed to launch scraper: {exc}\n")
            self._reset()
            return

        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()

    def _pump(self, proc: subprocess.Popen) -> None:
        if proc.stdout is not None:
            for line in proc.stdout:
                self.log_queue.put(line)
        code = proc.wait()
        self.log_queue.put(f"\n[gui] Scraper finished (exit code {code}).\n")
        self.root.after(0, self._reset)

    def stop(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            return
        self._append(
            "\n[gui] Stopping scraper — saving results collected so far...\n")
        self.stop_btn.configure(state="disabled")
        try:
            if sys.platform == "win32":
                self.proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                self.proc.send_signal(signal.SIGINT)
        except (OSError, ValueError) as exc:
            self._append(f"[gui] Could not signal scraper ({exc}); force-killing.\n")
            self._force_kill()
            return
        # Backup: if it hasn't shut down gracefully within 20s, force-kill it.
        self.root.after(20000, self._force_kill_if_alive)

    def _force_kill_if_alive(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self._append(
                "[gui] Scraper didn't stop in time — force-killing it.\n")
            self._force_kill()

    def _force_kill(self) -> None:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        try:
            if sys.platform == "win32":
                # Kill the whole tree (Chrome/chromedriver are child processes).
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                    capture_output=True,
                )
            else:
                proc.kill()
        except OSError as exc:
            self._append(f"[gui] Force-kill failed: {exc}\n")

    def _reset(self) -> None:
        self.proc = None
        self.run_btn.configure(state="normal")
        self.max_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status.configure(text="Idle")

    def on_close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self._force_kill()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
