import multiprocessing
import numpy as np
import warnings
from collections import deque
import random
import itertools
from multiprocessing import Pool, cpu_count
from numpy import mean
import time
import humanize

from numpy.core.defchararray import endswith

"""
To change counting (balanced/unbalanced):
self.dragon_count
adjust play_dragon
adjust counting method

Dragon unbalanced starting count returns (units/shoe) based on 320 million shoes
-33: 0.600
-32: 0.612988
-31: 0.588

2-card 9/7 unbalanced starting count returns (units/shoe) based on 320 million shoes
-32: 1.30000
-33: 1.31879
-34: 1.33
-35: 1.321
-36: 1.32
-37: 1.29

3-card 9/7 unbalanced starting count returns (units/shoe) based on 320 million shoes
-33/9: 0.645 
-33/2: 0.600
-33/3: 0.580
-33/9: 0.65658
-33/9: 0.65371
-32/9: 0.61884
-34/9: 0.66919
-35/9: 0.639


Balanced: 0.71
"""

SIDE_BETS = {
    'dragon': {
        'payout': 40,
        'starting_count': -32,
        'trigger_count': 0,
        'tags': [0, 1, 0, 0, -1, -1, -1, -1, 2, 2],
        'conditions': (
            (-1, -1, 3, 7, "Banker"),
        )
    },
    'two_card_9_7': {
        'payout': 50,
        'starting_count': -34,
        'trigger_count': 0,
        'tags': [1, 1, 1, 1, 1, 1, 1, -5, 1, -5],
        'conditions': (
            (2, 9, 2, 7, "Player"),
            (2, 7, 2, 9, "Banker")
        )
    },
    'three_card_9_7': {
        'payout': 200,
        'starting_count': -34,
        'trigger_count': 0,
        # 'tags': [1, 1, 0, 0, -1, -2, -1, -2, 1, 1], #original tags
        'tags': [0, 1, 0, 0, -1, -1, -1, -1, 2, 2], #dragon tags
        'conditions': (
            (3, 9, 3, 7, "Player"),
            (3, 7, 3, 9, "Banker")
        )
    }
}

def build_side_bet_dictionary(dictionary : dict):
    side_bet_dict = {}
    for bet in SIDE_BETS:
        for condition in SIDE_BETS[bet]['conditions']:
            p_cards = [2,3] if condition[0] == -1 else [condition[0]]
            p_totals = list(range(0, condition[3])) if condition[1] == -1 else [condition[1]]
            b_cards = [2, 3] if condition[2] == -1 else [condition[2]]
            b_totals = list(range(0, condition[1])) if condition[3] == -1 else [condition[3]]
            for i in p_cards:
                for j in p_totals:
                    for k in b_cards:
                        for l in b_totals:
                            side_bet_dict[(i, j, k, l, condition[4])] = bet

    return side_bet_dict

side_bet_dictionary = build_side_bet_dictionary(SIDE_BETS)

