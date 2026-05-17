#!/usr/bin/env python3
"""Fang & Flush — Terminal Prototype (combat loop only)."""

import random
from collections import namedtuple, Counter

from constants import (
    PLAYER_MAX_HP, HP_RECOVERY, HAND_DRAW, HAND_MAX, HAND_KEEP,
    PLAYS_PER_TURN, DISCARDS_PER_TURN,
    STARTING_DECK_SIZE, SUITS, NUMBERS, COMBO_MULTIPLIERS,
    MONSTER_STARTING_HAND, MONSTER_DRAW_PER_TURN, MONSTER_PLAY_PER_TURN,
    MONSTER_BASE_HP, FIGHTS_PER_FLOOR,
)

Card = namedtuple("Card", ["suit", "number", "function"])

# ─── Artifacts ───

ARTIFACTS = {
    "blood_edge": {
        "name": "Blood Edge",
        "desc": "10% of attack damage heals you",
    },
    "iron_wall": {
        "name": "Iron Wall",
        "desc": "30% of shield converts to damage",
    },
    "pair_boost": {
        "name": "Pair Boost",
        "desc": "Pair multiplier: x2 -> x3",
    },
    "straight_draw": {
        "name": "Straight Draw",
        "desc": "Playing a straight draws 2 extra cards",
    },
    "low_power": {
        "name": "Low Power",
        "desc": "Cards numbered 3 or below: multiplier +1.0",
    },
    "glass_cannon": {
        "name": "Glass Cannon",
        "desc": "All damage x1.5, but you take x1.5 damage too",
    },
    "thick_skin": {
        "name": "Thick Skin",
        "desc": "Shield persists between turns (doesn't reset)",
    },
    "combo_chain": {
        "name": "Combo Chain",
        "desc": "If both plays are combos (not singles), +0.5 mult to the 2nd",
    },
}

# ─── Special Cards ───

SPECIAL_TYPES = ["windfall", "bloodpact", "sharpen", "curse", "mirror", "recycle"]
SPECIAL_NAMES = {
    "windfall":  "Windfall",
    "bloodpact": "BloodPact",
    "sharpen":   "Sharpen",
    "curse":     "Curse",
    "mirror":    "Mirror",
    "recycle":   "Recycle",
}
SPECIAL_DESCS = {
    "windfall":  "Draw 2",
    "bloodpact": "Lose HP = card number, draw 3",
    "sharpen":   "+0.5 mult for 2 turns",
    "curse":     "Enemy takes 3 dmg/turn for 3 turns",
    "mirror":    "Copy last combo's damage again",
    "recycle":   "Discard hand, draw 5",
}

# ANSI colors
C = {
    "red": "\033[91m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
}


def colored(text, suit):
    return f"{C.get(suit, '')}{text}{C['reset']}"


def card_str(card):
    if card.function in SPECIAL_NAMES:
        label = f"{SPECIAL_NAMES[card.function]} {card.number}"
    else:
        label = f"{card.function} {card.number}"
    return colored(label, card.suit)


def card_str_short(card):
    return colored(str(card.number), card.suit)


CIRCLED = "①②③④⑤⑥⑦⑧⑨"


def hand_display(cards):
    top_parts = []
    bot_parts = []
    for i, c in enumerate(cards):
        if c.function in SPECIAL_NAMES:
            label = f"{SPECIAL_NAMES[c.function]} {c.number}"
        else:
            label = f"{c.function} {c.number}"
        cell = f"[{label}]"
        top_parts.append(colored(cell, c.suit))
        pad = len(cell)
        num = CIRCLED[i]
        left = pad // 2
        right = pad - left - 1
        bot_parts.append(" " * left + num + " " * right)
    top = "  " + "  ".join(top_parts)
    bot = "  " + "  ".join(bot_parts)
    return top + "\n" + bot


# ─── Deck Generation ───

def make_starting_deck():
    pool = [(s, n) for s in SUITS for n in NUMBERS]
    chosen = random.sample(pool, STARTING_DECK_SIZE)
    deck = []
    for i, (suit, num) in enumerate(chosen):
        if i < 10:
            fn = "atk"
        elif i < 13:
            fn = "def"
        else:
            fn = random.choice(SPECIAL_TYPES)
        deck.append(Card(suit, num, fn))
    random.shuffle(deck)
    return deck


