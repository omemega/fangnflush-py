# Fang & Flush: Slay That Jester — Python Prototype

Terminal prototype for validating the core combat loop.

## Run

```
python3 main.py
```

No dependencies beyond Python 3 stdlib.

## Rules

**Goal:** Survive 3 fights per floor.

**Cards:** Each card has a suit (red/yellow/blue/green, shown by color), a number (1-13), and a function (atk/def).

**Turn flow:**
1. Draw 4 cards (7 max hand, first turn draws 7)
2. Discard & redraw: swap any cards from hand (2 times free per turn)
3. Play combos: form valid combos and play them (2 plays per turn)
4. Monster attacks: monster plays 1 random card from its visible hand
5. End of turn: keep 3 cards, discard the rest (you choose)

**Combos (strict card count):**

| Combo | Cards | Multiplier |
|-------|-------|-----------|
| Single | 1 | x1 |
| Pair | 2 same number | x2 |
| Flush-3 | 3 same suit | x1.5 |
| Straight-3 | 3 consecutive | x3 |
| Flush-4 | 4 same suit | x2.5 |
| Straight-4 | 4 consecutive | x4.5 |
| Three of a Kind | 3 same number | x6 |
| Straight Flush-3 | 3 same suit + consecutive | x8 |
| Straight Flush-4 | 4 same suit + consecutive | x15 |
| Straight Flush-5 | 5 same suit + consecutive | x25 |

**Damage:** sum of atk card numbers in combo x multiplier
**Shield:** sum of def card numbers in combo x multiplier

**Controls:**
- `1 2 4` — play cards 1, 2, 4 as a combo
- `d 1 3 5` — discard cards 1, 3, 5 and redraw
- `e` — end turn (skip remaining plays)
- `s` — toggle sort (by number / by suit)
- `q` — quit

**Monster:** visible hand, plays 1 random card per turn. Atk cards deal their number as damage (shield absorbs first). Def cards do nothing to you.

**Between fights:** heal 32 HP (max 80).

## Config

All constants in `constants.py`. Key values:

```
HAND_DRAW = 4, HAND_MAX = 7, HAND_KEEP = 3
PLAYS_PER_TURN = 2, DISCARDS_PER_TURN = 2
PLAYER_MAX_HP = 80, HP_RECOVERY = 32
MONSTER_BASE_HP = 60
```
