import time
import threading
import routing

games = {}

class PokerGame:
    hand_strengths = {
        0 : "High Card",
        3 : "Pair",
        6 : "Two Pair",
        7 : "3 of a Kind",
        8 : "Straight",
        9 : "Flush",
        10 : "Full House",
        12 : "4 of a Kind",
        17 : "Straight Flush",
        18 : "Royal Flush"
    }

    def __init__(self, id: int):
        self.id: str = id
        self.players: list[Player] = []
        self.deck: list[list[int]] = [(i, j) for j in range(1,14) for i in range(1, 5)]
        self.hand_size = 2
        self.sm_blind: int = 100
        self.button: int = 0
        self.pots: list[Pot] = []
        self.cards: list[Card] = []

        self.actions_map = {
            'player': {
                'add': self.add_player, 
                'rmv': self.rmv_player, 
                'sitout': self.sitout_player, 
                'sitin': self.sitin_player, 
            }, 
            'get': {
                'players': self.get_players, 
                'id': self.get_id
            }
        }

        seppuku = threading.Thread(target=self.destruct)
        seppuku.start()

    def handle_message(self, message: str) -> None:
        type, cmd, data = message.split(':', 2)
        return self.actions_map[type][cmd](data)

    def destruct(self):
        while True:
            clock = 0
            while len(self.players) == 0:
                time.sleep(1)
                clock += 1
                if clock == 30:
                    routing.close_router(self.id)
                    del games[self.id]
            time.sleep(10)

    def add_player(self, client_address: str):
        if len(self.players) == 8:
            return {'code': '400', 'message': 'Game is Full'}
        
        new_seat = len(self.players)
        for seat, player in enumerate(self.players):
            if seat != player.seat:
                new_seat = seat

        player = Player(new_seat, client_address)
        self.players.append(player)
        self.players.sort(key=lambda p: p.seat)
        return {'code': '200', 'message': 'Player added'}

    def rmv_player(self, rmv_addr: str):
        for seat, player in enumerate(self.players):
            if player.addr == rmv_addr:
                self.players.pop(seat)
                return {'code': '200', 'message': 'Player removed'}
        return {'code': '400', 'message': 'Player not found'}
    
    def sitout_player(self, addr: str):
        pass

    def sitin_player(self, addr: str):
        pass

    def get_players(self, _):
        return [p.addr for p in self.players]

    def get_id(self, _):
        return self.id