class Shoe():
    def __init__(self):
        self.shoe = self.make_shoe()

        self.hands = 0  # 6
        self.player_wins = 0  # 0
        self.banker_wins = 0  # 1
        self.ties = 0  # 2
        self.dragon_wins = 0  # 3

        self.side_bet_counts = {}

        for side_bet in SIDE_BETS:
            self.side_bet_counts[f'{side_bet}_count'] = SIDE_BETS[side_bet]['starting_count']
            setattr(self, f"{side_bet}_wins", 0)
            setattr(self, f"{side_bet}_bets", 0)
            setattr(self, f"{side_bet}_bets_won", 0)

    def make_shoe(self):
        deck = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 0, 0, 0] * 4
        shoe = deque(deck * 8)  # 6-deck shoe
        random.shuffle(shoe)
        return shoe

    def shoe_complete(self):
        if len(self.shoe) < 14:
            return True
            # self.shoe = self.make_shoe()
        return False

    def draw(self, hand):
        hand.append(self.shoe.popleft())

    def deal_cards(self, player_cards, banker_cards):
        for _ in range(2):
            self.draw(player_cards)
            self.draw(banker_cards)

    def calculate_hand_value(self, player_cards, banker_cards):
        Player_value = sum(player_cards) % 10
        Banker_value = sum(banker_cards) % 10
        return (Player_value, len(player_cards)), (Banker_value, len(banker_cards))

    def check_natural(self, player_cards, banker_cards):
        P_tuple, B_tuple = self.calculate_hand_value(player_cards, banker_cards)
        if (P_tuple[1] == 2 and 8 <= P_tuple[0] <= 9) or  (B_tuple[1] == 2 and 8 <= B_tuple[0] <= 9):
            return True
        return False

    def player_play(self, player_cards):
        if sum(player_cards) % 10 <= 5:
            self.draw(player_cards)

    def banker_play(self, player_cards, banker_cards):
        player_tuple, banker_tuple = self.calculate_hand_value(player_cards, banker_cards)

        if banker_tuple[0] >= 7:
            return
        elif player_tuple[1] == 2 and banker_tuple[0] <= 5:
            self.draw(banker_cards)
            return
        elif player_tuple[1] == 3:
            P_3rd = player_cards[2]
            draw_check = {
                0: True,
                1: True,
                2: True,
                3: True if P_3rd != 8 else False,
                4: True if 2 <= P_3rd <= 7 else False,
                5: True if 4 <= P_3rd <= 7 else False,
                6: True if 6 <= P_3rd <= 7 else False
            }
            if draw_check.get(banker_tuple[0], False):
                self.draw(banker_cards)

    def pay_main(self, player_cards, banker_cards):
        player_tuple, banker_tuple = self.calculate_hand_value(player_cards, banker_cards)
        if player_tuple[0] > banker_tuple[0]:
            self.player_wins += 1
        elif banker_tuple[0] > player_tuple[0] and not (banker_tuple[0] == 7 and banker_tuple[1] == 3):
            self.banker_wins += 1
        elif banker_tuple[0] == player_tuple[0]:
            self.ties += 1
        elif banker_tuple[0] == 7 > player_tuple[0] and banker_tuple[1] == 3:
            self.dragon_wins += 1
            return True
        else:
            raise Exception(f"No hand categorization found. Player: {player_tuple}, Banker: {banker_tuple}")

    # def check_correctness(self, Player, Banker):
    #     if (len(Player) == 3 or len(Banker) == 3) and (8 <= sum(Player[:2]) % 10 <= 9 or 8 <= sum(Banker[:2]) % 10 <= 9):
    #         raise Exception(f"Natural processing error. Player: {Player}, Banker: {Banker}")
    #     if sum(Player[:2]) % 10 > 5 and len(Player) == 3:
    #         raise Exception(f"Player draw error. Player: {Player}, Banker: {Banker}")
    #     if len(Banker) == 3:
    #         if len(Player) == 2:
    #             if sum(Banker[:2]) % 10 > 5:
    #                 raise Exception(f"Banker draw error. Player: {Player}, Banker: {Banker}")
    #         elif len(Player) == 3:
    #             if sum(Banker[:2]) % 10 == 3 and Player[2] in [8]:
    #                 raise Exception(f"Banker draw error. Player: {Player}, Banker: {Banker}")
    #             elif sum(Banker[:2]) % 10 == 4 and Player[2] in [0, 1, 8, 9]:
    #                 raise Exception(f"Banker draw error. Player: {Player}, Banker: {Banker}")
    #             elif sum(Banker[:2]) % 10 == 5 and Player[2] in [0, 1, 2, 3, 8, 9]:
    #                 raise Exception(f"Banker draw error. Player: {Player}, Banker: {Banker}")
    #             elif sum(Banker[:2]) % 10 == 6 and Player[2] in [0, 1, 2, 3, 4, 5, 8, 9]:
    #                 raise Exception(f"Banker draw error. Player: {Player}, Banker: {Banker}")
    #             elif sum(Banker[:2]) % 10 in [7, 8, 9]:
    #                 raise Exception(f"Banker draw error. Player: {Player}, Banker: {Banker}")

    def update_side_bet_counts(self, player_cards, banker_cards):
        cards = player_cards + banker_cards
        for side_bet in self.side_bet_counts:
            for card in cards:
                self.side_bet_counts[side_bet] += SIDE_BETS[side_bet.removesuffix("_count")]['tags'][card]

    def play_side_bets(self):
        side_bets = []
        for side_bet in self.side_bet_counts:
            side_bet_name = side_bet.removesuffix("_count")
            if self.side_bet_counts[side_bet] >= SIDE_BETS[side_bet_name]['trigger_count']:
                side_bets.append(side_bet_name)
                setattr(self, f"{side_bet_name}_bets", getattr(self, f"{side_bet_name}_bets") + 1)
        return side_bets

    def pay_side_bets(self, player_cards, banker_cards, side_bets_played):
        player_tuple, banker_tuple = self.calculate_hand_value(player_cards, banker_cards)
        if player_tuple[0] > banker_tuple[0]:
            winner = "Player"
        elif banker_tuple[0] > player_tuple[0]:
            winner = "Banker"
        else:
            winner = "Tie"

        hand_signature = (player_tuple[1], player_tuple[0], banker_tuple[1], banker_tuple[0], winner)
        side_bet = side_bet_dictionary.get(hand_signature, False)

        if side_bet in side_bets_played:
            setattr(self, f"{side_bet}_bets_won", getattr(self, f"{side_bet}_bets_won") + 1)

        if side_bet not in ["dragon", False]:
            setattr(self, f"{side_bet}_wins", getattr(self, f"{side_bet}_wins") + 1)


    def end_game(self, player_cards, banker_cards, sides):
        self.pay_main(player_cards, banker_cards)
        self.pay_side_bets(player_cards, banker_cards, sides)
        self.update_side_bet_counts(player_cards, banker_cards)
        # self.check_correctness(Player, Banker)
        self.hands += 1

    def play(self):
        side_bets = self.play_side_bets()

        player_cards = []
        banker_cards = []
        self.deal_cards(player_cards, banker_cards)

        if self.check_natural(player_cards, banker_cards):
            self.end_game(player_cards, banker_cards, side_bets)
            return

        self.player_play(player_cards)
        self.banker_play(player_cards, banker_cards)

        self.end_game(player_cards, banker_cards, side_bets)

    def play_shoe(self):
        while not self.shoe_complete():
            self.play()
        # return (self.player_wins, self.banker_wins, self.ties, self.dragon_wins,
        #         self.two_card_9_7, self.three_card_9_7, self.hands, self.dragon_bets,
        #         self.dragon_bets_won, self.two_card_9_7_bets, self.two_card_9_7_bets_won, self.three_card_9_7_bets,
        #         self.three_card_9_7_bets_won)
        # print(self.shoe)

        # draw cards
        # check cards
        # check if player draw
        # check if dealer draw


