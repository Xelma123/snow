"""OpenRouter tool JSON schemas — keep names in sync with tools/manifest.py."""

from __future__ import annotations

from typing import Any


def openrouter_tools_schema() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_home_state",
                "description": "Işık durumunu oku. Kısma öncesi kullan.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "light.* veya alias (salon, ampul, ates)",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "light_control",
                "description": (
                    "Işık aç/kapat/toggle/parlaklık. "
                    "Argo: ateş yak=on, söndür=off, knk ışığı aç=on."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": ["on", "off", "toggle"],
                        },
                        "brightness_abs": {"type": "integer"},
                        "brightness_delta": {"type": "integer"},
                        "color_temp_kelvin": {"type": "integer"},
                        "rgb_color": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 3,
                            "maxItems": 3,
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "switch_control",
                "description": "switch.* aç/kapat/toggle",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {"type": "string"},
                        "action": {
                            "type": "string",
                            "enum": ["on", "off", "toggle"],
                        },
                    },
                    "required": ["entity_id", "action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "media_control",
                "description": (
                    "TV / Android TV / media_player kontrol. "
                    "Aç, kapat, play, pause, ses."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "media_player.* veya boş=varsayılan TV",
                        },
                        "action": {
                            "type": "string",
                            "enum": [
                                "on",
                                "off",
                                "toggle",
                                "play",
                                "pause",
                                "stop",
                                "play_pause",
                                "next",
                                "previous",
                                "volume_up",
                                "volume_down",
                                "mute",
                                "volume_set",
                            ],
                        },
                        "volume_level": {
                            "type": "number",
                            "description": "0.0–1.0 for volume_set",
                        },
                    },
                    "required": ["action"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_entities",
                "description": "HA entity listesi",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "enum": ["light", "switch", "scene", "media_player"],
                        }
                    },
                    "required": ["domain"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_scenes",
                "description": "Sahneleri listele",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "activate_scene",
                "description": "scene.* çalıştır",
                "parameters": {
                    "type": "object",
                    "properties": {"entity_id": {"type": "string"}},
                    "required": ["entity_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "home_summary",
                "description": "Ev özeti: ışık, switch, TV/media, sahne",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": (
                    "Hava durumu. place boşsa ev konumu; "
                    "place='Berlin' veya 'Avrupa/Paris' gibi yer adı olabilir."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "place": {
                            "type": "string",
                            "description": "Şehir/ülke adı; boş=ev",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "profile_get",
                "description": (
                    "Kayıtlı kullanıcı profilini oku. "
                    "Örn: 'adım ne?', 'ismimi hatırlıyor musun?' → key=user_name. "
                    "Soru soruyorsa ASLA profile_set kullanma."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Şimdilik genelde user_name",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "profile_set",
                "description": (
                    "Kullanıcı adını KAYDET. Sadece açık tanıtımda: "
                    "'benim adım Murat', 'adımı Murat olarak kaydet'. "
                    "'adım ne' SORUSUDUR — set etme."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "user_name": {
                            "type": "string",
                            "description": "Gerçek isim (ne/kim/nedir olamaz)",
                        }
                    },
                    "required": ["user_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_routine",
                "description": (
                    "İsimli ev makrosu çalıştır (film_gecesi, iyi_geceler, eve_donus, sabah). "
                    "Çok adımlı ışık+TV senaryoları."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "routine_id": {
                            "type": "string",
                            "description": (
                                "film_gecesi | iyi_geceler | eve_donus | sabah veya alias"
                            ),
                        }
                    },
                    "required": ["routine_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_routines",
                "description": "Kayıtlı rutin/makroları listele",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_jobs",
                "description": "Bekleyen zamanlanmış işleri listele",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_job",
                "description": "Zamanlanmış işi iptal et",
                "parameters": {
                    "type": "object",
                    "properties": {"job_id": {"type": "integer"}},
                    "required": ["job_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "answer_only",
                "description": "Ev eylemi yok; sadece sohbet",
                "parameters": {
                    "type": "object",
                    "properties": {"note": {"type": "string"}},
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "pc_control",
                "description": (
                    "MSI/PC kontrolü (anlık veya Snow'un tek seferlik gecikmeli işi). "
                    "Yinelenen zamanlama YOK. "
                    "wake=WOL uyandır, status=açık mı, "
                    "sleep/shutdown/reboot/lock/close_tab/open_url/open_app/volume agent gerekir. "
                    "target boşsa varsayılan PC (msi)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "msi | bilgisayar | pc veya boş",
                        },
                        "action": {
                            "type": "string",
                            "enum": [
                                "status",
                                "wake",
                                "sleep",
                                "shutdown",
                                "reboot",
                                "lock",
                                "volume",
                                "mute",
                                "unmute",
                                "open_url",
                                "close_tab",
                                "open_app",
                                "run_macro",
                            ],
                        },
                        "value": {
                            "description": "volume 0-100, URL, app id veya macro id",
                        },
                    },
                    "required": ["action"],
                },
            },
        },
    ]


def schema_tool_names() -> list[str]:
    names: list[str] = []
    for item in openrouter_tools_schema():
        fn = (item.get("function") or {})
        n = fn.get("name")
        if n:
            names.append(str(n))
    return names
