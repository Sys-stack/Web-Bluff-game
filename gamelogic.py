import random
from collections import defaultdict

class BluffGame:
    def __init__(self, userids, roomname, num_players=4):
        
        self.num_players = num_players
        self.userids = userids[roomname]
        
        self.suits = ['S', 'H', 'C', 'D']
        self.ranks = list(range(1, 14))  
        self.deck = [(suit, rank) for suit in self.suits for rank in self.ranks]
        
        self.player_hands = {}
        for i in self.userids:
            self.player_hands[i] = []
            
        self.current_player = None
        self.turn_count = 1
        self.last_play = {"player": -1, "claimed_rank": -1, "cards": []}
        
        self.game_status = True
        
        self.turn = {"played_previous":[]}
        
        self.player_html = {}
        self.called_bluff = {}
        for i in self.userids:
            self.called_bluff[i] = False
        for i in self.userids:
            self.player_html[i] = []
        self.bluff_caller = None

    def back_hand(self, userid):
        self.back = ""
        for card in self.player_hands[userid]:
            self.back.append("<img class = 'cardback' src = 'https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/style-font-decor/BACK.png'>")
        return self.back.append
    
    def deal_cards(self):
        random.shuffle(self.deck)
        
        while self.deck:
            index = len(self.deck) % self.num_players
            self.player_hands[self.userids[index]].append(self.deck.pop())
            
        for i in self.userids:
            self.player_hands[i].sort(key=lambda x: x[1])
    
    def sort_hand(self, userid):
        self.player_hands[userid].sort(key = lambda x : x[1])

    def display_hand(self, userid):
        self.player_html[userid] = []
        for suit, rank in self.player_hands[userid]:
            self.player_html[userid].append(f'<img class = "card" src = "https://raw.githubusercontent.com/Sys-stack/Web-Bluff-game/refs/heads/style-font-decor/Dark%20Cards/{rank}-{suit}.png" value = "{rank}{suit}"> ')
            
        
    def played(self, userid, played_hands):
        for selected_cards in played_hands:

            self.deck.append(selected_cards)
            self.player_hands[userid].remove(selected_cards)
        
    def call_bluff(self, userid):
        self.called_bluff[userid] = True
        
        for key in self.called_bluff:
            if self.called_bluff[key] == True:
                self.bluff_caller = key
            else:
                self.bluff_caller = None
        
        if self.check_bluff_truth():
            self.player_hands[self.bluff_caller].extend(self.deck)
            self.sort_hand(self.player_hands[self.bluff_caller])
            self.deck = []
            
            for key in self.called_bluff:
                self.called_bluff[key] = False
                
            return "not-bluff"
        else:
            self.player_hands[self.current_player].extend(self.deck)
            self.sort_hand(self.current_player)
            self.deck = []
            
            for key in self.called_bluff:
                self.called_bluff[key] = False
            
            return "bluff"
             
         
    def check_bluff_truth(self):
        self.boolvar = True
        for card in self.turn["previous_played"]:
            if card[1] != self.turn_count:
                self.boolvar = False
                break
        return self.boolvar
    
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
        if self.game_over():
            self.game_status = False
        
        
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
        
    def game_over(self):
        if not self.player_hands[self.current_player]:
            return True
        else:
            return False
        
    
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
    
    game.after_play([game.player_hands[game.current_player][0]])
    
    print(f" afterplay: {game.player_hands[game.current_player]}")
    
    game.next_player_shift()
    
    print(f"Starter is {game.current_player} and has the deck {game.player_hands[game.current_player]}")
    
    game.after_play([game.player_hands[game.current_player][0]])
    print(game.called_bluff)
    print(f" afterplay: {game.player_hands[game.current_player]}")
    
    print(f" {game.userids[0]} has called bull shit {game.current_player}, and the card is a {game.call_bluff(game.userids[0])}")
    print(f"After BULLSHITTED {game.player_hands[game.current_player]}")
    
        
    