class Player:
    def __init__(self, seat: int, addr: str):
        self.addr = addr
        self.seat = seat
        self.balance = 0
        self.cur_bet = 0
        self.hole = [[0,0],[0,0]]
        self.hand = [] #Final hand out of 7 cards
        self.rank = [0,0] #[Hand Type, Hand Type Strength] For scoring
        self.sit_out = False
        self.in_pot = [False] #Array to allow for different bools for different pots

    def __repr__(self):
        return f"Name: {self.name}; Balance: ${self.balance}; Hole Cards: {self.rHole}"

    def pay_blind(self, blind: int):
        if blind > self.balance:
            blind = self.balance
        self.cur_bet += blind
        self.balance -= blind

    def ante_up(self, ante: int):
        if ante > self.balance:
            self.fold()
            self.sit()
        self.balance -= ante

    #Deal cards out of deck into player's hand
    def deal(self, hand: list[list[int]]):
        self.hole = hand

    #Take in proposed bet, call, or raise; check legality, transfer money, print & return result
    def bet(self, betAdd, currBet, bb, pots):

        totalBet = betAdd + self.cur_bet
        
        #Ensure legality of bet
        if totalBet < bb: betAdd = bb - self.cur_bet; print("The first bet must be at least the BB"); print("")
        elif totalBet > bb and totalBet < bb*2: betAdd = bb*2 - self.cur_bet; print("First raise must be twice BB."); print("")
        if betAdd > self.balance:
            betAdd = self.balance
        pots[0] += betAdd
        
        #Transfer from balance to bet
        self.balance -= betAdd
        self.cur_bet += betAdd
        
        #Determine action and report.
        if self.balance == 0: print(f"{self.name} goes All In for ${self.cur_bet} ")
        elif self.cur_bet > currBet:
            if first and round > 1: print(f"{self.name} bets ${self.cur_bet}")
            else: print(f"{self.name} raises to ${self.cur_bet}")
        elif self.cur_bet == currBet: print(f"{self.name} calls for ${betAdd}")
        print("")
        
        return [pots, self.cur_bet] if self.cur_bet >= currBet else [pots, currBet]
    
    def reset_bet(self):
        self.cur_bet = 0

    def fold(self):
        self.cur_bet = 0
        self.in_pot = [False]

    def sit(self):
        self.sit_out = True

    def all_in(self):
        self.cur_bet = self.balance
        self.balance = 0

    def cardsToDeck(self, deck):
        deck.extend(self.hole)
        self.hole = [[0,0],[0,0]]
        self.hand = []
        self.inPot = [True]
        return deck

    #Use all possible cards to find best hand of 5 cards
    def find_rank(self, allCards):

        #Clear Rank
        self.rank = [0,0]

        #Sort Available Cards by Number
        allCards = sorted(allCards, key=lambda x: x[1])
        for i in allCards:
            i.append(1)
        [bestRank, bestHand] = [[0,0,0], []]
            
        #Cycle through all possible 5 out of 7 and determine rank [hand type, strength of type]
        for i in range(0,6):
            for j in range(i+1,7):

                #Set Variables
                _counts = [1,1,0,0,0,0]
                prevCardVal = -1
                pairs = 0
                flushStr = [0,1]
                [tempRank, tempHand] = [[0,0], []]

                #Begin checking pick 5 of 7 cards
                for card in allCards:
                    
                    #Skip new pair of cards, add used cards to temporary hand
                    k = allCards.index(card)
                    if k == i or k == j: continue

                    #Add new card to temp hand
                    tempHand.append(card)
                    
                    #Find X of a Kind (2, 3, 4, full house)
                    if card[1] == prevCardVal: _counts[0] += 1
                    else: _counts[0] = 1
                    
                    if _counts[0] == 2:
                        tempRank[0] += 3
                        tempRank[1] += card[1]*2*100**pairs
                        card[2] = 0
                        allCards[k-1][2] = 0
                        pairs += 1
                    elif _counts[0] == 3:
                        tempRank[0] += 4
                        tempRank[1] += card[1]*100
                        card[2] = 0
                    elif _counts[0] == 4:
                        tempRank = [12, card[1]]
                        card[2] = 0
                    
                    #Find Straight
                    if card[1] == prevCardVal + 1: _counts[1] += 1
                    elif len(tempHand) == 5 and card[1] == 13 and tempHand[0][1] == 1: _counts[1] += 1 #Check for wheel
                    else: _counts[1] = 1
                    if _counts[1] == 5: tempRank = [8, card[1]]

                    #Update strength for flush (card5 * 2^4 + card4 * 2^3 +...)
                    flushStr[0] += card[1]*flushStr[1]
                    flushStr[1] *= 2

                    #Find Flush
                    _curSuit = card[0]
                    _counts[_curSuit+1] += 1
                    if _counts[_curSuit+1] == 5:
                        tempRank[0] += 9
                        tempRank[1] += flushStr[0]
                        if tempRank == [17,13]: tempRank[0] == 18

                    #Set last value for check against next card
                    prevCardVal = card[1]

                #Find kicker and add value to rank
                if tempRank[0] < 8:
                    kickerMax = 0
                    for c in range(len(tempHand)):
                        if tempHand[c][2] and tempHand[c][1] > kickerMax: kickerMax = tempHand[c][1]
                        
                    tempRank[1] += kickerMax

                #If rank is better than last hand, update player's hand
                if tempRank[0] > bestRank[0] or (tempRank[0] == bestRank[0] and tempRank[1] > bestRank[1]):
                    [bestRank, bestHand] = [tempRank, tempHand]

        #Remove kicker markers from cards ([x, x, 1] -> [x, x])
        for card in allCards:
            card.pop()

        #Set player rank and hand to bests
        [self.rank, self.hand] = [bestRank, bestHand]

class Card:
    rank_reprs = {
        0 : "2", 1 : "3",
        2 : "4", 3 : "5",
        4 : "6", 5 : "7",
        6 : "8", 7 : "9",
        8 : "10", 9 : "J",
        10 : "Q", 11 : "K",
        12 : "A", 
    }

    suit_reprs = {
        0 : "\u2660",
        1 : "\u2663",
        2 : "\u2665",
        3 : "\u2666",
    }

    def __init__(self, rank: int, suit: int):
        self.rank = rank
        self.suit = suit
    
    def __repr__(self):
        return f'{self.suit_reprs[self.suit]}{self.rank_reprs[self.rank]}'

class Pot:
    def __init__(self, seats: list[int]):
        self.total = 0
        self.max_bet = float('inf')
        self.seats: set[int] = set(seats)

    def add(self, bets: int) -> None:
        self.total += bets

    def split(self, ways: int) -> list[int]:
        pots = [self.total // ways] * ways
        remainder = self.total % ways
        for pot in pots[:remainder]:
            pot += 1
        return pots

    def reset(self) -> None:
        self.total = 0
        self.max_bet = float('inf')
        self.seats = set()

    def remove_player(self, seat: int) -> None:
        if seat in self.seats:
            self.seats.remove(seat)
            return
        raise Exception(f'Player in seat {seat} is not in the pot.')
    
class CardGame:
    def __init__(self, id: int):
        self.id: int = id
        self.players: dict[int, Player] = {}
        self.deck: list[list[int]] = [(i, j) for j in range(1,14) for i in range(1, 5)]
        self.hand_size = 2
        self.button: int = -1
        self.pots: list[Pot] = []
        self.cards: list[Card] = []

        garbage_thread = threading.Thread(target=self.destruct)
        garbage_thread.start()

    def destruct(self):
        while True:
            clock = 0
            while self and len(self.players) == 0:
                time.sleep(1)
                clock += 1
                if clock == 30:
                    routing.close_router(self.id)
                    del self[self.id]
            time.sleep(10)