import multiprocessing
import numpy as np
import warnings
from collections import deque
import random
import itertools
from multiprocessing import Pool, cpu_count
from numpy import mean
import time

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


class Shoe():
    def __init__(self):
        self.shoe = self.make_shoe()

        self.player_wins = 0  # 0
        self.banker_wins = 0  # 1
        self.ties = 0  # 2
        self.dragon_wins = 0  # 3
        self.two_card_97 = 0  # 4
        self.three_card_97 = 0  # 5
        self.hands = 0  # 6

        self.dragon_count = -32
        # self.dragon_count = 0
        self.dragon_bets = 0  # 7
        self.dragon_bets_won = 0  # 8

        self.two_card_97_count = -34
        # self.two_card_97_count = 0
        self.two_card_97_bets = 0  # 9
        self.two_card_97_bets_won = 0  # 10

        self.three_card_97_count = -34
        self.three_card_97_bets = 0  # 11
        self.three_card_97_bets_won = 0  # 12

    def make_shoe(self):
        deck = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 0, 0, 0, ] * 4
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

    def deal_cards(self, Player, Banker):
        for _ in range(2):
            self.draw(Player)
            self.draw(Banker)

    def calculate_hand_value(self, Player, Banker):
        Player_value = sum(Player) % 10
        Banker_value = sum(Banker) % 10
        return (Player_value, len(Player)), (Banker_value, len(Banker))

    def check_natural(self, Player, Banker):
        P_tuple, B_tuple = self.calculate_hand_value(Player, Banker)
        if (P_tuple[1] == 2 and 8 <= P_tuple[0] <= 9) or (B_tuple[1] == 2 and 8 <= B_tuple[0] <= 9):
            return True
        return False

    def Player_play(self, Player):
        if sum(Player) % 10 <= 5:
            self.draw(Player)

    def Banker_play(self, Player, Banker):
        P_tuple, B_tuple = self.calculate_hand_value(Player, Banker)

        if B_tuple[0] >= 7:
            return
        elif P_tuple[1] == 2 and B_tuple[0] <= 5:
            self.draw(Banker)
            return
        elif P_tuple[1] == 3:
            P_3rd = Player[2]
            draw_check = {
                0: True,
                1: True,
                2: True,
                3: True if P_3rd != 8 else False,
                4: True if 2 <= P_3rd <= 7 else False,
                5: True if 4 <= P_3rd <= 7 else False,
                6: True if 6 <= P_3rd <= 7 else False
            }
            if draw_check.get(B_tuple[0], False):
                self.draw(Banker)

    def pay_main(self, Player, Banker):
        P_tuple, B_tuple = self.calculate_hand_value(Player, Banker)
        if P_tuple[0] > B_tuple[0]:
            # print(f"Player wins with a {P_tuple[1]}-card {P_tuple[0]} against a Banker {B_tuple[1]}-card {B_tuple[0]}!")
            self.player_wins += 1
        elif B_tuple[0] > P_tuple[0] and not (B_tuple[0] == 7 and B_tuple[1] == 3):
            # print(f"Banker wins with a {B_tuple[1]}-card {B_tuple[0]} against a Player {P_tuple[1]}-card {P_tuple[0]}!")
            self.banker_wins += 1
        elif B_tuple[0] == P_tuple[0]:
            """
            This must go before dragon is computed, 
            or else an additional condition will have to be 
            checked in checking the dragon win in order to ensure
            that it is not a tie (2-card player 7 v. 3-card banker 7)
            """
            # print(f"Tie with a Player {P_tuple[1]}-card {P_tuple[0]} and a Banker {B_tuple[1]}-card {B_tuple[0]}!")
            self.ties += 1
        elif B_tuple[0] == 7 and B_tuple[1] == 3:
            # print(f"Dragon wins with a {B_tuple[1]}-card {B_tuple[0]} against a Player {P_tuple[1]}-card {P_tuple[0]}!")
            self.dragon_wins += 1
            return True
        else:
            raise Exception(f"No hand categorization found. Player: {P_tuple}, Banker: {B_tuple}")

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

    def update_dragon_count(self, Player, Banker):
        cards = Player + Banker
        for card in cards:
            if card == 1:
                self.dragon_count += 1
                # self.dragon_count += 0
            elif card in [4, 5, 6, 7]:
                self.dragon_count -= 1
            elif card in [8, 9]:
                self.dragon_count += 2

    def play_dragon(self):
        if self.dragon_count >= 0:
            return True
        return False
        #
        #
        # true_count = self.dragon_count / (len(self.shoe)/52)
        # if true_count >= 4:
        #     return True
        # return False

    def update_two_card_97_count(self, Player, Banker):
        cards = Player + Banker
        for card in cards:
            if card in [1, 2, 3, 4, 5, 6, 8, 0]:  # adjusted 1 to add 1 for unbalanced count
                self.two_card_97_count += 1
            elif card in [7, 9]:
                self.two_card_97_count -= 5

    def play_two_card_97(self):
        if self.two_card_97_count >= 0:
            return True
        return False
        #
        # true_count = self.two_card_97_count / (len(self.shoe)/52)
        # if true_count >= 6:
        #     return True
        # return False

    def update_three_card_97_count(self, Player, Banker):
        cards = Player + Banker
        for card in cards:
            if card in [1, 8, 0, 9]:  # 9, 2, 3
                self.three_card_97_count += 1
            elif card in [4, 6]:
                self.three_card_97_count -= 1
            elif card in [5, 7]:
                self.three_card_97_count -= 2

    def play_three_card_97(self):
        if self.three_card_97_count >= 0:
            return True
        return False

        # true_count = self.three_card_97_count / (len(self.shoe) / 52)
        # if true_count >= 5:
        #     return True
        # return False

    def pay_sides(self, Player, Banker, sides):
        P_tuple, B_tuple = self.calculate_hand_value(Player, Banker)
        if B_tuple[0] == 7 and B_tuple[1] == 3 and B_tuple[0] > P_tuple[0] and sides[0] == True:
            # print(f"Dragon wins with a {B_tuple[1]}-card {B_tuple[0]} against a Player {P_tuple[1]}-card {P_tuple[0]}!")
            self.dragon_bets_won += 1
        if ((B_tuple[0] == 7 and P_tuple[0] == 9) or (B_tuple[0] == 9 and P_tuple[0] == 7)) and B_tuple[1] == 2 and \
                P_tuple[1] == 2:
            if sides[1] == True:
                self.two_card_97_bets_won += 1
            self.two_card_97 += 1
        if ((B_tuple[0] == 7 and P_tuple[0] == 9) or (B_tuple[0] == 9 and P_tuple[0] == 7)) and B_tuple[1] == 3 and \
                P_tuple[1] == 3:
            if sides[2] == True:
                self.three_card_97_bets_won += 1
            self.three_card_97 += 1

    def end_game(self, Player, Banker, sides):
        self.pay_main(Player, Banker)
        self.pay_sides(Player, Banker, sides)
        self.update_dragon_count(Player, Banker)
        self.update_two_card_97_count(Player, Banker)
        self.update_three_card_97_count(Player, Banker)
        # self.check_correctness(Player, Banker)
        self.hands += 1

    def play(self):
        side_bets = [False] * 3

        if self.play_dragon():
            side_bets[0] = True
            self.dragon_bets += 1

        if self.play_two_card_97():
            side_bets[1] = True
            self.two_card_97_bets += 1

        if self.play_three_card_97():
            side_bets[2] = True
            self.three_card_97_bets += 1

        Player = []
        Banker = []
        self.deal_cards(Player, Banker)

        if self.check_natural(Player, Banker):
            self.end_game(Player, Banker, side_bets)
            return

        self.Player_play(Player)
        self.Banker_play(Player, Banker)

        self.end_game(Player, Banker, side_bets)

    def play_shoe(self):
        while not self.shoe_complete():
            self.play()
        return (self.player_wins, self.banker_wins, self.ties, self.dragon_wins,
                self.two_card_97, self.three_card_97, self.hands, self.dragon_bets,
                self.dragon_bets_won, self.two_card_97_bets, self.two_card_97_bets_won, self.three_card_97_bets,
                self.three_card_97_bets_won)
        # print(self.shoe)

        # draw cards
        # check cards
        # check if player draw
        # check if dealer draw