class Simulation():
    def __init__(self, shoes):
        self.shoes = shoes
        temp_instance = Shoe()
        for attr in vars(temp_instance):
            if not attr.endswith("_counts") and attr != 'shoe':
                setattr(self, attr, 0)

    def run_simulation(self):
        for _ in range(self.shoes):
            shoe = Shoe()
            shoe.play_shoe()

            for attr in [var for var in vars(self) if var != 'shoes']:
                self.__dict__[attr] += shoe.__dict__[attr]

def main_function(_):
    sim = Simulation(1000000)
    sim.run_simulation()
    return vars(sim)

def run_simulation_n_times(n):
    with multiprocessing.Pool() as pool:
        simulation_results = pool.map(main_function, range(n))

    return_results = {}

    for result in simulation_results:
        for key, value in result.items():
            if key in return_results:
                return_results[key] += value
            else:
                return_results[key] = value

    return return_results


def print_results(results, elapsed):
    # Calculate the maximum length of the keys (with formatting) to align them to the right
    key_width = 1 + max(len(key.capitalize().replace('_', ' ')) for key in results.keys()
                    if not key.endswith('_bets') and not key.endswith('_bets_won') and key not in ['shoes', 'hands'])

    # Print the predefined results with proper alignment
    print(f"=======Baccarat Monte Carlo Simulation Results=======")

    print(f"{'Shoes:':>{key_width}} {humanize.intword(results['shoes'])}")
    print(f"{'Hands:':>{key_width}} {humanize.intword(results['hands'])}")
    print(f"{'Completed in:':>{key_width}} {elapsed}s")

    print("")

    # Calculate the maximum width of the fraction for proper alignment of the closing parenthesis
    max_fraction_width = max(len(f"{value}/{results['hands']}") for key, value in results.items()
                            if not key.endswith('_bets') and not key.endswith('_bets_won') and key not in ['shoes', 'hands'])

    # Find the maximum length of the formatted keys to align the parentheses
    for key, value in results.items():
        if not key.endswith("_bets") and not key.endswith("_bets_won") and key not in ['shoes', 'hands']:
            # Capitalize and replace underscores with spaces in the key
            formatted_key = key.capitalize().replace('_', ' ')
            # Format the value as a percentage
            value_percentage = value / results['hands'] * 100
            value_str = f"{value}/{results['hands']}"

            # Print the key and the formatted result with alignment for the closing parenthesis
            print(f"{formatted_key + ':':>{key_width}} {value_percentage:>6.2f}%    ({value_str:>{max_fraction_width}})")

    print("")
    for side_bet in SIDE_BETS:
        bets = results[f'{side_bet}_bets']
        bets_won = results[f'{side_bet}_bets_won']
        bets_lost = bets - bets_won

        bet_payout = SIDE_BETS[side_bet]['payout']
        bet_return = bets_lost * -1 + bets_won * bet_payout
        bet_return_units_per_shoe = bet_return / results['shoes']

        if bet_return_units_per_shoe > 0:
            bet_return_units_per_shoe_string = f"+{bet_return_units_per_shoe:.3f}"
        else:
            bet_return_units_per_shoe_string = f"{bet_return_units_per_shoe}"

        side_bet_name = side_bet.capitalize().replace('_', ' ')

        bets_percentage = bets / results['hands'] * 100
        bets_fraction_string = f"{bets}/{results['hands']}"

        bets_won_percentage = bets_won / bets * 100
        bets_won_percentage_string = f"{bets_won}/{bets}"

        print(f"{side_bet_name + ':':>{key_width}} {bet_return_units_per_shoe_string:>7} {'units per shoe':>17}")
        print(f"{'Bets:':>{key_width}} {bets_percentage:>6.2f}%    ({bets_fraction_string:>{max_fraction_width}})")
        print(f"{'Bets won:':>{key_width}} {bets_won_percentage:>6.2f}%    ({bets_won_percentage_string:>{max_fraction_width}})")
        print(f"{'Tags (0-9):':>{key_width}} {SIDE_BETS[side_bet]['tags']}")

        print("")
        # print(f"{side_bet_name} units won per shoe: {bet_return_units_per_shoe}")


#bets
#bets won

if '__main__' == __name__:
    # main = main_function(None)
    # print(vars(main))
    start = time.time()
    results = run_simulation_n_times(32)
    end = time.time()
    elapsed = end - start
    print_results(results, elapsed)


