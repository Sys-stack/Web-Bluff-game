import random
from collections import defaultdict

class BluffGame:
    def __init__(self, num_players=4):
        self.num_players = num_players
        
        self.suits = ['S', 'H', 'C', 'D']
        self.ranks = list(range(1, 14))  
        self.deck = [(suit, rank) for suit in self.suits for rank in self.ranks]
        
        self.player_hands = [[] for _ in range(num_players)]
        self.current_player = 0
        self.pass_count = 0
        self.last_play = {"player": -1, "claimed_rank": -1, "cards": []}
        self.game_over = False
        
    def deal_cards(self):
        random.shuffle(self.deck)
        
        while self.deck:
            self.player_hands[len(self.deck) % self.num_players].append(self.deck.pop())
            
        for i in range(self.num_players):
            self.player_hands[i].sort(key=lambda x: x[1])
    
    def sort_hand(self, pnum):
        # Group cards by rank
        hand_by_rank = defaultdict(list)
        for suit, rank in self.player_hands[pnum]:
            hand_by_rank[rank].append(suit)

    def display_hand(self, pnum):
        for 
    
