from monopoly_board import Board, Cards, Street
from monopoly_player import Player
import random
from  itertools import cycle
from typing import Optional, List


class GameLogic:
    def __init__(self, kanskaarten:Optional[List[str]] = None, algemeenfondskaarten:Optional[List[str]] = None): # do a little bit here, just enough to get off the ground
        if kanskaarten and algemeenfondskaarten:
            self.board = Board(kaartenkans, kaartenalgemeenfonds)
        else:
            self.board = Board()
        self.players:list[Player] = []
        self.currently_playing:Optional[Player] = None
        self.finished = False
        self.winner = None

    # websockets stuff
    def serialise(self)->dict: #NOTE the board is static, so it should not be sent. Only the cards change, but they arent visible so they dont have to be sent
        serialised_players = [player.serialise() for player in self.players]
        return {
            'turn': self.turn,
            'n_players': len(self.players),
            'finished': self.finished,
            'currently playing': self.currently_playing,
            'players': serialised_players
        }

    # Game logic stuff
    def wait_for_players_to_join(self):
        speler1 = Player('marki')
        self.players.append(speler1)
        speler2 = Player('thijsa')
        self.players.append(speler2)
        speler3 = Player('bartje')
        self.players.append(speler3)

    def startup(self): # extra startup stuff
        # make an iterator
        self.players_iterator = cycle(self.players)


    def play(self): # this is where the magic happens
        self.turn = 0
        while not self.finished:
            self.turn+=1
            print("")
            self.__do_1_turn_1_player()

    def buysellInput2(self):
        geldig_antwoord = False
        while not geldig_antwoord:
            print("Wat is je gewenste verdeling van huizen/hotels?")
            print("Geef je antwoord als 'X Y' waarbij X het aantal huizen/hotels is voor de eerste en Y voor de tweede")
            print("Als je 0 huizen wilt, dan type je '0 0'; als je twee hotels wilt dan type je '5 5' ")
            print("Je anwwoord bestaat dus uit drie characters")
            print("Je kan ook 'g' typen om terug te gaan")
            antwoord = input("")
            if antwoord == 'g':
                return
            if not len(antwoord) == 3: continue
            if not antwoord[0] in ["0","1","2","3",'4','5']: continue
            if not antwoord[2] in ["0","1","2","3",'4','5']: continue
            if not antwoord[1] == ' ': continue
            X = int(antwoord[0])
            Y = int(antwoord[2])
            if abs(X-Y) <= 1:
                geldig_antwoord = True
            else:
                print("House counts cannot differ by more than 1")
        return X,Y
    
    def __2straten(self, STRAAT1:Street, STRAAT2:Street,X:int,Y:int):
        if not isinstance(self.currently_playing,Player): raise RuntimeError("")
        verschil = X - STRAAT1.house_count
        verschil2 = Y - STRAAT2.house_count
        expected_total_cost = verschil  * STRAAT1.HOUSE_COST + verschil2 * STRAAT2.HOUSE_COST
        if expected_total_cost > self.currently_playing.money:
            print("It is expected that you cannot afford this.")
            print(f"You wanted to put {X} houses on {STRAAT1.name} where there are currently {STRAAT1.house_count} houses. This would cost {STRAAT1.HOUSE_COST * (X - STRAAT1.house_count)}")
            print(f"You wanted to put {Y} houses on {STRAAT2.name} where there are currently {STRAAT2.house_count} houses. This would cost {STRAAT2.HOUSE_COST * (Y - STRAAT2.house_count)}")
            print(f"You currently have {self.currently_playing.money}")
            return
        costs = STRAAT1.HOUSE_COST
        while not verschil == 0:
            verschil = X - STRAAT1.house_count
            if verschil>0:
                STRAAT1.build_house()
                self.currently_playing.pay(costs)
            elif verschil<0:
                STRAAT1.sell_house()
                self.currently_playing.receive(costs//2)
            verschil = X - STRAAT1.house_count

        verschil = Y - STRAAT2.house_count
        costs = STRAAT2.HOUSE_COST
        while not verschil == 0:
            verschil = Y - STRAAT2.house_count
            if verschil>0:
                STRAAT2.build_house()
                self.currently_playing.pay(costs)
            elif verschil<0:
                STRAAT2.sell_house()
                self.currently_playing.receive(costs//2)
            verschil = Y - STRAAT2.house_count

    def buysellInput3(self):
        geldig_antwoord = False
        while not geldig_antwoord:
            print("Wat is je gewenste verdeling van huizen/hotels?")
            print("Geef je antwoord als 'X Y Z' waarbij X het aantal huizen/hotels is voor de eerste en Y voor de tweede en Z voor de derde")
            print("Als je 0 huizen wilt, dan type je '0 0 0'; als je twee hotels wilt dan type je '5 5 5' ")
            print("Je anwwoord bestaat dus uit vijf characters")
            print("Je kan ook 'g' typen om terug te gaan")
            antwoord = input("")
            if antwoord == 'g':
                return
            if not len(antwoord) == 5: continue
            if not antwoord[0] in ["0","1","2","3",'4','5']: continue
            if not antwoord[2] in ["0","1","2","3",'4','5']: continue
            if not antwoord[4] in ["0","1","2","3",'4','5']: continue
            if not antwoord[1] == ' ': continue
            if not antwoord[3] == ' ': continue
            X = int(antwoord[0])
            Y = int(antwoord[2])
            Z = int(antwoord[4])
            # if abs(X-Y) <= 1:
            #     geldig_antwoord = True
            # else:
            #     print("House counts cannot differ by more than 1")
            if not abs(X-Y) <=1:
                print("House counts cannot differ by more than 1")
                continue
            if not abs(Z-Y) <=1:
                print("House counts cannot differ by more than 1")
                continue
            if not abs(X-Z) <=1:
                print("House counts cannot differ by more than 1")
                continue
            geldig_antwoord = True
        return X,Y,Z

    def __3straten(self, STRAAT1:Street, STRAAT2:Street, STRAAT3:Street, X:int,Y:int, Z:int):
        if not isinstance(self.currently_playing,Player): raise RuntimeError("")
        if not isinstance(STRAAT1, Street): raise RuntimeError("")
        if not isinstance(STRAAT2, Street): raise RuntimeError("")
        if not isinstance(STRAAT3, Street): raise RuntimeError("")
        verschil = X - STRAAT1.house_count
        verschil2 = Y - STRAAT2.house_count
        verschil3 = Z - STRAAT3.house_count
        expected_total_cost = verschil  * STRAAT1.HOUSE_COST + verschil2 * STRAAT2.HOUSE_COST + verschil3 * STRAAT3.HOUSE_COST
        if expected_total_cost > self.currently_playing.money:
            print("It is expected that you cannot afford this.")
            print(f"You wanted to put {X} houses on {STRAAT1.name} where there are currently {STRAAT1.house_count} houses. This would cost {STRAAT1.HOUSE_COST * (X - STRAAT1.house_count)}")
            print(f"You wanted to put {Y} houses on {STRAAT2.name} where there are currently {STRAAT2.house_count} houses. This would cost {STRAAT2.HOUSE_COST * (Y - STRAAT2.house_count)}")
            print(f"You wanted to put {Z} houses on {STRAAT3.name} where there are currently {STRAAT3.house_count} houses. This would cost {STRAAT3.HOUSE_COST * (Z - STRAAT3.house_count)}")
            print(f"You currently have {self.currently_playing.money}")
            return
        
        verschil = X - STRAAT1.house_count
        costs = STRAAT1.HOUSE_COST
        while not verschil == 0:
            verschil = X - STRAAT1.house_count
            if verschil>0:
                STRAAT1.build_house()
                self.currently_playing.pay(costs)
            elif verschil<0:
                STRAAT1.sell_house()
                self.currently_playing.receive(costs//2)
            verschil = X - STRAAT1.house_count

        verschil = Y - STRAAT2.house_count
        costs = STRAAT2.HOUSE_COST
        while not verschil == 0:
            verschil = Y - STRAAT2.house_count
            if verschil>0:
                STRAAT2.build_house()
                self.currently_playing.pay(costs)
            elif verschil<0:
                STRAAT2.sell_house()
                self.currently_playing.receive(costs//2)
            verschil = Y - STRAAT2.house_count

        verschil = Z - STRAAT3.house_count
        costs = STRAAT3.HOUSE_COST
        while not verschil == 0:
            verschil = Z - STRAAT3.house_count
            if verschil>0:
                STRAAT3.build_house()
                self.currently_playing.pay(costs)
            elif verschil<0:
                STRAAT3.sell_house()
                self.currently_playing.receive(costs//2)
            verschil = Z - STRAAT3.house_count

    def buysell_houses(self):
        if self.currently_playing is None: raise RuntimeError("")
        print(f"{self.currently_playing} want to buy/sell houses")
        self.currently_playing.update_completed_sets()
        if len(self.currently_playing.complete_sets) == 0:
            print("You do not have any completed sets so  oyu cannot do this")
            return
        ready = False
        while not ready:
            print(f"Your complete sets are {self.currently_playing.complete_sets}")
            print("which set do you want to work on? Make sure you spell it without capitalization")
            print("You can type 'g' if you are finished")
            result = input("")
            if result == 'g':
                ready = True
                continue
            cities = ['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam']
            if not result in cities:
                print("you didnt spell it right")
                continue
            match result:
                case 'ons dorp':
                    dorpstraat = self.board.spaces[1]
                    if not isinstance(dorpstraat, Street): raise RuntimeError("")
                    brink = self.board.spaces[3]
                    if not isinstance(brink, Street): raise RuntimeError("")
                    print(f"{dorpstraat.name} has {dorpstraat.house_count} houses")
                    print(f"{brink.name} has {brink.house_count} houses")
                    X,Y = self.buysellInput2()
                    if X is None or Y is None:return # The player doesnt want to build houses
                    self.__2straten(dorpstraat, brink, X,Y)

                case 'arnhem':
                    steenstraat:Street = self.board.spaces[6]
                    ketelstraat:Street = self.board.spaces[8]
                    velperplein:Street = self.board.spaces[9]
                    print(f"{steenstraat.name} has {steenstraat.house_count} houses")
                    print(f"{ketelstraat.name} has {ketelstraat.house_count} houses")
                    print(f"{velperplein.name} has {velperplein.house_count} houses")
                    X,Y,Z = self.buysellInput3()
                    if X is None or Y is None or Z is None:return # The player doesnt want to build houses
                    self.__3straten(steenstraat,ketelstraat,velperplein,X,Y,Z)
                case 'haarlem':
                    barteljorisstraat   = self.board.spaces[11]
                    zijlweg             = self.board.spaces[13]
                    houtstraat          = self.board.spaces[14]
                    print(f"{barteljorisstraat.name} has {barteljorisstraat.house_count} houses")
                    print(f"{zijlweg.name} has {zijlweg.house_count} houses")
                    print(f"{houtstraat.name} has {houtstraat.house_count} houses")
                    X,Y,Z = self.buysellInput3()
                    if X is None or Y is None or Z is None:return # The player doesnt want to build houses
                    self.__3straten(barteljorisstraat,zijlweg,houtstraat,X,Y,Z) # it may complain about this types not matching, but they do
                case 'utrecht':
                    neude       = self.board.spaces[16]
                    biltstraat  = self.board.spaces[18]
                    vreeburg    = self.board.spaces[19]
                    print(f"{neude.name} has {neude.house_count} houses")
                    print(f"{biltstraat.name} has {biltstraat.house_count} houses")
                    print(f"{vreeburg.name} has {vreeburg.house_count} houses")
                    X,Y,Z = self.buysellInput3()
                    if X is None or Y is None or Z is None:return # The player doesnt want to build houses
                    self.__3straten(neude,biltstraat,vreeburg,X,Y,Z)
                case 'groningen':
                    a_kerkhof = self.board.spaces[21]
                    grotemarkt = self.board.spaces[23]
                    heerestraat = self.board.spaces[24]
                    print(f"{a_kerkhof.name} has {a_kerkhof.house_count} houses")
                    print(f"{grotemarkt.name} has {grotemarkt.house_count} houses")
                    print(f"{heerestraat.name} has {heerestraat.house_count} houses")
                    X,Y,Z = self.buysellInput3()
                    if X is None or Y is None or Z is None:return # The player doesnt want to build houses
                    self.__3straten(a_kerkhof,grotemarkt,heerestraat,X,Y,Z)
                case 'den haag':
                    spui = self.board.spaces[26]
                    plein = self.board.spaces[27]
                    langepote = self.board.spaces[29]
                    print(f"{spui.name} has {spui.house_count} houses")
                    print(f"{plein.name} has {plein.house_count} houses")
                    print(f"{langepote.name} has {langepote.house_count} houses")
                    X,Y,Z = self.buysellInput3()
                    if X is None or Y is None or Z is None:return # The player doesnt want to build houses
                    self.__3straten(spui,plein,langepote,X,Y,Z)
                case 'rotterdam':
                    hofplein = self.board.spaces[31]
                    blaak = self.board.spaces[32]
                    coolsingel = self.board.spaces[34]
                    print(f"{hofplein.name} has {hofplein.house_count} houses")
                    print(f"{blaak.name} has {blaak.house_count} houses")
                    print(f"{coolsingel.name} has {coolsingel.house_count} houses")
                    X,Y,Z = self.buysellInput3()
                    if X is None or Y is None or Z is None:return # The player doesnt want to build houses
                    self.__3straten(hofplein,blaak,coolsingel,X,Y,Z)
                case 'amsterdam':
                    leidschestraat = self.board.spaces[37]
                    if not isinstance(leidschestraat,Street): raise RuntimeError("")
                    kalverstraat = self.board.spaces[39]
                    if not isinstance(kalverstraat,Street): raise RuntimeError("")
                    print(f"{leidschestraat.name} has {leidschestraat.house_count} houses")
                    print(f"{kalverstraat.name} has {kalverstraat.house_count} houses")

                    X,Y = self.buysellInput2()
                    if X is None or Y is None:return # The player doesnt want to build houses
                    self.__2straten(leidschestraat,kalverstraat,X,Y)
                case _:
                    raise RuntimeError("Unreachable")
            continue
                    
        return



    def __do_1_turn_1_player(self):
        current_player = self.players_iterator.__next__()
        self.currently_playing = current_player
        print(f"The current player is {current_player}. They are standing on space {self.board.spaces[self.currently_playing.position]}")
        print(f"The current player has {current_player.money} money")
        # check if they are dead
        if self.currently_playing.money<0:
            print("This player is a broke boi so they cant play; NEXT")
            return
        # state 1: Choose between actions: throw dice, buy/sell houses, /mortgage/unmortgage, offer trade
        ready = False
        while not ready:
            print("Menu: what do you want to do? Your options are:")
            print("1: Throw dice")
            print("2: Buy/Sell houses")
            print("3: mortgage/unmortgage porperties")
            print("4: offer trade to other players")
            result = input("")
            match result:
                case "1": # keep playing
                    break # break means its allreaddyy inplemented
                case "2": # buy/sell houses
                    self.buysell_houses()
                case "3": # mortgage / unmortgage
                    print("Wees geen kleine speler. Dit doen we niet")
                case "4": # offer trade
                    print("trading is not yet implemented")
                    pass # dit wordt moeite
                case _:
                    print("Invalid response, please chose 1,2,3 or 4")

        # check for player in jail
        if self.currently_playing.jailtime!= 0:
            print("This player is in Jail")
            self.currently_playing.jailtime-=1
            print("In this game, you dont get to escape jail")

        # now the real turn can start
        throw = self.__throw_dice()
        current_player.most_recent_diceroll = throw
        current_player.walk(steps = throw)
        current_player_position = current_player.position
        landing_space = [space for space in self.board.spaces if space.position == current_player_position]
        if not len(landing_space) == 1: raise RuntimeError("")
        landing_space = landing_space[0]
        print(f"Player {self.currently_playing} landed on {landing_space}")
        try:
            landing_space.on_land(current_player)
        except Exception as e:
            print(f"While player {self.currently_playing} landed on {landing_space}, an issue occures during the on_land function with errormessage: {e}")


    def check_finished(self):
        not_finished_count = 0
        for player in self.players:
            if not player.has_lost:
                not_finished_count+=1
        if not_finished_count<2:
            self.finished = True

    def __throw_dice(self)->int:
        throw = random.randint(1,6) + random.randint(1,6)
        print(f"{throw} thrown")
        return throw




if __name__ == "__main__":
    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")
    game = GameLogic()
    game.wait_for_players_to_join()
    game.startup()
    game.play()