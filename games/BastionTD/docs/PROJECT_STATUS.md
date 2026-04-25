# Project Status

## Current Status

- Bastion TD is currently a fully playable retro-inspired tower defense game with a complete run from title screen to victory or defeat.
- The project already includes the full core loop: menu flow, instructions, settings, randomized maps, tower building, enemy waves, bosses, pause, fast-forward, end screens, and saved run stats.
- The game is structured around short build phases followed by active defense phases, giving each run a steady prepare-and-react rhythm.

## What the Game Is

- Bastion TD is a base defense game where the player protects a stronghold from incoming enemy waves.
- Each battlefield is a compact grid with the base on the right side and one or two enemy spawn points on the left.
- Enemies travel along guaranteed routes toward the base, while the player places towers on open ground to stop them before they break through.

## How a Run Works

1. The player starts from the title screen and can begin a new run, open the instructions, or change settings.
2. A fresh battlefield is generated with obstacles, decorative scenery, and a valid path from every spawn point to the base.
3. The run begins with 200 gold and 20 lives.
4. During the build phase, the player moves a cursor across the map, chooses a tower, and places defenses on empty tiles.
5. The next wave is started manually once the player is ready.
6. During the wave phase, enemies spawn in sequence and towers attack automatically.
7. Defeated enemies award gold, escaped enemies remove lives, and clearing a wave grants a bonus payout.
8. The cycle repeats until all 20 waves are cleared or the base runs out of lives.

## Towers

- Arrow Tower: cheap, reliable single-target damage with strong range growth through upgrades.
- Cannon Tower: slower but heavier shots that damage groups with splash impact.
- Ice Tower: lighter damage, but slows enemies to control the pace of the wave.
- Lightning Tower: jumps damage across nearby enemies for chain hits.
- Flame Tower: fast attacks that apply burning damage over time.
- Every tower has three levels total.
- Towers can be upgraded during the build phase.
- Towers can also be sold for half of the total gold invested in them.

## Enemies

- Goblin: the basic frontline enemy.
- Wolf: fast and fragile, built to slip through weak defenses.
- Knight: slower and tougher, with armour that cuts incoming damage.
- Healer: restores health to nearby enemies and extends wave pressure.
- Swarm: weak on its own, but dangerous in large numbers.
- Titan: boss enemy with very high health, armour, and a much larger penalty if it reaches the base.

## Wave Structure

- The game contains 20 waves.
- Boss waves appear on waves 5, 10, 15, and 20.
- Early waves focus on simpler enemies, midgame waves mix speed and armour, and later waves combine support units, swarms, and bosses.
- Clearing a wave returns the game to build mode so the player can adjust tower placement and upgrades before the next attack.

## Core Systems

- Map generation: each battlefield is randomized, but every spawn route is validated so the base is always reachable.
- Combat flow: towers automatically target enemies in range and fire projectiles tied to their tower-specific effects.
- Economy: gold is spent on placement and upgrades, earned from kills, and increased by wave-clear rewards.
- Base defense: lives are lost whenever enemies reach the base, with Titans causing a much bigger hit than standard enemies.
- HUD and feedback: the interface shows wave number, gold, lives, current phase, enemies remaining, and a boss health bar during Titan fights.
- Pace control: runs support pausing and a triple-speed option.
- Settings: the player can toggle visual mode, sound effects, music, and the on-screen performance counter.
- Persistence: the game saves best wave reached, highest gold-earned score, and total runs played.

## Menus and Flow

- Title screen: start a run, open instructions, open settings, or quit.
- Instructions screen: explains the controls, the wave loop, and the tower roster.
- Pause overlay: resume the run or return to the title screen.
- Game over screen: shows run stats and allows retrying or returning to the title screen.
- Victory screen: appears after surviving all 20 waves and shows final run stats.

## Win and Loss Conditions

- Victory is achieved by surviving all 20 waves.
- Defeat happens when lives fall to zero.
- Both end states summarize the run so the player can quickly restart or return to the main menu.