class Simulation():
    def __init__(self, shoes):
        self.shoes = shoes

        self.player_total = 0
        self.banker_total = 0
        self.tie_total = 0
        self.dragon_total = 0
        self.two_card_97_total = 0
        self.three_card_97_total = 0
        self.hands_total = 0

        self.dragon_bets_total = 0
        self.dragon_bets_won_total = 0

        self.two_card_97_bets_total = 0
        self.two_card_97_bets_won_total = 0

        self.three_card_97_bets_total = 0
        self.three_card_97_bets_won_total = 0

    def run_simulation(self):
        for _ in range(self.shoes):
            shoe = Shoe()
            result = shoe.play_shoe()

            self.player_total += result[0]
            self.banker_total += result[1]
            self.tie_total += result[2]
            self.dragon_total += result[3]
            self.two_card_97_total += result[4]
            self.three_card_97_total += result[5]
            self.hands_total += result[6]

            self.dragon_bets_total += result[7]
            self.dragon_bets_won_total += result[8]

            self.two_card_97_bets_total += result[9]
            self.two_card_97_bets_won_total += result[10]

            self.three_card_97_bets_total += result[11]
            self.three_card_97_bets_won_total += result[12]

    def compute_data(self):
        # print(f"Player {self.player_total/self.hand_total} ({self.player_total}/{self.hand_total})")
        # print(f"Banker {self.banker_total/self.hand_total} ({self.banker_total}/{self.hand_total})")
        # print(f"Tie {self.tie_total/self.hand_total} ({self.tie_total}/{self.hand_total})")
        # print(f"Dragon {self.dragon_total/self.hand_total} ({self.dragon_total}/{self.hand_total})")
        # print(f"Hands {self.hand_total/self.hand_total} ({self.hand_total}/{self.hand_total})")

        return [self.player_total, self.banker_total, self.tie_total, self.dragon_total, self.two_card_97_total,
                self.three_card_97_total, self.hands_total, self.dragon_bets_total, self.dragon_bets_won_total,
                self.two_card_97_bets_total, self.two_card_97_bets_won_total, self.three_card_97_bets_total,
                self.three_card_97_bets_won_total]


