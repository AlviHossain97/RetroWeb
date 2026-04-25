"""
Save manager — JSON-based persistence.
v3 → backward-compatible legacy format (flat inventory list).
v4 → full grid inventory + all new systems.
v5 → campaign / world-stage + new stage content.
On GBA: maps to SRAM read/write.
"""

import copy
import json
import os

SAVE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "savegame.json")
SAVE_VERSION = 5


def serialize_save_data(data: dict, *, pretty: bool = False) -> bytes:
    """Encode save data into bytes so storage can be swapped independently."""
    dump_kwargs = {"ensure_ascii": True, "sort_keys": True}
    if pretty:
        dump_kwargs["indent"] = 2
    else:
        dump_kwargs["separators"] = (",", ":")
    payload = json.dumps(data, **dump_kwargs)
    if pretty:
        payload += "\n"
    return payload.encode("utf-8")


def deserialize_save_data(payload: bytes | str | dict | None) -> dict | None:
    """Decode save bytes or text back into a save dict."""
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if not isinstance(payload, str):
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def estimate_save_size(data: dict) -> int:
    """Return the compact serialized size for platform budget checks."""
    return len(serialize_save_data(data))


def read_save_bytes(path: str | None = None) -> bytes | None:
    path = path or SAVE_PATH
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def write_save_bytes(payload: bytes, path: str | None = None) -> bool:
    path = path or SAVE_PATH
    try:
        with open(path, "wb") as handle:
            handle.write(payload)
        return True
    except OSError:
        return False


def build_save_data(
    player,
    inventory,
    quest_manager,
    map_name,
    opened_chests,
    collected_items,
    defeated_boss,
    difficulty_mode="normal",
    coins=0,
    defeated_enemies=None,
    dynamic_drops=None,
    boss_state=None,
    # v4 systems (all optional for backward compat)
    progression=None,
    reputation=None,
    bestiary=None,
    consequence_state=None,
    fast_travel=None,
    weather=None,
    killed_animals=None,
    # v5: campaign stage system
    campaign=None,
) -> dict:
    data = {
        "version": SAVE_VERSION,
        "map": map_name,
        "player_x": player.x,
        "player_y": player.y,
        "player_hp": player.hp,
        "player_facing": player.facing,
        "difficulty": difficulty_mode,
        "coins": max(0, int(coins)),
        # v4 grid inventory (falls back to legacy flat list if new save not used)
        "inventory": inventory.to_save(),
        "quest_stages": {},
        "opened_chests": list(opened_chests),
        "collected_items": list(collected_items),
        "defeated_boss": defeated_boss,
        "defeated_enemies": list(defeated_enemies or []),
        "dynamic_drops": list(dynamic_drops or []),
        "boss_state": boss_state or {},
        # v4 extension fields
        "progression": _save_progression(progression),
        "reputation": _save_reputation(reputation),
        "bestiary": _save_bestiary(bestiary),
        "consequence_state": _save_consequence_state(consequence_state),
        "fast_travel": _save_fast_travel(fast_travel),
        "weather": _save_weather(weather),
        "killed_animals": list(killed_animals or []),
        # v5: campaign
        "campaign": _save_campaign(campaign),
    }
    for qid, quest in quest_manager.quests.items():
        data["quest_stages"][qid] = {"stage": quest.stage, "complete": quest.complete}
    return data


def save_game(
    player,
    inventory,
    quest_manager,
    map_name,
    opened_chests,
    collected_items,
    defeated_boss,
    difficulty_mode="normal",
    coins=0,
    defeated_enemies=None,
    dynamic_drops=None,
    boss_state=None,
    progression=None,
    reputation=None,
    bestiary=None,
    fast_travel=None,
    weather=None,
    killed_animals=None,
    campaign=None,
):
    data = build_save_data(
        player,
        inventory,
        quest_manager,
        map_name,
        opened_chests,
        collected_items,
        defeated_boss,
        difficulty_mode=difficulty_mode,
        coins=coins,
        defeated_enemies=defeated_enemies,
        dynamic_drops=dynamic_drops,
        boss_state=boss_state,
        progression=progression,
        reputation=reputation,
        bestiary=bestiary,
        fast_travel=fast_travel,
        weather=weather,
        killed_animals=killed_animals,
        campaign=campaign,
    )
    return write_save_data(data)


def write_save_data(data: dict) -> bool:
    return write_save_bytes(serialize_save_data(data, pretty=True))


# ── v5 serialisation helpers ──────────────────────────────────────────────────


def _save_campaign(camp):
    if camp is None:
        return {}
    return camp.to_save()


# ── v4 serialisation helpers ──────────────────────────────────────────────────


def _save_progression(prog):
    if prog is None:
        return {}
    return {
        "xp": prog.xp,
        "level": prog.level,
        "skill_points": prog.skill_points,
        "total_skill_points_earned": prog.total_skill_points_earned,
        "allocated": dict(prog.allocated),
    }


def _save_reputation(rep):
    if rep is None:
        return {}
    return rep.to_save()


def _save_bestiary(bst):
    if bst is None:
        return {}
    return {
        "encountered": list(bst.encountered),
        "kills": {k: v for k, v in bst.kills.items()},
    }


def _save_consequence_state(cs):
    if cs is None:
        return {}
    return cs.to_save()


def _save_fast_travel(ft):
    if ft is None:
        return []
    return list(ft.unlocked)


