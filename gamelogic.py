import random
from collections import defaultdict

roomname = "yes"
userids[roomname] = ["1sihs", "whhsjs", "eiehje", "ekejj"]
class BluffGame:
    def __init__(self, num_players=4, userids):
        
        self.num_players = num_players
        self.userids = userids[roomname]
        
        self.suits = ['S', 'H', 'C', 'D']
        self.ranks = list(range(1, 14))  
        self.deck = [(suit, rank) for suit in self.suits for rank in self.ranks]
        self.player_hands = {}
        for i in userids:
            self.player_hands[i] = []
        self.current_player = 0
        self.pass_count = 0
        self.last_play = {"player": -1, "claimed_rank": -1, "cards": []}
        self.game_over = False
        
        self.player_html = {}
        
        for i in userids:
            self.player_html[i] = []
            
    def deal_cards(self):
        random.shuffle(self.deck)
        
        while self.deck:
            index = len(self.deck) % self.num_players
            self.player_hands[userids[index]].append(self.deck.pop())
            
        for i in userids:
            self.player_hands[i].sort(key=lambda x: x[1])
    
    def sort_hand(self, userid):
        # Group cards by rank
        hand_by_rank = defaultdict(list)
        for suit, rank in self.player_hands[userid]:
            hand_by_rank[rank].append(suit)

    def display_hand(self, userid):
        self.player_html[userid] = []
        for suit, rank in self.player_hands[userid]:
            self.player_html[userid].append(f'<img class = "card" src = "https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/style-font-decor/Dark%20Cards/{rank}-{suit}.png" value = "{rank}{suit}"> ')
            
        
    def play_hand(self, userid, played_hands):
        for i in played_hands[userid]:
        self.deck.append(self.player_hands[userid].pop(i))
        
    def call_bluff(self, userid, playedhands):
        
        
    
    def play(self, userid):
        print(self.player_hands[userid])
        print(self.player_html[userid])
        
    
if __name__ == "__main__":
    game = BluffGame()
    game.deal_cards()
    game.display_hand(userids[0])
    game.play(userids[0])
