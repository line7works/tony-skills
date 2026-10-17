"""The machine's facts, resolved in one place (the contract's E16-12).

Every machine location and every account name the lifecycle code uses comes from here: from the
session's `HOME`, which a test points at its own temporary directory, and from one user-level
settings file outside any repository. No committed file holds a personal path or an account name,
so nothing here has a default for the vault, the developer root or an account: what the settings
file does not say, the tool does not know, and the gate fails on a vault it was not told of.

The tool's own folder, `<home>/.sun-v2`, holds the run directories (`runs/<run id>/`, RUN-4), the
keying value's file (`keying`, RUN-2, SEC-7) and, in `locks/`, the lock files (`<fingerprint>.lock`)
and the record of open runs (`open-runs.json`, RUN-3). Building these paths reads nothing.

The settings file, `<home>/.config/sun-v2/settings.json`:

    {"settings_version": 1,
     "vault": {"path": "...", "marker_file": "...", "projects_dir": "...", "synced_segments": ["..."]},
     "locations": {"<name>": "<path>", ...},
     "accounts": {"<provider>": ["<account or team name>", ...]},
     "program_folders": ["<folder>", ...]}

The search list (the frame's SEC-3; the owner's ruling A46): the four system folders written here, in this order,
then each folder he names under `program_folders`, in the order he writes them. The order and the four folders were
decided on his behalf, his to change by a word (A48, A49). No other folder is on it; the session's path is never
consulted. A folder he names is taken with no check of the folder or of what stands in it (RK11, A48).
"""
import os

TOOL_FOLDER = ".sun-v2"
SETTINGS_REL = os.path.join(".config", "sun-v2", "settings.json")
OPEN_RUNS_NAME = "open-runs.json"
LOCK_SUFFIX = ".lock"
SYSTEM_FOLDERS = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")


class Facts(object):
    def __init__(self, env):
        home = env.get("HOME") or ""
        self.home = os.path.abspath(home) if home else ""
        self.tool_home = os.path.join(self.home, TOOL_FOLDER) if self.home else ""
        self.runs_root = os.path.join(self.tool_home, "runs")
        self.locks_dir = os.path.join(self.tool_home, "locks")
        self.keying_file = os.path.join(self.tool_home, "keying")
        self.open_runs_file = os.path.join(self.locks_dir, OPEN_RUNS_NAME)
        self.settings_path = os.path.join(self.home, SETTINGS_REL) if self.home else ""
        self._settings = None
        self._settings_read = False

    def run_dir(self, run_id):
        return os.path.join(self.runs_root, run_id)

    def lock_file(self, fingerprint):
        return os.path.join(self.locks_dir, fingerprint + LOCK_SUFFIX)

    def settings(self, fs):
        """The settings file, read once; None where it is missing or is not an object."""
        if not self._settings_read:
            self._settings_read = True
            try:
                doc = fs.read_json(self.settings_path)
                self._settings = doc if isinstance(doc, dict) else None
            except (OSError, ValueError):
                self._settings = None
        return self._settings

    def vault(self, fs):
        settings = self.settings(fs) or {}
        vault = settings.get("vault")
        return vault if isinstance(vault, dict) else None

    def locations(self, fs):
        settings = self.settings(fs) or {}
        found = settings.get("locations")
        return dict(found) if isinstance(found, dict) else {}

    def search_list(self, fs, system=None):
        """The tool's search list: the system folders, then his folders in the order he writes them. An entry that
        is not an absolute path names no folder and is not on the list. `system` is the world's system folders
        (`world.system_folders`, these four on a real machine; a test's world names its fixture's)."""
        settings = self.settings(fs) or {}
        named = settings.get("program_folders")
        his = [f for f in named if isinstance(f, str) and os.path.isabs(f)] if isinstance(named, list) else []
        return list(SYSTEM_FOLDERS if system is None else system) + his

    def accounts(self, fs):
        settings = self.settings(fs) or {}
        found = settings.get("accounts")
        out = {}
        if isinstance(found, dict):
            for provider, names in found.items():
                if isinstance(names, list):
                    out[provider] = [n for n in names if isinstance(n, str)]
        return out
