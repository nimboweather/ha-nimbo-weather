"""Checks in the spirit of hassfest / the HACS action, runnable without them (CI runs the real ones)."""

from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).parents[1]
COMP = ROOT / "custom_components/nimbo_weather"


def _keys(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        out |= _keys(v, f"{prefix}{k}.") if isinstance(v, dict) else {f"{prefix}{k}"}
    return out


def test_manifest() -> None:
    m = json.loads((COMP / "manifest.json").read_text())
    assert list(m)[:2] == ["domain", "name"] and list(m)[2:] == sorted(list(m)[2:])  # hassfest's key order
    assert m["domain"] == COMP.name and m["config_flow"] is True and m["iot_class"] == "cloud_polling"
    assert m["version"] and m["requirements"] == [] and isinstance(m["codeowners"], list)


def test_hacs_json() -> None:
    h = json.loads((ROOT / "hacs.json").read_text())
    assert h["name"] and h["homeassistant"]


def test_translations_match_strings() -> None:
    strings = _keys(json.loads((COMP / "strings.json").read_text()))
    langs = sorted(p.stem for p in (COMP / "translations").glob("*.json"))
    assert langs == ["de", "en", "es", "fr", "it"]
    for lang in langs:
        t = json.loads((COMP / "translations" / f"{lang}.json").read_text())
        assert _keys(t) == strings, lang
        assert "[%key:" not in json.dumps(t), lang  # custom integrations ship resolved strings
