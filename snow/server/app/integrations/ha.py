"""Home Assistant REST client."""

from __future__ import annotations

from typing import Any

from app.config import Settings
from app.http_client import get_http_client


class HomeAssistantError(Exception):
    pass


class HomeAssistant:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.ha_url.rstrip("/")
        self._token = settings.ha_token
        self._default_light = settings.ha_default_light
        self._default_tv = getattr(settings, "ha_default_tv", "") or ""

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def ping(self) -> dict[str, Any]:
        url = f"{self._base}/api/"
        client = get_http_client()
        r = await client.get(url, headers=self._headers())
        if r.status_code >= 400:
            raise HomeAssistantError(f"HA ping {r.status_code}: {r.text[:160]}")
        return r.json() if r.content else {"message": "API running."}

    async def get_state(self, entity_id: str) -> dict[str, Any]:
        url = f"{self._base}/api/states/{entity_id}"
        client = get_http_client()
        r = await client.get(url, headers=self._headers())
        if r.status_code == 404:
            raise HomeAssistantError(f"Entity bulunamadı: {entity_id}")
        if r.status_code >= 400:
            raise HomeAssistantError(f"HA hata {r.status_code}: {r.text[:200]}")
        return r.json()

    async def get_states(self) -> list[dict[str, Any]]:
        url = f"{self._base}/api/states"
        client = get_http_client()
        r = await client.get(url, headers=self._headers())
        if r.status_code >= 400:
            raise HomeAssistantError(f"HA states hata {r.status_code}")
        return r.json()

    async def call_service(
        self, domain: str, service: str, data: dict[str, Any]
    ) -> Any:
        url = f"{self._base}/api/services/{domain}/{service}"
        client = get_http_client()
        r = await client.post(url, headers=self._headers(), json=data)
        if r.status_code >= 400:
            raise HomeAssistantError(f"HA servis hata {r.status_code}: {r.text[:200]}")
        if not r.content:
            return []
        return r.json()

    def resolve_light(self, entity_id: str | None) -> str:
        eid = (entity_id or self._default_light).strip()
        if not eid.startswith("light."):
            raise HomeAssistantError("Sadece light.* entity'lerine izin var.")
        return eid

    def resolve_switch(self, entity_id: str) -> str:
        eid = entity_id.strip()
        if not eid.startswith("switch."):
            raise HomeAssistantError("Sadece switch.* entity'lerine izin var.")
        return eid

    async def light_snapshot(self, entity_id: str | None = None) -> dict[str, Any]:
        eid = self.resolve_light(entity_id)
        st = await self.get_state(eid)
        attrs = st.get("attributes") or {}
        bri = attrs.get("brightness")
        pct = int(round((int(bri) / 255) * 100)) if bri is not None else None
        return {
            "entity_id": eid,
            "state": st.get("state"),
            "brightness_pct": pct,
            "friendly_name": attrs.get("friendly_name", eid),
            "color_temp_kelvin": attrs.get("color_temp_kelvin"),
            "rgb_color": attrs.get("rgb_color"),
        }

    async def light_control(
        self,
        *,
        entity_id: str | None = None,
        action: str,
        brightness_abs: int | None = None,
        brightness_delta: int | None = None,
        color_temp_kelvin: int | None = None,
        rgb_color: list[int] | None = None,
    ) -> dict[str, Any]:
        eid = self.resolve_light(entity_id)
        action = action.lower().strip()

        if action == "off":
            await self.call_service("light", "turn_off", {"entity_id": eid})
            return await self.light_snapshot(eid)

        if action == "toggle":
            await self.call_service("light", "toggle", {"entity_id": eid})
            return await self.light_snapshot(eid)

        data: dict[str, Any] = {"entity_id": eid}

        if brightness_delta is not None and brightness_abs is not None:
            raise HomeAssistantError("brightness_abs ve brightness_delta birlikte olamaz.")

        if brightness_delta is not None:
            snap = await self.light_snapshot(eid)
            current = snap.get("brightness_pct")
            if current is None:
                current = 100 if snap.get("state") == "on" else 0
            target = max(0, min(100, int(current) + int(brightness_delta)))
            if target <= 0:
                await self.call_service("light", "turn_off", {"entity_id": eid})
                return await self.light_snapshot(eid)
            data["brightness_pct"] = target
        elif brightness_abs is not None:
            target = max(0, min(100, int(brightness_abs)))
            if target <= 0:
                await self.call_service("light", "turn_off", {"entity_id": eid})
                return await self.light_snapshot(eid)
            data["brightness_pct"] = target

        if color_temp_kelvin is not None:
            data["color_temp_kelvin"] = int(color_temp_kelvin)
        if rgb_color is not None and len(rgb_color) == 3:
            data["rgb_color"] = [int(x) for x in rgb_color]

        await self.call_service("light", "turn_on", data)
        return await self.light_snapshot(eid)

    async def switch_control(self, entity_id: str, action: str) -> dict[str, Any]:
        eid = self.resolve_switch(entity_id)
        action = action.lower().strip()
        if action == "on":
            await self.call_service("switch", "turn_on", {"entity_id": eid})
        elif action == "off":
            await self.call_service("switch", "turn_off", {"entity_id": eid})
        elif action == "toggle":
            await self.call_service("switch", "toggle", {"entity_id": eid})
        else:
            raise HomeAssistantError("switch action: on|off|toggle")
        st = await self.get_state(eid)
        return {
            "entity_id": eid,
            "state": st.get("state"),
            "friendly_name": (st.get("attributes") or {}).get("friendly_name", eid),
        }

    async def activate_scene(self, entity_id: str) -> dict[str, Any]:
        eid = entity_id.strip()
        if not eid.startswith("scene."):
            raise HomeAssistantError("Sadece scene.* entity'lerine izin var.")
        await self.call_service("scene", "turn_on", {"entity_id": eid})
        return {"activated": eid}

    async def list_by_domain(self, domain: str) -> list[dict[str, str]]:
        domain = domain.strip().lower()
        states = await self.get_states()
        out: list[dict[str, str]] = []
        for st in states:
            eid = st.get("entity_id", "")
            if not eid.startswith(f"{domain}."):
                continue
            name = (st.get("attributes") or {}).get("friendly_name", eid)
            out.append(
                {
                    "entity_id": eid,
                    "name": name,
                    "state": str(st.get("state", "")),
                }
            )
        return out

    async def resolve_media(self, entity_id: str | None) -> str:
        eid = (entity_id or self._default_tv or "").strip()
        if eid and not eid.startswith("media_player."):
            raise HomeAssistantError("Sadece media_player.* entity'lerine izin var.")
        if not eid:
            eid = (await self.find_first_media_player()) or ""
        if not eid:
            raise HomeAssistantError(
                "media_player yok — HA'da Android TV entegrasyonu ve HA_DEFAULT_TV kontrol et."
            )
        return eid

    async def media_snapshot(self, entity_id: str | None = None) -> dict[str, Any]:
        eid = await self.resolve_media(entity_id)
        st = await self.get_state(eid)
        attrs = st.get("attributes") or {}
        return {
            "entity_id": eid,
            "state": st.get("state"),
            "friendly_name": attrs.get("friendly_name", eid),
            "source": attrs.get("source"),
            "app_name": attrs.get("app_name"),
            "media_title": attrs.get("media_title"),
            "volume_level": attrs.get("volume_level"),
        }

    async def media_control(
        self,
        *,
        entity_id: str | None = None,
        action: str,
        volume_level: float | None = None,
    ) -> dict[str, Any]:
        eid = await self.resolve_media(entity_id)
        action = action.lower().strip()
        data: dict[str, Any] = {"entity_id": eid}

        service_map = {
            "on": ("media_player", "turn_on"),
            "off": ("media_player", "turn_off"),
            "toggle": ("media_player", "toggle"),
            "play": ("media_player", "media_play"),
            "pause": ("media_player", "media_pause"),
            "stop": ("media_player", "media_stop"),
            "play_pause": ("media_player", "media_play_pause"),
            "next": ("media_player", "media_next_track"),
            "previous": ("media_player", "media_previous_track"),
            "volume_up": ("media_player", "volume_up"),
            "volume_down": ("media_player", "volume_down"),
            "mute": ("media_player", "volume_mute"),
        }

        if action == "volume_set" and volume_level is not None:
            await self.call_service(
                "media_player",
                "volume_set",
                {"entity_id": eid, "volume_level": max(0.0, min(1.0, float(volume_level)))},
            )
            return await self.media_snapshot(eid)

        if action == "mute":
            await self.call_service(
                "media_player",
                "volume_mute",
                {"entity_id": eid, "is_volume_muted": True},
            )
            return await self.media_snapshot(eid)

        if action not in service_map:
            raise HomeAssistantError(
                "media action: on|off|toggle|play|pause|stop|next|previous|volume_up|volume_down|mute|volume_set"
            )
        domain, service = service_map[action]
        await self.call_service(domain, service, data)
        return await self.media_snapshot(eid)

    async def find_first_media_player(self) -> str | None:
        players = await self.list_by_domain("media_player")
        if not players:
            return None
        # prefer android / tv in name
        for p in players:
            blob = (p["entity_id"] + " " + p["name"]).lower()
            if any(k in blob for k in ("android", "tv", "televizyon", "shield", "chromecast")):
                return p["entity_id"]
        return players[0]["entity_id"]

    async def home_summary(self) -> dict[str, Any]:
        lights = await self.list_by_domain("light")
        switches = await self.list_by_domain("switch")
        scenes = await self.list_by_domain("scene")
        media = await self.list_by_domain("media_player")
        default = None
        try:
            default = await self.light_snapshot()
        except HomeAssistantError:
            default = None
        default_tv = None
        try:
            tv_id = self._default_tv or await self.find_first_media_player()
            if tv_id:
                default_tv = await self.media_snapshot(tv_id)
        except HomeAssistantError:
            default_tv = None
        return {
            "default_light": default,
            "default_tv": default_tv,
            "lights": lights[:40],
            "switches": switches[:40],
            "scenes": scenes[:40],
            "media_players": media[:20],
            "counts": {
                "lights": len(lights),
                "switches": len(switches),
                "scenes": len(scenes),
                "media_players": len(media),
            },
        }
