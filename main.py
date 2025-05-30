"""
Gemini Test – Auto‑save Cookies + Heartbeat
==========================================

Monitors Gemini’s auto‑refresh (``auto_refresh=True``) **and** prints a tiny heartbeat dot every 5 s so you know the
script is alive even when Google hasn’t rotated cookies for a while. When a new ``__Secure-1PSIDTS`` / ``PSIDCC``
arrives, it overwrites the value in **.env** and shows a log line.

Key features
------------
* **Heartbeat**: each monitor tick prints "." (no newline) if cookie unchanged.
  * After 50 dots we break the line to avoid an endlessly long console row.
* **Cross‑platform clean exit**: press **Enter** or **Ctrl+C** to stop; background task is cancelled gracefully.
* **Auto‑save**: updated cookie value is written back to ``.env`` and injected into ``os.environ`` for the live process.

Prerequisites
-------------
````bash
pip install gemini_webapi python-dotenv
````

Make sure **.env** has:
```env
SECURE_1PSID=   g.a000xQi...C0076
SECURE_1PSIDTS= sidts-CjIB5H03...  # or PSIDCC value
```

Run:
```bash
python gemini_test.py
```
Watch dots ⠒ cookie unchanged, and log lines when it rotates.
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

from gemini_webapi import GeminiClient
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENV_PATH = Path(".env")
CHECK_INTERVAL = 5                # Seconds between heartbeat checks
LINE_WRAP = 50                    # Wrap heartbeat every N dots

# ---------------------------------------------------------------------------
# Load credentials from .env
# ---------------------------------------------------------------------------
load_dotenv(override=False)
SECURE_1PSID = os.getenv("SECURE_1PSID")
SECURE_1PSIDTS = os.getenv("SECURE_1PSIDTS")  # May hold PSIDCC value
PROXY = os.getenv("PROXY")  # Read proxy from .env file

if not SECURE_1PSID or not SECURE_1PSIDTS:
    raise RuntimeError("Missing SECURE_1PSID or SECURE_1PSIDTS in .env. Run get_latest_gemini_cookies.py first.")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _update_env_file(key: str, value: str, env_path: Path = ENV_PATH) -> None:
    """Insert or replace ``key=value`` in the given .env file (UTF‑8)."""
    lines = []
    updated = False
    if env_path.exists():
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    updated = True
                else:
                    lines.append(line)
    if not updated:
        lines.append(f"{key}={value}\n")
    env_path.write_text("".join(lines), encoding="utf-8")


def _partner_cookie(jar: dict[str, str]) -> Optional[str]:
    for name in ("__Secure-1PSIDTS", "__Secure-1PSIDCC", "Secure_1PSIDTS", "Secure_1PSIDCC"):
        if name in jar:
            return jar[name]
    return None

# ---------------------------------------------------------------------------
# Monitor task
# ---------------------------------------------------------------------------
async def monitor_cookies(client: GeminiClient, stop_event: asyncio.Event) -> None:
    last = _partner_cookie(client.cookies)
    dot_count = 0
    while not stop_event.is_set():
        await asyncio.sleep(CHECK_INTERVAL)
        current = _partner_cookie(client.cookies)
        if current and current != last:
            last = current
            os.environ["SECURE_1PSIDTS"] = current
            _update_env_file("SECURE_1PSIDTS", current)
            print(f"\n[auto‑save] Updated .env with new PSIDTS/CC: {current[:32]}…", flush=True)
            dot_count = 0  # reset heartbeat line after update
        else:
            print(".", end="", flush=True)
            dot_count += 1
            if dot_count >= LINE_WRAP:
                print()  # newline after LINE_WRAP dots
                dot_count = 0

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    client = GeminiClient(SECURE_1PSID, SECURE_1PSIDTS, proxy=PROXY)
    await client.init(timeout=30, auto_close=False, close_delay=300, auto_refresh=True)

    stop_event = asyncio.Event()
    monitor_task = asyncio.create_task(monitor_cookies(client, stop_event))

    try:
        resp = await client.generate_content("Please tell me your specific model name.")
        print("\n" + resp.text)
        print("\n[Press Enter to quit]", end="", flush=True)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, input)
    finally:
        stop_event.set()
        await monitor_task
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
