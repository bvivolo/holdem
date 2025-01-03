import ast
import poker.objects as poker
from poker.objects import (
    Card, 
    Player, 
    PokerGame, 
    Pot, 
)
import random
import routing
import threading
import time

def create_game(name: str, game_id: int) -> None:
    print(type(game_id))
    game = PokerGame(game_id)
    router = routing.new_router(game_id)
    router.register_game_handler(game.handle_message)
    poker.games[game_id] = game
    
    game_thread = threading.Thread(target=run_game, args=(game))
    game_thread.start()

def run_game(game: PokerGame) -> None:

    router = routing.get_router(game.id)

    players = game.players
    deck = game.deck
    button = game.button
    ftr = game.cards
    pots = game.pots
    sm_blind = game.sm_blind
    bg_blind = sm_blind * 2

    while True:

        wait_for_players(players)

        seats = get_active_seats(players)
        pots.append(Pot(seats))
        set_btn_position(button, seats)

        for seat in get_blind_seats(seats, button):
            players[seat].pay_blind(sm_blind)
        
        for s in seats:
            hand = take_hand(deck, game.hand_size)
            players[s].deal(hand)
        
        # Send message to app
        print("Cards dealt."); print("")

        turn = increment_seat(seats, button, 3)
        turn_count = 0 
        last_bet = bg_blind

        while True:
            
            if not players[turn].in_pot[active_pot]: turn += 1; continue

            #If all bets are equal and not first turn of the round
            if last_bet == players[turn].total_bet and turn_count >= len(seats):
                    
                for player in players.values():
                    player.reset_bet()

                #Display pot total.
                print(f"The pot is ${pots[0]}."); print("")
                turn_count = 0

                #Flip next card(s)
                if len(ftr) == 0: flip_cards(game, 3)
                elif len(ftr) <= 4: flip_cards(game, 1)
                else: break
                
                for cards in ftr:
                    print(f"{suitDict[cards[0]]}{valDict[cards[1]]}")
                print("")

                turn = (button + 1) % len(seats)
                last_bet = 0
                continue
            
            #Display current bet
            print(f"The bet is ${last_bet}"); print("")
            
            #Decide available actions
            actions = [[True,"check"], [True,"bet"], [True,f"call (${last_bet-players[turn].total_bet} more)"], [True,"raise"], [True,"fold"]]

            if turn_count == 0:
                if len(ftr): actions[2][0], actions[3][0] = False, False
                else: actions[1][0] = False
                    
            if last_bet > players[turn].total_bet: actions[0][0], actions[1][0] = False, False
            elif last_bet == players[turn].total_bet and (not turn_count == 0 or len(ftr) == 0): actions[1][0], actions[2][0] = False, False
            if last_bet >= players[turn].balance: actions[3][0] = False

            #Display options, get & execute action
            while True:
                for a in actions:
                    if a[0]: print(f"-- {a[1]}")
                print("")
                action = input(f"{players[turn].name}, pick an above action: ")

                #Execute Action
                if action == "check" and actions[0][0]:
                    print(f"{players[turn].name} checks."); print("")
                    break
                    
                elif action == "bet" and actions[1][0]:
                    bet = int(input("How much do you want to bet?"))
                    [pots, last_bet] = players[turn].bet(bet, last_bet, bg_blind, pots)
                    break
                
                elif action == "call" and actions[2][0]:
                    [pots, last_bet] = players[turn].bet(last_bet-players[turn].total_bet, last_bet, bg_blind, pots)
                    break
                    
                elif action == "raise" and actions[3][0]:
                    newRaise = int(input("How much more do you want to raise by?"))
                    [pots, last_bet] = players[turn].bet(newRaise+last_bet-players[turn].total_bet, last_bet, bg_blind, pots)
                    break
                    
                elif action == "fold" and actions[4][0]:
                    players[turn].fold()
                    break
                    
                else: print("Action is invalid."); print("")
            
            #Next players turn
            turn = increment_seat(seats, turn, 1)
            turn_count += 1

        #Cycle through active players and determine score ("rank")
        ranked_players = []
        for p in players.values():
            
            #Skip folded players, else score the cards
            if p.in_pot == [False]: continue
            else: p.find_rank(p.hole+ftr)

            #Rank hand and display result
            ranked_players.append(p)
            print(f"{p.name}'s Hand: {p.rHand} Type: {rankDict[p.rank[0]]}")

        #Sort ranked players by hand type, then strength of type
        print("")
        ranked_players = sorted(ranked_players, key = lambda y: (y.rank[0], y.rank[1]), reverse=True)
        
        #Pay winners and reset pot
        payWinners(ranked_players, pots, players)
        pots = [0]

        #Reset pot; return Flop, Turn, River, and hole cards to deck
        print("")
        pots = [0]
        for i in range(len(ftr)):
            deck.append(ftr.pop())
        for p in players:
            p.inPot = [True]
            deck = p.cardsToDeck(deck)

        #Check to play another hand
        anotherOne = input("Would you like to play another hand? (y/n): ")
        if anotherOne == "y": break
        elif anotherOne == "n": play = False; break
        else: print("Invalid Response")
        
        #Move button to next player
        button = (button+1)%len(players)
        print(f"The button moves to {players[button].name}."); print("")

    for p in players: del p

def wait_for_players(players):
    while len(players) < 2:
        continue
    time.sleep(30)

def set_btn_position(button: int, seats: list[int]) -> None:
    if button == -1:
        button = seats[random.randint(0, len(seats))]
    button = increment_seat(seats, button, 1)
    
def get_active_seats(players: list[Player]) -> list[int]:
    seats = [player.seat for player in players if player.sit_out == False]
    return seats

def get_blind_seats(seats: list[int], button: int) -> list[int]:
    n = len(seats)
    sm_blind_pos = (button + 1) % n
    bg_blind_pos = (button + 2) % n
    return [sm_blind_pos, bg_blind_pos]

def flip_cards(game, count: int) -> None:
    for _ in range(count):
        game.cards.append(game.deck.pop(random.randint(0,len(game.deck)-1)))

def increment_seat(seats: list[int], cur: int, count: int) -> int:
    new_seat = seats[(seats.index(cur) + count) % len(seats)]
    return new_seat

def take_hand(deck: list[list[int]], hand_size: int) -> list[list[int, int]]:
    return [deck.pop(random.randint(0,len(deck)-1)) for _ in hand_size]