def make_monster_deck():
    pool = [(s, n) for s in SUITS for n in NUMBERS]
    chosen = random.sample(pool, 20)
    deck = []
    for suit, num in chosen:
        fn = random.choice(["atk", "def"])
        deck.append(Card(suit, num, fn))
    random.shuffle(deck)
    return deck


# ─── Combo Detection ───

def detect_combo(cards):
    if len(cards) == 0:
        return "single", 1.0
    if len(cards) == 1:
        return "single", COMBO_MULTIPLIERS["single"]

    suits = [c.suit for c in cards]
    nums = sorted([c.number for c in cards])
    n = len(cards)
    same_suit = len(set(suits)) == 1
    is_consecutive = all(nums[i+1] - nums[i] == 1 for i in range(n - 1))
    num_counts = Counter(nums)

    if n == 5 and same_suit and is_consecutive:
        return "straight_flush_5", COMBO_MULTIPLIERS["straight_flush_5"]
    if n == 4 and same_suit and is_consecutive:
        return "straight_flush_4", COMBO_MULTIPLIERS["straight_flush_4"]
    if n == 3 and same_suit and is_consecutive:
        return "straight_flush_3", COMBO_MULTIPLIERS["straight_flush_3"]

    if n == 3 and any(v >= 3 for v in num_counts.values()):
        return "three_of_kind", COMBO_MULTIPLIERS["three_of_kind"]

    if n == 4 and is_consecutive:
        return "straight_4", COMBO_MULTIPLIERS["straight_4"]
    if n == 4 and same_suit:
        return "flush_4", COMBO_MULTIPLIERS["flush_4"]

    if n == 3 and is_consecutive:
        return "straight_3", COMBO_MULTIPLIERS["straight_3"]
    if n == 3 and same_suit:
        return "flush_3", COMBO_MULTIPLIERS["flush_3"]

    if n == 2 and nums[0] == nums[1]:
        return "pair", COMBO_MULTIPLIERS["pair"]

    if n == 1:
        return "single", COMBO_MULTIPLIERS["single"]

    return None, 0


# ─── Game State ───

SUIT_ORDER = {s: i for i, s in enumerate(SUITS)}


class GameState:
    def __init__(self):
        self.player_hp = PLAYER_MAX_HP
        self.deck = make_starting_deck()
        self.sort_mode = "number"
        self.artifacts = []

    def start_fight(self, fight_num):
        self.fight_num = fight_num
        self.draw_pile = list(self.deck)
        random.shuffle(self.draw_pile)
        self.discard_pile = []
        self.hand = []
        self.shield = 0

        self.monster_hp = MONSTER_BASE_HP
        self.sharpen_turns = 0
        self.curse_turns = 0
        self.last_combo_damage = 0
        self.combos_this_turn = 0
        monster_deck = make_monster_deck()
        self.monster_hand = monster_deck[:MONSTER_STARTING_HAND]
        self.monster_draw_pile = monster_deck[MONSTER_STARTING_HAND:]

    def draw_cards(self, n):
        for _ in range(n):
            if len(self.hand) >= HAND_MAX:
                break
            if not self.draw_pile:
                if not self.discard_pile:
                    break
                self.draw_pile = self.discard_pile[:]
                self.discard_pile = []
                random.shuffle(self.draw_pile)
            self.hand.append(self.draw_pile.pop())
        self.sort_hand()

    def sort_hand(self):
        if self.sort_mode == "number":
            self.hand.sort(key=lambda c: c.number)
        else:
            self.hand.sort(key=lambda c: (SUIT_ORDER[c.suit], c.number))

    def toggle_sort(self):
        self.sort_mode = "suit" if self.sort_mode == "number" else "number"
        self.sort_hand()

    def monster_draw(self):
        for _ in range(MONSTER_DRAW_PER_TURN):
            if self.monster_draw_pile:
                self.monster_hand.append(self.monster_draw_pile.pop())


# ─── Display ───

