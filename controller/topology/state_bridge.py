"""Small cross-process bridge for controller link state."""

import json
import os
import tempfile
from pathlib import Path
from threading import Lock
from typing import Dict


_STATE_FILE = Path(__file__).resolve().parents[2] / ".sdn-ite-link-state.json"
_LOCK = Lock()


def set_link_state(link_id: str, is_active: bool) -> None:
    """Persist a controller-observed link state for the backend process."""
    if not link_id:
        return

    with _LOCK:
        states = _read_states()
        states[link_id] = is_active
        fd, temp_name = tempfile.mkstemp(
            prefix=".sdn-ite-link-state-",
            suffix=".tmp",
            dir=str(_STATE_FILE.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(states, stream)
            os.replace(temp_name, _STATE_FILE)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)


def get_link_states() -> Dict[str, bool]:
    """Read controller-observed link states, returning an empty map if absent."""
    with _LOCK:
        return _read_states()


def _read_states() -> Dict[str, bool]:
    try:
        with _STATE_FILE.open("r", encoding="utf-8") as stream:
            raw_states = json.load(stream)
        return {
            str(link_id): bool(is_active)
            for link_id, is_active in raw_states.items()
        }
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
