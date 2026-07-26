"""Open-Meteo weather (no API key)."""

from __future__ import annotations

from typing import Any

from app.http_client import get_http_client
from app.tools.context import ToolContext

WMO = {
    0: "açık",
    1: "çoğunlukla açık",
    2: "parçalı bulutlu",
    3: "kapalı",
    45: "sisli",
    48: "kırağılı sis",
    51: "hafif çisenti",
    61: "hafif yağmur",
    63: "yağmur",
    65: "şiddetli yağmur",
    71: "hafif kar",
    73: "kar",
    75: "şiddetli kar",
    80: "sağanak",
    95: "gök gürültülü",
}


async def get_weather(ctx: ToolContext, args: dict[str, Any]) -> Any:
    place = args.get("place")
    lat, lon = ctx.settings.home_lat, ctx.settings.home_lon
    label = "ev"
    if place and str(place).strip():
        label = str(place).strip()
        client = get_http_client()
        g = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": label, "count": 1, "language": "tr"},
        )
        g.raise_for_status()
        results = (g.json() or {}).get("results") or []
        if not results:
            return {"error": f"Yer bulunamadı: {label}"}
        hit = results[0]
        lat, lon = hit["latitude"], hit["longitude"]
        label = f"{hit.get('name')}, {hit.get('country_code', '')}".strip(", ")

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    }
    client = get_http_client()
    r = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
    r.raise_for_status()
    cur = r.json().get("current") or {}
    code = cur.get("weather_code")
    return {
        "place": label,
        "temperature_c": cur.get("temperature_2m"),
        "humidity_pct": cur.get("relative_humidity_2m"),
        "weather_code": code,
        "condition_tr": WMO.get(int(code), "değişken")
        if code is not None
        else "bilinmiyor",
        "wind_kmh": cur.get("wind_speed_10m"),
        "time": cur.get("time"),
    }