def display_state(gs):
    gs.sort_hand()
    sort_label = "by number" if gs.sort_mode == "number" else "by suit"
    print()
    print(f"{C['bold']}══════════════════════════════════════{C['reset']}")
    print(f"{C['bold']}  FANG & FLUSH   Fight {gs.fight_num}/{FIGHTS_PER_FLOOR}{C['reset']}")
    print(f"{C['bold']}══════════════════════════════════════{C['reset']}")
    print(f"  YOU: HP {gs.player_hp}/{PLAYER_MAX_HP}  Shield: {gs.shield}")
    if gs.artifacts:
        art_names = [ARTIFACTS[a]["name"] for a in gs.artifacts]
        print(f"  Artifacts: {', '.join(art_names)}")
    print(f"  MONSTER: HP {gs.monster_hp}/{MONSTER_BASE_HP}")
    print(f"──────────────────────────────────────")
    print(f"  Monster hand: " + " ".join(f"[{card_str(c)}]" for c in gs.monster_hand))
    print(f"──────────────────────────────────────")
    print(f"  Your hand ({sort_label}, 's' to toggle):")
    print(hand_display(gs.hand))
    print(f"──────────────────────────────────────")
    print(f"  {C['dim']}Pair=x2  Flush3=x1.5  Str3=x3  Flush4=x2.5  Str4=x4.5")
    print(f"  3oK=x6  StrFl3=x8  StrFl4=x15  StrFl5=x25{C['reset']}")


# ─── Input Helpers ───

def get_action(gs, plays_left, discards_left):
    disc_hint = ' / "d 1 3"discard' if discards_left > 0 else ""
    while True:
        raw = input(f'  "1 2 4"play{disc_hint} / "e"nd / "s"ort / "q"uit: ').strip().lower()
        if raw in ("e", "end"):
            return "done", None
        if raw == "q":
            return "quit", None
        if raw == "s" or raw == "sort":
            gs.toggle_sort()
            sort_label = "by number" if gs.sort_mode == "number" else "by suit"
            print(f"  Sorted {sort_label}:")
            print(hand_display(gs.hand))
            continue
        if raw.startswith("d ") and discards_left <= 0:
            print("  No swaps left.")
            continue
        if raw.startswith("d ") and discards_left > 0:
            try:
                indices = [int(x) - 1 for x in raw[2:].split()]
                if not indices:
                    continue
                if any(i < 0 or i >= len(gs.hand) for i in indices):
                    print("  Invalid card number.")
                    continue
                if len(set(indices)) != len(indices):
                    print("  Duplicate selection.")
                    continue
                return "mulligan", indices
            except ValueError:
                print("  Enter: d 1 2 3")
            continue
        if raw == "d":
            if discards_left > 0:
                print("  Usage: d 1 2 3 (discard cards 1, 2, 3)")
            else:
                print("  No swaps left.")
            continue
        try:
            indices = [int(x) - 1 for x in raw.split()]
            if not indices:
                continue
            if any(i < 0 or i >= len(gs.hand) for i in indices):
                print("  Invalid card number.")
                continue
            if len(set(indices)) != len(indices):
                print("  Duplicate selection.")
                continue
            return "play", indices
        except ValueError:
            print("  Enter numbers separated by spaces.")


def get_discard_input(gs):
    need_discard = len(gs.hand) - HAND_KEEP
    if need_discard <= 0:
        return
    print(f"\n  Discard {need_discard} card(s).")
    print(hand_display(gs.hand))

    while True:
        raw = input(f"  Choose {need_discard} to discard (e.g. \"1 3\"): ").strip()
        try:
            indices = [int(x) - 1 for x in raw.split()]
            if len(indices) != need_discard:
                print(f"  Must choose exactly {need_discard}.")
                continue
            if any(i < 0 or i >= len(gs.hand) for i in indices):
                print("  Invalid card number.")
                continue
            if len(set(indices)) != len(indices):
                print("  Duplicate selection.")
                continue
            for i in sorted(indices, reverse=True):
                gs.discard_pile.append(gs.hand.pop(i))
            return
        except ValueError:
            print("  Enter numbers separated by spaces.")


