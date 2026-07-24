"""Runtime configuration - the only place environment/paths live.

Load order (later wins): built-in defaults -> agentmailkit.json (project) ->
AGENTMAILKIT_* environment variables. No path is ever hardcoded in the core, so
the same package runs against any vault, laptop, or CI/cloud checkout.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

CONFIG_ENV = "AGENTMAILKIT_CONFIG"
CONFIG_NAMES = ("agentmailkit.json", ".agentmailkit.json")


@dataclass
class Config:
    # Where the tool reads/writes. `root` is the base for local-file sources.
    root: Path = field(default_factory=lambda: Path.cwd())
    jobs_dir: Path = field(default_factory=lambda: Path.cwd() / "jobs")
    prompts_dir: Optional[Path] = None            # defaults to jobs_dir/prompts
    out_dir: Optional[Path] = None                # defaults to root/out
    default_to: str = ""                          # recipient fallback
    sender: str = ""                              # From address for delivery
    timezone: str = "local"
    default_model: str = "echo"
    secrets: Dict[str, str] = field(default_factory=dict)  # name -> keychain/env ref
    extra: Dict[str, Any] = field(default_factory=dict)    # backend-specific settings

    def __post_init__(self):
        self.root = Path(self.root).expanduser()
        self.jobs_dir = Path(self.jobs_dir).expanduser()
        self.prompts_dir = Path(self.prompts_dir).expanduser() if self.prompts_dir else self.jobs_dir / "prompts"
        self.out_dir = Path(self.out_dir).expanduser() if self.out_dir else self.root / "out"


def _find_config(start: Optional[Path]) -> Optional[Path]:
    env = os.environ.get(CONFIG_ENV)
    if env:
        return Path(env).expanduser()
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        for name in CONFIG_NAMES:
            p = d / name
            if p.is_file():
                return p
    return None


def load(start: Optional[Path] = None) -> Config:
    path = _find_config(start)
    data: Dict[str, Any] = {}
    if path:
        data = json.loads(path.read_text(encoding="utf-8"))
        # Relative paths in the file resolve against the file's own directory.
        base = path.parent
        for key in ("root", "jobs_dir", "prompts_dir", "out_dir"):
            if key in data and data[key] and not os.path.isabs(str(data[key])):
                data[key] = str((base / data[key]).resolve())
    # Environment overrides (AGENTMAILKIT_ROOT, AGENTMAILKIT_DEFAULT_TO, ...).
    for f in Config.__dataclass_fields__:
        env_key = "AGENTMAILKIT_" + f.upper()
        if env_key in os.environ:
            data[f] = os.environ[env_key]
    known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
    return Config(**known)
