"""Weather from Open-Meteo: no API key, no account, real numbers.

Included because a digest should be useful before it is clever. It is also the
clearest demonstration of why deterministic sources matter: a model asked to "check
the weather" will confidently invent a temperature. A model handed 18C / 63F cannot.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ..plugins import source

API = "https://api.open-meteo.com/v1/forecast"
GEO = "https://geocoding-api.open-meteo.com/v1/search"
UA = "agentmailkit/0.1 (+https://github.com/ariaxhan/agentmailkit)"
TIMEOUT = 12

# WMO weather codes, condensed to plain language.
CODES = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain", 71: "light snow", 73: "snow",
    75: "heavy snow", 77: "snow grains", 80: "light showers", 81: "showers",
    82: "violent showers", 85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "severe thunderstorm with hail",
}


def _get(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}


def _geocode(place):
    data = _get(f"{GEO}?{urllib.parse.urlencode({'name': place, 'count': 1})}")
    hits = data.get("results") or []
    if not hits:
        return None
    h = hits[0]
    label = ", ".join(x for x in (h.get("name"), h.get("admin1"), h.get("country_code")) if x)
    return h["latitude"], h["longitude"], label


@source("weather")
def weather_source(ctx, arg: str) -> str:
    """arg = a place name, or 'lat,lon', optionally '@Label', optionally '#days'.

        weather:Brooklyn
        weather:37.77,-122.42@San Francisco#3
    """
    raw = (arg or "").strip()
    days = 2
    head, sep, tail = raw.rpartition("#")
    if sep and tail.strip().isdigit():
        raw, days = head.strip(), max(1, min(int(tail.strip()), 7))
    raw, _, label_override = raw.partition("@")
    raw = raw.strip()
    if not raw:
        return "(weather: give a place name or 'lat,lon')"

    parts = raw.split(",")
    if len(parts) == 2 and all(p.strip().lstrip("-").replace(".", "").isdigit() for p in parts):
        lat, lon, label = float(parts[0]), float(parts[1]), label_override.strip() or raw
    else:
        found = _geocode(raw)
        if not found:
            return f"(weather: could not locate {raw!r})"
        lat, lon, label = found
        label = label_override.strip() or label

    params = urllib.parse.urlencode({
        "latitude": lat, "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "current": "temperature_2m,weather_code",
        "timezone": "auto", "forecast_days": days,
    })
    data = _get(f"{API}?{params}")
    daily = data.get("daily") or {}
    if not daily.get("time"):
        return f"(weather unavailable for {label})"

    units = (data.get("daily_units") or {}).get("temperature_2m_max", "C")
    out = [f"## WEATHER - {label} (live from Open-Meteo; these figures are real)\n"]
    cur = data.get("current") or {}
    if cur.get("temperature_2m") is not None:
        out.append(f"- Right now: {round(cur['temperature_2m'])}{units}, "
                   f"{CODES.get(cur.get('weather_code'), 'unknown')}")
    for i, day in enumerate(daily["time"][:days]):
        hi = daily["temperature_2m_max"][i]
        lo = daily["temperature_2m_min"][i]
        code = CODES.get(daily["weather_code"][i], "unknown")
        pop = daily.get("precipitation_probability_max", [None] * days)[i]
        rain = f", {pop}% chance of precipitation" if pop is not None else ""
        out.append(f"- {day}: {round(lo)} to {round(hi)}{units}, {code}{rain}")
    return "\n".join(out) + "\n"