# ─── Combat ───

COMBO_NAMES = {
    "single": "Single",
    "pair": "Pair",
    "flush_3": "Flush-3",
    "straight_3": "Straight-3",
    "flush_4": "Flush-4",
    "straight_4": "Straight-4",
    "three_of_kind": "Three of a Kind",
    "straight_flush_3": "Straight Flush-3",
    "straight_flush_4": "Straight Flush-4",
    "straight_flush_5": "Straight Flush-5",
}


def play_combo(gs, indices):
    cards = [gs.hand[i] for i in indices]
    combo_type, mult = detect_combo(cards)
    bonus_msgs = []

    # Artifact: pair_boost
    if "pair_boost" in gs.artifacts and combo_type == "pair":
        mult = 3.0
        bonus_msgs.append("Pair Boost: x2 -> x3")

    # Artifact: low_power
    if "low_power" in gs.artifacts:
        low_cards = [c for c in cards if c.number <= 3]
        if low_cards:
            mult += 1.0
            bonus_msgs.append("Low Power: +1.0 mult")

    # Buff: sharpen
    if gs.sharpen_turns > 0:
        mult += 0.5
        bonus_msgs.append(f"Sharpen: +0.5 mult ({gs.sharpen_turns} turns left)")

    # Artifact: combo_chain (2nd play bonus)
    if "combo_chain" in gs.artifacts and gs.combos_this_turn >= 1 and combo_type != "single":
        mult += 0.5
        bonus_msgs.append("Combo Chain: +0.5 mult (2nd combo)")

    atk_sum = sum(c.number for c in cards if c.function == "atk")
    def_sum = sum(c.number for c in cards if c.function == "def")

    damage = int(atk_sum * mult)
    shield = int(def_sum * mult)

    # Artifact: glass_cannon
    if "glass_cannon" in gs.artifacts:
        damage = int(damage * 1.5)
        if damage > 0:
            bonus_msgs.append("Glass Cannon: dmg x1.5")

    name = COMBO_NAMES.get(combo_type, combo_type)
    print(f"\n  >> {name} (x{mult}) — ", end="")
    print(" + ".join(card_str_short(c) for c in cards))
    for msg in bonus_msgs:
        print(f"     {C['bold']}[{msg}]{C['reset']}")

    if damage > 0:
        gs.monster_hp -= damage
        print(f"     Damage: {damage}")
    if shield > 0:
        gs.shield += shield
        print(f"     Shield: +{shield}")

    # Special card effects
    specials = [c for c in cards if c.function in SPECIAL_NAMES]
    for sc in specials:
        if sc.function == "windfall":
            print(f"     {C['bold']}[Windfall: draw 2]{C['reset']}")
        elif sc.function == "bloodpact":
            cost = sc.number
            gs.player_hp -= cost
            print(f"     {C['bold']}[BloodPact: -{cost} HP, draw 3]{C['reset']}")
        elif sc.function == "sharpen":
            gs.sharpen_turns += 2
            print(f"     {C['bold']}[Sharpen: +0.5 mult for 2 turns]{C['reset']}")
        elif sc.function == "curse":
            gs.curse_turns += 3
            print(f"     {C['bold']}[Curse: 3 dmg/turn for 3 turns]{C['reset']}")
        elif sc.function == "mirror":
            mirror_dmg = gs.last_combo_damage
            if mirror_dmg > 0:
                gs.monster_hp -= mirror_dmg
                print(f"     {C['bold']}[Mirror: repeat {mirror_dmg} dmg]{C['reset']}")
            else:
                print(f"     {C['bold']}[Mirror: no previous combo to copy]{C['reset']}")
        elif sc.function == "recycle":
            print(f"     {C['bold']}[Recycle: discard hand, draw 5]{C['reset']}")

    if not specials and damage == 0 and shield == 0:
        print(f"     (no atk/def value)")

    # Artifact: blood_edge
    if "blood_edge" in gs.artifacts and damage > 0:
        heal = max(1, damage // 10)
        gs.player_hp = min(gs.player_hp + heal, PLAYER_MAX_HP)
        print(f"     {C['bold']}[Blood Edge: +{heal} HP]{C['reset']}")

    # Artifact: iron_wall
    if "iron_wall" in gs.artifacts and shield > 0:
        bonus_dmg = max(1, shield * 3 // 10)
        gs.monster_hp -= bonus_dmg
        print(f"     {C['bold']}[Iron Wall: {bonus_dmg} bonus dmg]{C['reset']}")

    gs.last_combo_damage = damage
    if combo_type != "single":
        gs.combos_this_turn += 1

    for i in sorted(indices, reverse=True):
        gs.discard_pile.append(gs.hand.pop(i))

    # Post-removal effects (need hand space)
    if "straight_draw" in gs.artifacts and combo_type.startswith("straight"):
        gs.draw_cards(2)
        print(f"     {C['bold']}[Straight Draw: +2 cards]{C['reset']}")
    for sc in specials:
        if sc.function == "windfall":
            gs.draw_cards(2)
        elif sc.function == "bloodpact":
            gs.draw_cards(3)
        elif sc.function == "recycle":
            while gs.hand:
                gs.discard_pile.append(gs.hand.pop())
            gs.draw_cards(5)


def monster_turn(gs):
    # Curse tick
    if gs.curse_turns > 0:
        gs.monster_hp -= 3
        gs.curse_turns -= 1
        print(f"\n  {C['bold']}[Curse: monster takes 3 dmg ({gs.curse_turns} turns left)]{C['reset']}")
        if gs.monster_hp <= 0:
            return

    gs.monster_draw()

    if not gs.monster_hand:
        print("  Monster has no cards to play.")
        return

    for _ in range(MONSTER_PLAY_PER_TURN):
        if not gs.monster_hand:
            break
        card = random.choice(gs.monster_hand)
        gs.monster_hand.remove(card)

        if card.function == "atk":
            raw_dmg = card.number
            if "glass_cannon" in gs.artifacts:
                raw_dmg = int(raw_dmg * 1.5)
            absorbed = min(gs.shield, raw_dmg)
            gs.shield -= absorbed
            actual = raw_dmg - absorbed
            gs.player_hp -= actual
            print(f"\n  Monster plays {card_str(card)} → {raw_dmg} dmg", end="")
            if absorbed > 0:
                print(f" (shield absorbs {absorbed}, you take {actual})")
            else:
                print()
        else:
            print(f"\n  Monster plays {card_str(card)} → defense (no effect on you)")


# ─── Main Loop ───

def run_fight(gs, fight_num):
    gs.start_fight(fight_num)
    gs.draw_cards(HAND_MAX)
    turn = 0

    while True:
        turn += 1
        if turn > 1:
            gs.draw_cards(HAND_DRAW)

        plays_left = PLAYS_PER_TURN
        discards_left = DISCARDS_PER_TURN
        display_state(gs)

        while plays_left > 0:
            print(f"  [Plays: {plays_left} | Swaps: {discards_left}]")
            action, indices = get_action(gs, plays_left, discards_left)
            if action == "quit":
                return "quit"
            if action == "done":
                break
            if action == "mulligan":
                count = len(indices)
                for i in sorted(indices, reverse=True):
                    gs.discard_pile.append(gs.hand.pop(i))
                gs.draw_cards(count)
                gs.sort_hand()
                discards_left -= 1
                print(f"  Swapped {count} card(s):")
                print(hand_display(gs.hand))
                continue
            cards = [gs.hand[i] for i in indices]
            combo_type, _ = detect_combo(cards)
            if combo_type is None:
                print("  Invalid combo. Single cards must be played one at a time.")
                continue
            play_combo(gs, indices)
            plays_left -= 1
            if gs.monster_hp <= 0:
                break
            if not gs.hand:
                print("  (no cards left)")
                break
            gs.sort_hand()
            print()
            print(hand_display(gs.hand))

        if gs.monster_hp <= 0:
            print(f"\n  {C['bold']}VICTORY!{C['reset']} Monster defeated in {turn} turns.")
            return "win"

        monster_turn(gs)

        if gs.monster_hp <= 0:
            print(f"\n  {C['bold']}VICTORY!{C['reset']} Monster defeated in {turn} turns.")
            return "win"

        if gs.player_hp <= 0:
            print(f"\n  {C['bold']}DEFEATED!{C['reset']} You died on turn {turn}.")
            return "lose"

        if "thick_skin" not in gs.artifacts:
            gs.shield = 0
        if gs.sharpen_turns > 0:
            gs.sharpen_turns -= 1
        gs.combos_this_turn = 0
        get_discard_input(gs)


def choose_artifact(gs, exclude=None):
    available = [k for k in ARTIFACTS if k not in (exclude or [])]
    options = random.sample(available, min(3, len(available)))
    print(f"\n{C['bold']}  Choose an artifact:{C['reset']}")
    for i, key in enumerate(options):
        art = ARTIFACTS[key]
        print(f"   {i+1}. {art['name']} — {art['desc']}")
    valid = [str(i+1) for i in range(len(options))]
    while True:
        raw = input(f"  Pick ({'/'.join(valid)}): ").strip()
        if raw in valid:
            return options[int(raw) - 1]
        print(f"  Enter {', '.join(valid)}.")


def generate_reward_cards():
    cards = []
    for _ in range(3):
        suit = random.choice(SUITS)
        num = random.randint(1, 13)
        fn = random.choices(
            ["atk", "def"] + SPECIAL_TYPES,
            weights=[40, 20] + [8] * len(SPECIAL_TYPES),
        )[0]
        cards.append(Card(suit, num, fn))
    return cards


def post_fight_reward(gs):
    print(f"\n{C['bold']}  REWARD — Choose a card to add to your deck:{C['reset']}")
    options = generate_reward_cards()
    for i, c in enumerate(options):
        desc = ""
        if c.function in SPECIAL_DESCS:
            desc = f" ({SPECIAL_DESCS[c.function]})"
        print(f"   {i+1}. {card_str(c)}{desc}")
    print(f"   4. Skip")
    while True:
        raw = input("  Pick (1/2/3/4): ").strip()
        if raw == "4":
            print("  Skipped.")
            return
        if raw in ("1", "2", "3"):
            chosen = options[int(raw) - 1]
            gs.deck.append(chosen)
            print(f"  Added {card_str(chosen)} to deck. Deck size: {len(gs.deck)}")
            return
        print("  Enter 1, 2, 3, or 4.")


def main():
    print(f"\n{C['bold']}  FANG & FLUSH — Terminal Prototype{C['reset']}")
    print(f"  3 fights, survive them all.\n")

    gs = GameState()
    chosen = choose_artifact(gs)
    gs.artifacts.append(chosen)
    print(f"  Equipped: {ARTIFACTS[chosen]['name']}\n")

    for fight in range(1, FIGHTS_PER_FLOOR + 1):
        print(f"\n{'='*40}")
        print(f"  FIGHT {fight}/{FIGHTS_PER_FLOOR} BEGIN")
        print(f"{'='*40}")

        result = run_fight(gs, fight)

        if result == "quit":
            print("  Goodbye.")
            return
        if result == "lose":
            print(f"\n  GAME OVER — survived {fight - 1}/{FIGHTS_PER_FLOOR} fights.")
            return

        gs.player_hp = min(gs.player_hp + HP_RECOVERY, PLAYER_MAX_HP)
        print(f"  Healed +{HP_RECOVERY} → HP {gs.player_hp}/{PLAYER_MAX_HP}")
        post_fight_reward(gs)

        if fight == FIGHTS_PER_FLOOR:
            new_art = choose_artifact(gs, exclude=gs.artifacts)
            gs.artifacts.append(new_art)
            print(f"  Equipped: {ARTIFACTS[new_art]['name']}")

    print(f"\n{C['bold']}  FLOOR CLEARED!{C['reset']} All {FIGHTS_PER_FLOOR} fights won.")
    print(f"  Final HP: {gs.player_hp}/{PLAYER_MAX_HP}")
    print(f"  Deck: {len(gs.deck)} cards | Artifacts: {', '.join(ARTIFACTS[a]['name'] for a in gs.artifacts)}")


if __name__ == "__main__":
    main()
