"""
Fang & Flush — All Game Constants
=================================
All tunable values in one place. Change here, affects everywhere.
"""

# ──────────────────────────────────
# PLAYER
# ──────────────────────────────────
PLAYER_MAX_HP = 80           # TODO: playtest — starting/max HP
HP_RECOVERY = 32             # TODO: playtest — fixed heal after each fight
HAND_DRAW = 4                # N: cards drawn per turn
HAND_MAX = 7                 # X: max hand size
HAND_KEEP = 3                # Y: cards kept at end of turn
STARTING_DECK_SIZE = 15      # initial deck size
ARTIFACT_SLOTS = 8           # shared between artifacts + consumables

# ──────────────────────────────────
# CARD POOL
# ──────────────────────────────────
SUITS = ["red", "yellow", "blue", "green"]
NUMBERS = list(range(1, 14))  # 1-13

# ──────────────────────────────────
# COMBO MULTIPLIERS
# (sorted by rarity, based on probability simulation)
# ──────────────────────────────────
COMBO_MULTIPLIERS = {
    "single":           1.0,   # 100% — always available
    "flush_3":          1.5,   # 81%
    "pair":             2.0,   # 79%
    "straight_3":       3.0,   # 51%
    "flush_4":          2.5,   # 23%
    "straight_4":       4.5,   # 17%
    "three_of_kind":    6.0,   # 8%
    "straight_flush_3": 8.0,   # 6%
    "straight_flush_4": 15.0,  # <1%
    "straight_flush_5": 25.0,  # ultra rare
}

# ──────────────────────────────────
# DAMAGE FORMULA
# ──────────────────────────────────
# Player: sum of attack card numbers in combo × combo multiplier = damage
# Shield: sum of defense card numbers in combo × combo multiplier = shield
# Monster: single card number × 1 = damage (no combos)
# Special cards: effect triggers in combo, number contributes to combo type but NOT to damage/shield sum

# ──────────────────────────────────
# MONSTER (basic, tier 1)
# ──────────────────────────────────
MONSTER_STARTING_HAND = 5    # cards in hand at fight start
MONSTER_DRAW_PER_TURN = 1    # cards drawn per turn
MONSTER_PLAY_PER_TURN = 1    # cards played per turn (random from hand)
MONSTER_BASE_HP = 50         # TODO: playtest — tier 1 basic monster HP
MONSTER_CARD_PLAY = "random" # selection method: random from hand

# ──────────────────────────────────
# FIGHT FLOW
# ──────────────────────────────────
# 1. Player turn: draw N → play combos (unlimited) → discard to Y
# 2. Monster turn: draw 1, play 1 (random from hand)
# 3. Shield absorbs monster damage, remainder hits HP
# 4. Repeat until monster or player HP <= 0
# 5. After fight: heal HP_RECOVERY_PCT of max HP

# ──────────────────────────────────
# DECK CYCLING
# ──────────────────────────────────
# Standard deckbuilding cycle:
# - Fight start: shuffle deck → draw pile
# - Play/discard → discard pile
# - Draw pile empty → shuffle discard pile → new draw pile

# ──────────────────────────────────
# ROGUELIKE STRUCTURE
# ──────────────────────────────────
FIGHTS_PER_FLOOR = 3         # TODO: playtest — normal fights before boss
# After each fight: choose 1 of 3 new cards to add to deck
# After boss: choose artifact reward
# Shop: buy/sell artifacts, remove cards, upgrade cards
