"""
bestiary.py — Enemy and animal encyclopedia with discovery tracking.

Entries are revealed in two stages:
  1. First encounter (spotted / damaged)  → shows name + silhouette
  2. After N kills (UNLOCK_KILLS_THRESHOLD) → reveals full stats + lore

The bestiary is rendered as a scrollable list in its own screen
(referenced from states/inventory_screen.py under a dedicated tab).
"""

from __future__ import annotations
from typing import Optional

import pygame

from settings import COLOR_ACCENT, COLOR_WHITE

# How many kills needed to unlock full entry
UNLOCK_KILLS_THRESHOLD = 3

# ─────────────────────────────────────────────────────────────────────────────
# BESTIARY ENTRY TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────
# "entity_id" maps to enemy etypes and animal atypes.

ENTRY_DEFS: dict[str, dict] = {
    # ── Enemies ───────────────────────────────────────────────────────────────
    "slime": {
        "name": "Slime",
        "type": "enemy",
        "habitat": "Dungeon — damp areas",
        "lore": "Gelatinous creatures formed from dungeon miasma. They divide when "
        "exposed to sufficient magical energy, making them deceptively hard "
        "to truly eliminate.",
        "tips": "Attack quickly — their low HP means they die before splitting. "
        "Fire attacks evaporate them instantly.",
        "weakness": "Fire, sharp blades",
        "threat": 1,  # 1-5 threat rating
    },
    "bat": {
        "name": "Cave Bat",
        "type": "enemy",
        "habitat": "Dungeon — upper passages",
        "lore": "Enormous bats that nest in cave ceilings. Their echolocation is "
        "disrupted by loud sounds, temporarily blinding them.",
        "tips": "They prefer to attack from angles — watch your flanks. "
        "Stay lit; bats hate strong light sources.",
        "weakness": "Light sources, area attacks",
        "threat": 2,
    },
    "skeleton": {
        "name": "Skeleton Warrior",
        "type": "enemy",
        "habitat": "Dungeon — burial chambers",
        "lore": "Reanimated remains of ancient soldiers. The enchantment binding "
        "them is tied to the dungeon's main power crystal. Destroy the "
        "crystal and they crumble.",
        "tips": "Skeletons retreat when low on health. Pressure them to prevent "
        "regeneration. Blunt weapons deal bonus damage.",
        "weakness": "Blunt damage, Holy items",
        "threat": 3,
    },
    "golem": {
        "name": "Stone Golem",
        "type": "enemy",
        "habitat": "Dungeon — lower halls",
        "lore": "Constructed by ancient builders as guardians. Their core glows "
        "when active; strike it for critical damage.",
        "tips": "Slow but hits hard. Strafe to their sides — their turning "
        "speed is their weakness. Target the glowing eye.",
        "weakness": "Magic attacks, flanking",
        "threat": 4,
    },
    "dark_golem": {
        "name": "Dark Golem",
        "type": "boss",
        "habitat": "Boss Chamber — deep dungeon",
        "lore": "The guardian of a forbidden ritual. Said to have been a benevolent "
        "protector once, now consumed by dark crystal corruption. Its true "
        "name — 'Valdur' — is written in the ancient tome.",
        "tips": "Phase 2 begins at half health. Environmental hazards in the arena "
        "can be triggered to deal massive damage. Its name can be spoken to "
        "end the fight peacefully.",
        "weakness": "Its own name, environmental hazards",
        "threat": 5,
    },
    # ── Stage 2 enemies ────────────────────────────────────────────────────────
    "wraith": {
        "name": "Wraith",
        "type": "enemy",
        "habitat": "Haunted Ruins — corridors and crypts",
        "lore": "Ethereal spirits bound to the ruins by ancient sorrow. They phase "
        "through walls and strike from blind spots.",
        "tips": "They flank aggressively. Keep your back to a wall. Fast weapons "
        "work better than slow heavy hits.",
        "weakness": "Holy items, sustained pressure",
        "threat": 3,
    },
    "bone_archer": {
        "name": "Bone Archer",
        "type": "enemy",
        "habitat": "Haunted Ruins — elevated perches",
        "lore": "Skeletal marksmen who never miss at range. Their bone arrows are "
        "prized as crafting material by those brave enough to harvest them.",
        "tips": "Close the distance fast — they're fragile in melee. Use cover "
        "to break their line of sight.",
        "weakness": "Melee attacks, blunt damage",
        "threat": 3,
    },
    "corrupted_knight": {
        "name": "Corrupted Knight",
        "type": "enemy",
        "habitat": "Haunted Ruins — throne halls",
        "lore": "Once noble protectors, now animated by dark ruin-energy. Their "
        "armor is nearly impenetrable from the front.",
        "tips": "Flank them — their heavy armor makes them slow to turn. "
        "Don't trade blows head-on.",
        "weakness": "Flanking, magic attacks",
        "threat": 4,
    },
    "revenant": {
        "name": "Revenant",
        "type": "enemy",
        "habitat": "Haunted Ruins — deep chambers",
        "lore": "Undead warriors driven by a singular purpose. They hunt with "
        "relentless focus and can sense the living from great distances.",
        "tips": "They retreat when wounded, then re-engage. Finish them quickly.",
        "weakness": "Fire, sustained aggression",
        "threat": 3,
    },
    "gravewarden": {
        "name": "The Gravewarden",
        "type": "boss",
        "habitat": "Ruins Depths — boss chamber",
        "lore": "An ancient warlord who refused to die. His shield absorbs damage "
        "until shattered. In his second phase, he abandons defense entirely "
        "and becomes a whirlwind of bone and fury.",
        "tips": "Break the shield with 3 hits first. In Phase 2, dodge the bone "
        "spin — it covers a wide area. Stay mobile.",
        "weakness": "Shield has limited durability, Phase 2 lacks defense",
        "threat": 5,
    },
    # ── Stage 3 enemies ────────────────────────────────────────────────────────
    "void_shade": {
        "name": "Void Shade",
        "type": "enemy",
        "habitat": "Mythic Sanctum — floating platforms",
        "lore": "Fragments of the void given shape. They move impossibly fast "
        "and flicker between visible and invisible states.",
        "tips": "Watch for the shimmer — they become briefly visible before "
        "attacking. Area attacks can catch them mid-flicker.",
        "weakness": "Area attacks, light magic",
        "threat": 4,
    },
    "crystal_colossus": {
        "name": "Crystal Colossus",
        "type": "enemy",
        "habitat": "Mythic Sanctum — crystal chambers",
        "lore": "Living crystal formations that absorb mythic energy. Their "
        "massive size makes them devastating but predictable.",
        "tips": "Extremely tanky. Their attacks are slow — dodge and counter. "
        "The bow is effective for safe damage.",
        "weakness": "Blunt damage, patience",
        "threat": 5,
    },
    "mythic_sentinel": {
        "name": "Mythic Sentinel",
        "type": "enemy",
        "habitat": "Mythic Sanctum — sanctum halls",
        "lore": "Elite guardians imbued with the Sovereign's power. They combine "
        "strength, speed, and tactical awareness.",
        "tips": "The toughest regular enemy. Fight one at a time if possible. "
        "They retreat to heal, so stay aggressive.",
        "weakness": "Flanking, fire attacks",
        "threat": 5,
    },
    "ascended_wraith": {
        "name": "Ascended Wraith",
        "type": "enemy",
        "habitat": "Mythic Sanctum — throne approach",
        "lore": "Wraiths elevated by mythic energy into something far more dangerous. "
        "The fastest and most aggressive non-boss enemy in the sanctum.",
        "tips": "Dodge first, attack second. Their speed means you can't out-run "
        "them — stand and fight with quick weapon swings.",
        "weakness": "Holy items, counter-attacks",
        "threat": 5,
    },
    "mythic_sovereign": {
        "name": "The Mythic Sovereign",
        "type": "boss",
        "habitat": "Throne Room — the final arena",
        "lore": "The corrupted god-king who shattered the sanctum. Three phases of "
        "escalating power: ground melee, levitating void attacks, and a final "
        "enraged form wreathed in golden fire.",
        "tips": "Phase 1: learn the charge timing. Phase 2: dodge void waves outward. "
        "Phase 3: stay close — the rift attack has a dead zone at melee range.",
        "weakness": "Melee range in Phase 3, dodge timing",
        "threat": 5,
    },
    # ── Animals ───────────────────────────────────────────────────────────────
    "deer": {
        "name": "Forest Deer",
        "type": "animal",
        "habitat": "Village — south forest, open meadows",
        "lore": "Graceful creatures that roam the outer forests. Sacred to the "
        "Forest Spirits faction; killing too many will damage your standing.",
        "tips": "Deer flee quickly. Approach from downwind (move perpendicular "
        "to their facing). Drop raw meat for health restoration.",
        "drops": "Raw Meat (×2), Animal Hide",
        "threat": 0,
    },
    "rabbit": {
        "name": "Woodland Rabbit",
        "type": "animal",
        "habitat": "Village — plains and meadows",
        "lore": "Fast, skittish animals that bolt at any noise. "
        "Rabbit stew is a village delicacy.",
        "tips": "Very fast — use the Shadow Cloak dash to catch up.",
        "drops": "Raw Meat (×1)",
        "threat": 0,
    },
    "wolf": {
        "name": "Grey Wolf",
        "type": "animal",
        "habitat": "Village — deep forest",
        "lore": "Pack hunters that protect their territory. Lone wolves are "
        "bolder than pack members. Their howl can alert nearby animals.",
        "tips": "Wolves attack from flanks. Stay near walls to limit their angles.",
        "drops": "Raw Meat (×2), Animal Hide",
        "threat": 2,
    },
    "boar": {
        "name": "Wild Boar",
        "type": "animal",
        "habitat": "Village — dense forest undergrowth",
        "lore": "Territorial and short-tempered, a charging boar can knock a "
        "knight off their feet. Their tusks regenerate every season.",
        "tips": "Side-step the charge — a charging boar staggered itself. "
        "Hit during the stagger for high damage.",
        "drops": "Raw Meat (×3), Animal Hide (×2)",
        "threat": 3,
    },
    "bear": {
        "name": "Forest Bear",
        "type": "animal",
        "habitat": "Dungeon path — outer forest",
        "lore": "Ancient bears that pre-date the dungeon itself. They are the "
        "oldest living creatures in the region and fiercely protect "
        "their dens. Killing one angers the Forest Spirits.",
        "tips": "Bears take significant damage before reacting. "
        "Use fire attacks and keep moving.",
        "drops": "Raw Meat (×4), Animal Hide (×3)",
        "threat": 4,
    },
    "fish": {
        "name": "River Fish",
        "type": "animal",
        "habitat": "Village — river",
        "lore": "Silver-scaled fish that glitter in the sunlight. The villagers "
        "depend on them as a food source.",
        "tips": "Cannot leave water. Wade in carefully.",
        "drops": "Raw Meat (×1)",
        "threat": 0,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# BESTIARY TRACKER
# ─────────────────────────────────────────────────────────────────────────────


class Bestiary:
    """
    Tracks discoveries and kill counts per entity type.

    State:
      encountered — set of entity IDs seen at least once
      kills       — {entity_id: kill_count}
    """

    def __init__(self):
        self.encountered: set[str] = set()
        self.kills: dict[str, int] = {}

    def on_encounter(self, entity_id: str):
        """Call the first time the player sees/damages an entity."""
        self.encountered.add(entity_id)

    def on_kill(self, entity_id: str):
        """Call on every confirmed kill."""
        self.encountered.add(entity_id)
        self.kills[entity_id] = self.kills.get(entity_id, 0) + 1

    def is_discovered(self, entity_id: str) -> bool:
        return entity_id in self.encountered

    def kill_count(self, entity_id: str) -> int:
        return self.kills.get(entity_id, 0)

    def is_fully_unlocked(self, entity_id: str) -> bool:
        return self.kill_count(entity_id) >= UNLOCK_KILLS_THRESHOLD

    def completion_ratio(self) -> tuple[int, int]:
        """(unlocked, total) for progress display."""
        total = len(ENTRY_DEFS)
        unlocked = sum(1 for eid in ENTRY_DEFS if self.is_fully_unlocked(eid))
        return unlocked, total

    def get_entries_for_display(self) -> list[dict]:
        """
        Return all entries sorted: enemies first, then animals; alphabetical within.
        Each entry includes discovery state.
        """
        result = []
        for eid, edef in sorted(
            ENTRY_DEFS.items(), key=lambda x: (x[1]["type"], x[1]["name"])
        ):
            discovered = self.is_discovered(eid)
            fully_unlocked = self.is_fully_unlocked(eid)
            entry = {
                "id": eid,
                "name": edef["name"] if discovered else "???",
                "type": edef["type"],
                "threat": edef.get("threat", 0),
                "discovered": discovered,
                "fully_unlocked": fully_unlocked,
                "kill_count": self.kill_count(eid),
                "kills_needed": max(0, UNLOCK_KILLS_THRESHOLD - self.kill_count(eid)),
            }
            # Only reveal full info once threshold met
            if fully_unlocked:
                entry.update(
                    {
                        "habitat": edef.get("habitat", "Unknown"),
                        "lore": edef.get("lore", ""),
                        "tips": edef.get("tips", ""),
                        "weakness": edef.get("weakness", "Unknown"),
                        "drops": edef.get("drops", ""),
                    }
                )
            result.append(entry)
        return result

    # ── Serialisation ─────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {
            "encountered": list(self.encountered),
            "kills": dict(self.kills),
        }

    @classmethod
    def from_save(cls, data: dict) -> "Bestiary":
        b = cls()
        b.encountered = set(data.get("encountered", []))
        b.kills = {k: int(v) for k, v in data.get("kills", {}).items()}
        return b


# ─────────────────────────────────────────────────────────────────────────────
# SIMPLE RENDERER  (used inside inventory_screen tab)
# ─────────────────────────────────────────────────────────────────────────────


def render_bestiary_panel(
    screen: pygame.Surface,
    bestiary: Bestiary,
    font,
    small_font,
    x: int,
    y: int,
    w: int,
    h: int,
    cursor: int,
):
    """Render bestiary list within a panel rect."""
    entries = bestiary.get_entries_for_display()
    if not entries:
        screen.blit(font.render("No encounters yet.", True, (140, 140, 150)), (x, y))
        return

    row_h = 30
    visible = h // row_h

    start = max(0, cursor - visible // 2)
    end = min(len(entries), start + visible)

    for i, entry in enumerate(entries[start:end]):
        ry = y + i * row_h
        is_sel = (start + i) == cursor

        if is_sel:
            pygame.draw.rect(
                screen, (40, 40, 60), (x - 4, ry - 2, w + 8, row_h - 2), border_radius=3
            )

        # Threat bar (dots)
        threat_color = [
            (80, 200, 80),
            (200, 200, 60),
            (230, 150, 40),
            (230, 80, 40),
            (180, 30, 30),
        ]
        threat = entry.get("threat", 0)
        for dot in range(5):
            dc = threat_color[min(dot, 4)] if dot < threat else (40, 40, 50)
            pygame.draw.circle(screen, dc, (x + w - 80 + dot * 12, ry + row_h // 2), 4)

        # Name
        name_col = (
            COLOR_ACCENT
            if entry["fully_unlocked"]
            else ((180, 180, 190) if entry["discovered"] else (70, 70, 80))
        )
        type_tag = f"[{entry['type'][0].upper()}]"
        screen.blit(
            small_font.render(f"{type_tag} {entry['name']}", True, name_col),
            (x, ry + 8),
        )

        # Kill count
        kills_txt = f"{entry['kill_count']}/{UNLOCK_KILLS_THRESHOLD}"
        kc = (120, 180, 120) if entry["fully_unlocked"] else (120, 120, 130)
        screen.blit(small_font.render(kills_txt, True, kc), (x + w - 130, ry + 8))

    # Detail panel for selected entry
    if cursor < len(entries):
        sel = entries[cursor]
        detail_y = y + visible * row_h + 12
        if sel["fully_unlocked"]:
            lines = [
                sel.get("habitat", ""),
                sel.get("weakness", ""),
                sel.get("drops", ""),
            ]
            lore = sel.get("lore", "")
            tips = sel.get("tips", "")
            if lore:
                lines.append(lore)
            if tips:
                lines.append(tips)
            for j, line in enumerate(lines):
                if line:
                    screen.blit(
                        small_font.render(line, True, (160, 160, 170)),
                        (x, detail_y + j * 16),
                    )
        elif sel["discovered"]:
            screen.blit(
                small_font.render(
                    f"Kill {sel['kills_needed']} more to reveal full entry.",
                    True,
                    (140, 140, 150),
                ),
                (x, detail_y),
            )
