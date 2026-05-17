#!/usr/bin/env python3
"""Balance simulator — run thousands of AI games to find optimal constants."""

import random
from collections import Counter, namedtuple
from itertools import combinations

from constants import (
    PLAYER_MAX_HP, HP_RECOVERY, HAND_DRAW, HAND_MAX, HAND_KEEP,
    PLAYS_PER_TURN, DISCARDS_PER_TURN, STARTING_DECK_SIZE,
    SUITS, NUMBERS, COMBO_MULTIPLIERS,
    MONSTER_STARTING_HAND, MONSTER_DRAW_PER_TURN, MONSTER_PLAY_PER_TURN,
    MONSTER_BASE_HP, BOSS_HP, FIGHTS_PER_FLOOR,
)

Card = namedtuple("Card", ["suit", "number", "function"])
SPECIAL_TYPES = ["windfall", "bloodpact", "sharpen", "curse", "mirror", "recycle"]
MONSTER_SPECIAL_TYPES = ["heavy", "mend", "rage", "armor"]

SIMS = 5000


def detect_combo(cards):
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
    return None, 0


def find_best_combos(hand):
    best = []
    for size in range(min(5, len(hand)), 0, -1):
        for group in combinations(range(len(hand)), size):
            cards = [hand[i] for i in group]
            ctype, mult = detect_combo(cards)
            if ctype is None:
                continue
            atk_sum = sum(c.number for c in cards if c.function == "atk")
            dmg = atk_sum * mult
            best.append((dmg, mult, ctype, list(group), cards))
    best.sort(reverse=True)
    return best


def make_deck():
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
    return deck


def make_monster_deck(is_boss=False):
    pool = [(s, n) for s in SUITS for n in NUMBERS]
    chosen = random.sample(pool, 20)
    deck = []
    special_pct = 50 if is_boss else 20
    for suit, num in chosen:
        if random.randint(1, 100) <= special_pct:
            fn = random.choice(MONSTER_SPECIAL_TYPES)
        else:
            fn = random.choice(["atk", "def"])
        deck.append(Card(suit, num, fn))
    random.shuffle(deck)
    return deck