def _save_weather(ws):
    if ws is None:
        return {}
    return {
        "state": ws.state,
        "timer": ws._state_timer,
        "duration": ws._duration,
    }


# ── Load ──────────────────────────────────────────────────────────────────────


def load_game():
    return deserialize_save_data(read_save_bytes())


def load_progression(data: dict):
    """Return a Progression instance from save data (or fresh if absent)."""
    from progression import Progression

    pd = data.get("progression", {})
    if pd:
        return Progression.from_save(pd)
    return Progression()


def load_reputation(data: dict):
    """Return a Reputation instance from save data (or fresh if absent)."""
    from reputation import Reputation

    rd = data.get("reputation", {})
    if rd:
        return Reputation.from_save(rd)
    return Reputation()


def load_bestiary(data: dict):
    """Return a Bestiary instance from save data (or fresh if absent)."""
    from bestiary import Bestiary

    bst = Bestiary()
    bd = data.get("bestiary", {})
    if bd:
        bst.encountered = set(bd.get("encountered", []))
        bst.kills = {k: int(v) for k, v in bd.get("kills", {}).items()}
    return bst


def load_fast_travel(data: dict):
    """Return a FastTravelManager with previously unlocked waypoints."""
    from fast_travel import FastTravelManager

    ft_data = data.get("fast_travel", [])
    if isinstance(ft_data, dict):
        return FastTravelManager.from_save(ft_data)
    ft = FastTravelManager()
    for wp in ft_data:
        ft.unlocked.add(wp)
    return ft


def load_consequence_state(data: dict):
    """Return a ConsequenceState from save data (or fresh if absent)."""
    from consequence_system import ConsequenceState

    cs_data = data.get("consequence_state", {})
    if cs_data:
        return ConsequenceState.from_save(cs_data)
    return ConsequenceState()


def load_killed_animals(data: dict) -> set:
    return set(data.get("killed_animals", []))


def load_weather(data: dict, *, viewport_width: int = 320, viewport_height: int = 240):
    """Return a WeatherSystem restored to its saved state."""
    from weather import WeatherSystem

    ws = WeatherSystem(viewport_width=viewport_width, viewport_height=viewport_height)
    wd = data.get("weather", {})
    if wd:
        ws.state = wd.get("state", "clear")
        ws._state_timer = float(wd.get("timer", 0.0))
        ws._duration = float(wd.get("duration", 60.0))
    return ws


def load_inventory(data: dict):
    """
    Return an Inventory from save data.
    Handles both v4 (dict with 'grid' key) and v3 (flat list) formats.
    """
    from inventory import Inventory

    inv_data = data.get("inventory", [])
    return Inventory.from_save(inv_data)


def load_campaign(data: dict):
    """Return a Campaign instance from save data (or fresh Stage 1 if absent)."""
    from campaign import Campaign

    return Campaign.from_save(data.get("campaign", {}))


def sanitize_loaded_save(data: dict | None) -> dict | None:
    """
    Normalize saves that would otherwise resume into a completed final-boss state.

    During active testing we prefer dropping the player back onto the Stage 2 →
    Stage 3 handoff rather than loading into a throne-room victory dead-end.
    """
    if not data:
        return data

    sanitized = copy.deepcopy(data)
    campaign = sanitized.setdefault("campaign", {})
    completed_stages = {
        int(stage)
        for stage in campaign.get("completed_stages", [])
        if isinstance(stage, (int, float, str))
    }
    boss_kills = dict(campaign.get("boss_kills", {}))
    boss_state = dict(sanitized.get("boss_state", {}))
    quest_stages = sanitized.setdefault("quest_stages", {})
    stage3_quest = dict(quest_stages.get("main_s3", {}))
    if sanitized.get("map") != "throne_room":
        return sanitized

    throne_room_finale = (
        3 in completed_stages
        or bool(boss_kills.get("mythic_sovereign"))
        or bool(stage3_quest.get("complete"))
        or bool(sanitized.get("defeated_boss"))
        or bool(boss_state.get("defeated"))
    )

    sanitized["defeated_boss"] = False
    sanitized["boss_state"] = {}

    if not throne_room_finale:
        sanitized["map"] = "sanctum_halls"
        sanitized["player_x"] = 2.0
        sanitized["player_y"] = 19.0
        sanitized["player_facing"] = "right"
        return sanitized

    sanitized["map"] = "ruins_depths"
    sanitized["player_x"] = 58.6
    sanitized["player_y"] = 19.0
    sanitized["player_facing"] = "right"

    defeated_enemies = sanitized.get("defeated_enemies", [])
    sanitized["defeated_enemies"] = [
        enemy_id
        for enemy_id in defeated_enemies
        if not (str(enemy_id).startswith("sh_") or str(enemy_id).startswith("tr_"))
    ]

    completed_stages.discard(3)
    campaign["world_stage"] = 3
    campaign["completed_stages"] = sorted(completed_stages)
    boss_kills["mythic_sovereign"] = False
    campaign["boss_kills"] = boss_kills

    stage3_quest["stage"] = 0
    stage3_quest["complete"] = False
    quest_stages["main_s3"] = stage3_quest

    return sanitized


# ── Misc ──────────────────────────────────────────────────────────────────────


def save_exists():
    return os.path.exists(SAVE_PATH)


def delete_save():
    if os.path.exists(SAVE_PATH):
        os.remove(SAVE_PATH)
