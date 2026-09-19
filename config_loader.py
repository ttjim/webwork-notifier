import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.json"


def load():
    with open(_CONFIG_PATH) as f:
        return json.load(f)