def sim_fight(deck, player_hp, is_boss=False):
    draw_pile = list(deck)
    random.shuffle(draw_pile)
    discard_pile = []
    hand = []
    shield = 0
    monster_hp = BOSS_HP if is_boss else MONSTER_BASE_HP
    monster_max_hp = monster_hp
    monster_rage = False
    sharpen_turns = 0
    curse_turns = 0

    mdeck = make_monster_deck(is_boss)
    monster_hand = mdeck[:MONSTER_STARTING_HAND]
    monster_draw = mdeck[MONSTER_STARTING_HAND:]

    turns = 0
    combo_types_used = Counter()
    total_damage_dealt = 0
    total_damage_taken = 0

    def draw_cards(n):
        nonlocal hand, draw_pile, discard_pile
        for _ in range(n):
            if len(hand) >= HAND_MAX:
                break
            if not draw_pile:
                if not discard_pile:
                    break
                draw_pile = discard_pile[:]
                discard_pile = []
                random.shuffle(draw_pile)
            hand.append(draw_pile.pop())

    draw_cards(HAND_MAX)

    while True:
        turns += 1
        if turns > 1:
            draw_cards(HAND_DRAW)

        # AI: discard worst cards (lowest atk value)
        for _ in range(DISCARDS_PER_TURN):
            if len(hand) <= 3:
                break
            combos_before = find_best_combos(hand)
            best_before = combos_before[0][0] if combos_before else 0
            worst_idx = None
            worst_val = float('inf')
            for i, c in enumerate(hand):
                test_hand = hand[:i] + hand[i+1:]
                test_combos = find_best_combos(test_hand)
                test_best = test_combos[0][0] if test_combos else 0
                loss = best_before - test_best
                if loss < worst_val:
                    worst_val = loss
                    worst_idx = i
            if worst_idx is not None and worst_val <= 0:
                discard_pile.append(hand.pop(worst_idx))
                draw_cards(1)

        # AI: play best combos
        for _ in range(PLAYS_PER_TURN):
            if not hand:
                break
            combos = find_best_combos(hand)
            if not combos:
                break
            dmg, mult, ctype, indices, cards = combos[0]

            atk_sum = sum(c.number for c in cards if c.function == "atk")
            def_sum = sum(c.number for c in cards if c.function == "def")

            actual_mult = mult
            if sharpen_turns > 0:
                actual_mult += 0.5

            damage = int(atk_sum * actual_mult)
            shld = int(def_sum * actual_mult)

            monster_hp -= damage
            shield += shld
            total_damage_dealt += damage
            combo_types_used[ctype] += 1

            for i in sorted(indices, reverse=True):
                discard_pile.append(hand.pop(i))

            if monster_hp <= 0:
                break

        if monster_hp <= 0:
            return {
                "result": "win", "turns": turns, "hp": player_hp,
                "damage_dealt": total_damage_dealt,
                "damage_taken": total_damage_taken,
                "combos": combo_types_used,
            }

        # Curse tick
        if curse_turns > 0:
            monster_hp -= 3
            curse_turns -= 1
            if monster_hp <= 0:
                return {
                    "result": "win", "turns": turns, "hp": player_hp,
                    "damage_dealt": total_damage_dealt,
                    "damage_taken": total_damage_taken,
                    "combos": combo_types_used,
                }

        # Monster turn
        if monster_draw:
            monster_hand.append(monster_draw.pop())

        if monster_hand:
            card = random.choice(monster_hand)
            monster_hand.remove(card)

            if card.function == "atk":
                raw_dmg = card.number * 2
                if monster_rage:
                    raw_dmg *= 2
                    monster_rage = False
                absorbed = min(shield, raw_dmg)
                shield -= absorbed
                actual = raw_dmg - absorbed
                player_hp -= actual
                total_damage_taken += actual
            elif card.function == "heavy":
                raw_dmg = card.number * 3
                if monster_rage:
                    raw_dmg *= 2
                    monster_rage = False
                absorbed = min(shield, raw_dmg)
                shield -= absorbed
                actual = raw_dmg - absorbed
                player_hp -= actual
                total_damage_taken += actual
            elif card.function == "mend":
                monster_hp = min(monster_hp + card.number * 2, monster_max_hp)
            elif card.function == "rage":
                monster_rage = True

        if player_hp <= 0:
            return {
                "result": "lose", "turns": turns, "hp": 0,
                "damage_dealt": total_damage_dealt,
                "damage_taken": total_damage_taken,
                "combos": combo_types_used,
            }

        shield = 0
        if sharpen_turns > 0:
            sharpen_turns -= 1

        # Discard to HAND_KEEP
        hand.sort(key=lambda c: c.number, reverse=True)
        while len(hand) > HAND_KEEP:
            discard_pile.append(hand.pop())

        if turns > 50:
            return {
                "result": "stall", "turns": turns, "hp": player_hp,
                "damage_dealt": total_damage_dealt,
                "damage_taken": total_damage_taken,
                "combos": combo_types_used,
            }


def sim_run():
    deck = make_deck()
    player_hp = PLAYER_MAX_HP
    fights_won = 0

    for fight in range(1, FIGHTS_PER_FLOOR + 1):
        result = sim_fight(deck, player_hp)
        player_hp = result["hp"]

        if result["result"] != "win":
            return {
                "fights_won": fights_won,
                "final_hp": 0,
                "result": "lose",
                "fight_results": result,
            }

        fights_won += 1
        player_hp = min(player_hp + HP_RECOVERY, PLAYER_MAX_HP)

    # Boss fight
    result = sim_fight(deck, player_hp, is_boss=True)
    player_hp = result["hp"]

    if result["result"] == "win":
        return {
            "fights_won": fights_won + 1,
            "final_hp": player_hp,
            "result": "win",
            "boss_turns": result["turns"],
        }
    else:
        return {
            "fights_won": fights_won,
            "final_hp": 0,
            "result": "lose_boss",
            "boss_turns": result["turns"],
        }