def multi_function(_):
    sim = Simulation(1000000)
    sim.run_simulation()
    return sim.compute_data()


def run_simulation_n_times(n):
    with multiprocessing.Pool() as pool:
        results = pool.map(multi_function, range(n))
    return np.array(results)


if '__main__' == __name__:
    start = time.time()
    results = run_simulation_n_times(32)
    end = time.time()
    combined = results.sum(axis=0)
    shoes = 1000000 * 32

    player = combined[0]
    banker = combined[1]
    tie = combined[2]
    dragon = combined[3]
    two_card_97 = combined[4]
    three_card_97 = combined[5]
    hands = combined[6]

    dragon_bets = combined[7]
    dragon_bets_won = combined[8]

    two_card_97_bets = combined[9]
    two_card_97_bets_won = combined[10]

    three_card_97_bets = combined[11]
    three_card_97_bets_won = combined[12]

    dragon_bets_lost = dragon_bets - dragon_bets_won
    dragon_profit = dragon_bets_lost * -1 + dragon_bets_won * 40
    dragon_units_per_shoe = dragon_profit / shoes

    two_card_97_bets_lost = two_card_97_bets - two_card_97_bets_won
    two_card_97_profit = two_card_97_bets_lost * -1 +  two_card_97_bets_won * 50
    two_card_97_units_per_shoe = two_card_97_profit / shoes

    three_card_97_bets_lost = three_card_97_bets - three_card_97_bets_won
    three_card_97_profit = three_card_97_bets_lost * -1 + three_card_97_bets_won * 200
    three_card_97_units_per_shoe = three_card_97_profit / shoes

    print(f"Number of shoes simulated: {shoes:,}")
    print(f"Simulation completed in {end - start:.2f}s")

    print("")
    print(f"Player {player/hands} ({player}/{hands})")
    print(f"Banker {banker/hands} ({banker}/{hands})")
    print(f"Tie {tie/hands} ({tie}/{hands})")
    print(f"Dragon {dragon/hands} ({dragon}/{hands})")
    print(f"2-card 9/7 {two_card_97/hands} ({two_card_97}/{hands})")
    print(f"3-card 9/7 {three_card_97/hands} ({three_card_97}/{hands})")

    print("")

    print(f"Dragon bets {dragon_bets/hands} ({dragon_bets}/{hands})")
    print(f"Dragon bets won {dragon_bets_won/dragon_bets} ({dragon_bets_won}/{dragon_bets})")
    print(f"Dragon units won per shoe {dragon_units_per_shoe}")

    print("")

    print(f"2-card 9/7 bets {two_card_97_bets/hands} ({two_card_97_bets}/{hands})")
    print(f"2-card 9/7 bets won {two_card_97_bets_won/two_card_97_bets} ({two_card_97_bets_won}/{two_card_97_bets})")
    print(f"2-card 9/7 units won per shoe {two_card_97_units_per_shoe}")

    print("")

    print(f"3-card 9/7 bets {three_card_97_bets/hands} ({three_card_97_bets}/{hands})")
    print(f"3-card 9/7 bets won {three_card_97_bets_won/three_card_97_bets} ({three_card_97_bets_won}/{three_card_97_bets})")
    print(f"3-card 9/7 units won per shoe {three_card_97_units_per_shoe}")

    # print(f"Dragon bets {combined[6]/combined[5]} ({combined[6]}/{combined[5]})")
    # print(f"Dragon bets won {combined[7]/combined[6]} ({combined[7]}/{combined[6]})")
    # print(f"Dragon units won per shoe {dragon_units_per_shoe}")
    # print("")
    # print(f"3-card 9/7 bets {combined[8]/combined[5]} ({combined[8]}/{combined[5]})")
    # print(f"3-card 9/7 bets won {combined[9]/combined[8]} ({combined[9]}/{combined[8]})")
    # print(f"3-card 9/7 units won per shoe {three_card_97_units_per_shoe}")



