import random
from collections import defaultdict

#initialising variables



class BluffGame:
    def __init__(self, userids, roomname, num_players=4):
        
        self.num_players = num_players
        self.userids = userids[roomname]
        
        self.suits = ['S', 'H', 'C', 'D']
        self.ranks = list(range(1, 14))  
        self.deck = [(suit, rank) for suit in self.suits for rank in self.ranks]
        
        self.player_hands = {}
        for i in userids[roomname]:
            self.player_hands[i] = []
        self.current_player = 0
        self.turn_count = 1
        self.last_play = {"player": -1, "claimed_rank": -1, "cards": []}
        
        self.game_over = False
        
        self.turn = {"previous":[], "current":[], "played_previous":[], "played_current":[]}
        
        self.player_html = {}
        self.call_bluff = {}
        for i in userids[roomname]:
            self.call_bluff[i] = False
        for i in userids:
            self.player_html[i] = []
            
    def deal_cards(self):
        random.shuffle(self.deck)
        
        while self.deck:
            index = len(self.deck) % self.num_players
            self.player_hands[userids[roomname][index]].append(self.deck.pop())
            
        for i in userids[roomname]:
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
            
        
    def played(self, userid, played_hands):
        for selected_cards in played_hands:

            self.deck.append(selected_cards)
            self.player_hands[userid].remove(selected_cards)
        
    def call_bluff(self, userid):
        for check in self.call_bluff[userid]:
            if check:
                pass
                if self.turn["previous"][1] != 's':
                    pass
        
    
    def start(self):
        self.deal_cards()
        for user in self.player_hands:
            
            if ('S', 1) in self.player_hands[user]:
                starter = user
        self.current_player = starter
        self.userindex = self.userids.index(starter)
        
    def after_play(self, played_hands):
        self.played(self.current_player, played_hands)
        self.turn["previous_played"] = played_hands
        
        
    def next_player_shift(self):
        if self.turn_count < 13:
            self.turn_count += 1
        else:
            self. turn_count = 1
        
        if self.userindex < 3:
            self.userindex += 1
        else:
            self.userindex = 0
        self.current_player = self.userids[self.userindex]
        
    def next_player_turned(self, played_hands):
        pass
        
        
    
if __name__ == "__main__":
    userids = {}
    roomname = "yes"
    userids[roomname] = ["1sihs", "whhsjs", "eiehje", "ekejj"]

    game = BluffGame(userids, roomname)
    game.start()
    
    print(f"Starter is {game.current_player} and has the deck {game.player_hands[game.current_player]}")
    
    game.after_play([('S', 1)])
    
    print(f" afterplay: {game.player_hands[game.current_player]}")
    
    game.next_player_shift()
    
    print(f"Starter is {game.current_player} and has the deck {game.player_hands[game.current_player]}")
    
    game.next_player_turned([("C", 5)])
    
    
        
    