def main():
    print(f"BALANCE SIMULATOR — {SIMS:,} runs")
    print(f"{'='*55}")
    print(f"  Player: HP={PLAYER_MAX_HP}, Recovery={HP_RECOVERY}")
    print(f"  Hand: draw={HAND_DRAW}, max={HAND_MAX}, keep={HAND_KEEP}")
    print(f"  Plays={PLAYS_PER_TURN}, Discards={DISCARDS_PER_TURN}")
    print(f"  Monster HP={MONSTER_BASE_HP}, Boss HP={BOSS_HP}")
    print(f"  Fights per floor={FIGHTS_PER_FLOOR}")
    print(f"{'='*55}\n")

    wins = 0
    losses = 0
    boss_losses = 0
    total_fights = Counter()
    final_hps = []
    boss_turns_list = []
    fight_dmg_dealt = []
    fight_dmg_taken = []

    for _ in range(SIMS):
        r = sim_run()
        total_fights[r["fights_won"]] += 1

        if r["result"] == "win":
            wins += 1
            final_hps.append(r["final_hp"])
            boss_turns_list.append(r.get("boss_turns", 0))
        elif r["result"] == "lose_boss":
            boss_losses += 1
        else:
            losses += 1

    print(f"  RESULTS:")
    print(f"  Floor clear rate: {wins/SIMS*100:.1f}%")
    print(f"  Die to normal monsters: {losses/SIMS*100:.1f}%")
    print(f"  Die to boss: {boss_losses/SIMS*100:.1f}%")
    print()

    print(f"  FIGHTS WON DISTRIBUTION:")
    for i in range(FIGHTS_PER_FLOOR + 2):
        count = total_fights.get(i, 0)
        pct = count / SIMS * 100
        bar = "█" * int(pct / 2)
        print(f"    {i} fights: {pct:5.1f}% {bar}")
    print()

    if final_hps:
        avg_hp = sum(final_hps) / len(final_hps)
        min_hp = min(final_hps)
        max_hp = max(final_hps)
        print(f"  WINNERS HP: avg={avg_hp:.0f}, min={min_hp}, max={max_hp}")

    if boss_turns_list:
        avg_bt = sum(boss_turns_list) / len(boss_turns_list)
        print(f"  BOSS FIGHT: avg turns={avg_bt:.1f}")

    print()

    # Run single fight sim for detailed stats
    print(f"  SINGLE FIGHT DETAILS (1000 sims, normal monster):")
    fight_turns = []
    fight_dmg = []
    fight_taken = []
    combo_totals = Counter()
    for _ in range(1000):
        r = sim_fight(make_deck(), PLAYER_MAX_HP)
        fight_turns.append(r["turns"])
        fight_dmg.append(r["damage_dealt"])
        fight_taken.append(r["damage_taken"])
        combo_totals.update(r["combos"])

    avg_turns = sum(fight_turns) / len(fight_turns)
    avg_dmg = sum(fight_dmg) / len(fight_dmg)
    avg_taken = sum(fight_taken) / len(fight_taken)
    print(f"    Avg turns per fight: {avg_turns:.1f}")
    print(f"    Avg damage dealt: {avg_dmg:.0f}")
    print(f"    Avg damage taken: {avg_taken:.0f}")
    print()

    print(f"  COMBO USAGE (per fight):")
    names = {
        "single": "Single", "pair": "Pair", "flush_3": "Flush-3",
        "straight_3": "Str-3", "flush_4": "Flush-4", "straight_4": "Str-4",
        "three_of_kind": "3oK", "straight_flush_3": "StrFl-3",
        "straight_flush_4": "StrFl-4", "straight_flush_5": "StrFl-5",
    }
    for ctype in ["single", "pair", "flush_3", "straight_3", "flush_4",
                   "straight_4", "three_of_kind", "straight_flush_3",
                   "straight_flush_4", "straight_flush_5"]:
        count = combo_totals.get(ctype, 0)
        per_fight = count / 1000
        print(f"    {names.get(ctype, ctype):10s} {per_fight:.2f}/fight")

    # Balance verdict
    print(f"\n{'='*55}")
    print(f"  BALANCE VERDICT")
    print(f"{'='*55}")
    clear_rate = wins / SIMS * 100
    if clear_rate > 80:
        print(f"  ⚠ Too easy ({clear_rate:.0f}% clear) — raise monster HP or damage")
    elif clear_rate < 30:
        print(f"  ⚠ Too hard ({clear_rate:.0f}% clear) — lower monster HP or raise recovery")
    else:
        print(f"  ✓ Balanced ({clear_rate:.0f}% clear rate)")

    if avg_turns < 2:
        print(f"  ⚠ Fights too short ({avg_turns:.1f} turns) — raise monster HP")
    elif avg_turns > 6:
        print(f"  ⚠ Fights too long ({avg_turns:.1f} turns) — lower monster HP")
    else:
        print(f"  ✓ Fight length OK ({avg_turns:.1f} turns)")

    if final_hps and avg_hp > 60:
        print(f"  ⚠ Winners too healthy ({avg_hp:.0f} HP) — raise difficulty")
    elif final_hps and avg_hp < 15:
        print(f"  ⚠ Winners barely alive ({avg_hp:.0f} HP) — lower difficulty slightly")
    else:
        print(f"  ✓ Winner HP OK ({avg_hp:.0f} avg)")


if __name__ == "__main__":
    main()
