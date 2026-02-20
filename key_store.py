"""
JSON-based API key storage on SD card.

Keys are stored in /sd/keys.json as:
    {"keys": [{"name": "OpenAI", "value": "sk-abc123..."}, ...]}
"""

import gc
import json


_KEYS_FILE = "/sd/keys.json"


class KeyStore:
    def __init__(self, sd_manager):
        self._sd = sd_manager

    def _load(self):
        """Load keys list from SD. Returns [] on any failure."""
        if not self._sd or not self._sd.is_mounted:
            return []
        data = self._sd.read_file(_KEYS_FILE)
        if data is None:
            return []
        try:
            obj = json.loads(data)
            gc.collect()
            return obj.get("keys", [])
        except (ValueError, KeyError):
            return []

    def _save(self, keys):
        """Save keys list to SD."""
        data = json.dumps({"keys": keys})
        self._sd.write_file(_KEYS_FILE, data)
        gc.collect()

    def list_keys(self):
        """Return list of key name strings."""
        return [k.get("name", "?") for k in self._load()]

    def get_key(self, name):
        """Return key dict {"name":..., "value":...} or None."""
        for k in self._load():
            if k.get("name") == name:
                return k
        return None

    def add_key(self, name, value):
        """Add a new key. Returns True on success."""
        keys = self._load()
        keys.append({"name": name, "value": value})
        self._save(keys)
        return True

    def delete_key(self, name):
        """Delete a key by name. Returns True if found and deleted."""
        keys = self._load()
        new_keys = [k for k in keys if k.get("name") != name]
        if len(new_keys) < len(keys):
            self._save(new_keys)
            return True
        return False
