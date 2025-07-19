from  __future__  import annotations
from abc import ABC, abstractmethod
import random
from collections import deque
from typing import TYPE_CHECKING, Optional, List
if TYPE_CHECKING:
    from monopoly_player import Player


class Cards:
    def __init__(self, cards:list[str]):
        if not type(cards) == list: raise ValueError("Deck must be a list of strings")
        if not len(cards) >2: raise ValueError("Deck must contain at least three cards")
        if not len(cards) <100: raise ValueError("Deck must contain less then 100 cards")
        for card in cards:
            if not type(card) == str: raise ValueError("Deck must be a list of strings")
            a = len(card)
            if a<1: raise ValueError("Cards must not be empty")
            if a>300: raise ValueError("Cards may not contain more than 300 characters")
        self.cards = deque(cards)
        self.shuffle()

    def shuffle(self):
        cards_list = list(self.cards)
        random.shuffle(cards_list)
        self.cards = deque(cards_list)

    def draw(self)->str:
        card = self.cards.popleft()
        self.cards.append(card)
        return card



class Space(ABC):
    def __init__(self, position:int, name:str):
        self.position = position
        self.name = name

    def __repr__(self):
        return self.name

    @abstractmethod
    def on_land(self, player:Player):
        pass

    @property
    @abstractmethod
    def purchasable(self)->bool:
        pass

    @property
    @abstractmethod
    def space_type(self)->str:
        pass


    
class Property(Space, ABC):
    def __init__(self,position:int, name:str, price:int):
        super().__init__(position=position, name=name)
        self.price = price
        self.owner:Optional[Player] = None
        self.morgaged = False
        
    @property
    def purchasable(self)->bool:
        return True

    def purchase(self, player:Player):
        if self.owner is None and player.money >= self.price:
            player.pay(self.price)
            self.owner = player
            player.properties.append(self)
            print(f"{player.name} bought {self.name} for ${self.price}")
        else:
            print(f"{self.name} is not available for purchase.")


    @property
    @abstractmethod
    def buildable(self)->bool:
        pass

    @abstractmethod
    def calculate_rent(self, diceroll:Optional[int] = None)->int: # this function assumes no mortgages
        pass

    def offer_purchase(self,player:Player):
        # Replace with UI or CLI prompt later
        print(f"{player.name} can buy {self.name} for ${self.price}.")
        # raise RuntimeError("TODO: implement a way to decline this")
        awnswered = False
        while not awnswered:
            print("Do you want to buy this? Type 1 or y for yes and type 2 or n for no")
            result = input(" ")
            match result:
                case "1" | "y":
                    self.purchase(player)
                    awnswered = True
                case "2" | "n":
                    awnswered = True
                    return
                case _:
                    print("Incorrect response")

    def on_land(self,player:Player):
        if self.owner is None:
            self.offer_purchase(player)
        elif self.owner == player:
            print(f"Player {player.name} landed of their own space")
        elif self.owner != player:
            if self.morgaged:
                print(f"Player {player.name} landed on {self.owner}'s property, but it is morgaged")
            else: #dokken vriend
                #update rent
                diceroll:int = player.most_recent_diceroll
                rent = self.calculate_rent(diceroll)
                player.pay(rent)
                self.owner.receive(rent)
                print(f"{player.name} pays ${rent} to {self.owner.name} for landing on {self.name}")

    # implemetn mortgaging?
    @abstractmethod
    def mortgage(self, player:Player):
        pass

    @abstractmethod
    def unmortgage(self, player:Player):
        pass

class Street(Property):
    def __init__(self, position:int, name:str, price:int, city:str, base_rent:list[int], house_cost:int):
        super().__init__(position, name, price)
        self.city = city
        self.base_rent = base_rent# rent depending on number of houses, 0-5 ; 5 ==hotel; 0==empty
        self.house_count:int = 0
        self.HOUSE_COST = house_cost

    @property
    def buildable(self)->bool:
        return True
    
    @property
    def space_type(self)->str:
        return "street"
    
    def calculate_rent(self, diceroll:Optional[int] = None)->int: # this function assumes no mortgages
        # this function is only called after this property has been purchased.
        if self.owner is None: raise RuntimeError("This property had its rent calculated but it doesnt have an owner")
        rent = self.base_rent[self.house_count]
        if self.city in self.owner.complete_sets and self.house_count ==0:
            return 2*rent
        else:
            return rent
    
    def build_house(self): # this function assumes that the build action is valid
        self.house_count +=1
        assert self.house_count in [0,1,2,3,4,5]

    def sell_house(self): # this functio assumes that this is a valid action
        self.house_count -=1
        assert self.house_count in [0,1,2,3,4,5]

    def mortgage(self,player:Player):
        raise RuntimeError("Not implemented yet")
    
    def unmortgage(self,player:Player):
        raise RuntimeError("Not implemented yet")

class Utility(Property):
    def __init__(self, position:int, name:str, price:int):
        super().__init__(position, name, price)

    @property
    def buildable(self)->bool:
        return False
    
    @property
    def space_type(self)->str:
        return "utility"
    
    def mortgage(self,player:Player):
        raise RuntimeError("Not implemented yet")
    
    def unmortgage(self,player:Player):
        raise RuntimeError("Not implemented yet")

    
    def calculate_rent(self, diceroll:Optional[int] = None)->int: # this function assumes no mortgages
        if not diceroll:
            raise ValueError("Requires a diceroll")
        if self.owner is None: raise RuntimeError("This property had its rent calculated but it doesnt have an owner")
        owner_utilities = sum(1 for p in self.owner.properties if isinstance(p, Utility))
        if not ((owner_utilities ==1 ) or (owner_utilities == 2)): raise RuntimeError("If this function is called, the owner must have one or two of the utilities")
        if owner_utilities == 1: return 4 * diceroll
        elif owner_utilities == 2: return 10*diceroll
        raise RuntimeError("unreachable")
    

class Station(Property):
    def __init__(self, position:int, name:str, price:int):
        super().__init__(position, name, price)

    @property
    def buildable(self)->bool:
        return False
    
    @property
    def space_type(self)->str:
        return "station"

    def mortgage(self,player:Player):
        raise RuntimeError("Not implemented yet")
    
    def unmortgage(self,player:Player):
        raise RuntimeError("Not implemented yet")
    
    def calculate_rent(self, diceroll:Optional[int] = None)->int:
        if self.owner is None: raise RuntimeError("This property had its rent calculated but it doesnt have an owner")
        owner_station_count = sum(1 for eigendom in self.owner.properties if isinstance(eigendom, Station))
        rents = [0,25,50,100,200]
        rent = rents[owner_station_count]
        return rent


class CardSpace(Space, ABC):            # THIS NEEDS TO BE COMPLETELY REFACTORED. THE CARDS ARE GLOBAL AND BELONG TO THE BOARD, NOT THE INDIVIDUAL SPACE
    def __init__(self, position:int, name:str, cards:Cards):
        super().__init__(position, name)
        self.deck = cards
    
    def on_land(self, player:Player): # TODO make this actually do something
        card:str = self.deck.draw()
        print(f"Player {player.name} drew a card that says: {card}")
        
    @property
    def purchasable(self)->bool:
        return False
    # @property
    # def space_type(self)->str:
    #     return 
        
class ChanceCard(CardSpace):
    def __init__(self, position:int, name:str, cards:Cards):
        super().__init__(position, name, cards)

    @property
    def space_type(self)->str:
        return "Chance"
    

class AlgemeenFondsCard(CardSpace):
    def __init__(self, position:int, name:str, cards:Cards):
        super().__init__(position, name, cards)

    @property
    def space_type(self)->str:
        return "AlgemeenFonds"
    

class Tax(Space):
    def __init__(self, position:int, name:str, amount:int):
        super().__init__(position, name)
        self.amount = amount

    def on_land(self, player:Player):
        player.pay(self.amount)
    
    @property
    def purchasable(self)->bool:
        return False
    @property
    def space_type(self)->str:
        return "tax"
        

class GO(Space):
    def __init__(self):
        super().__init__(position=0, name="GO")

    def on_land(self,player:Player):
        return
        player.receive(200)
        print(f"Player {player.name} landed on GO and got 200 dollas")

    @property
    def purchasable(self)->bool:
        return False

    @property
    def space_type(self)->str:
        return "go"
    

class GoToJail(Space):
    JailPosition = 9
    def __init__(self):
        super().__init__(position = 30, name = "Go to jail")
    def on_land(self, player:Player):
        player.position = self.JailPosition
        player.jailtime = 3

    @property
    def purchasable(self)->bool:
        return False
    @property
    def space_type(self)->str:
        return "go to jail"


class FreeParking(Space):
    def __init__(self, position:int, name:str):
        super().__init__(position, name)
    
    def on_land(self, player:Player):
        print(f"Player {player.name} landed on a free space and does nothing")
    @property
    def space_type(self)->str:
        return "free parking"
    @property
    def purchasable(self)->bool:
        return False



class Board:
    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")
    def __init__(self, kanskaarte:Optional[List[str]] = None, algemeenfondskaarte:Optional[List[str]] = None):
        if kanskaarte is None:
            kanskaarte = self.kaartenkans
        if algemeenfondskaarte is None:
            algemeenfondskaarte = self.kaartenalgemeenfonds
        kanskaarten = Cards(kanskaarte)
        algemeenfondskaarten =Cards(algemeenfondskaarte)
        self.spaces:list[Space] = [
            GO(),
            Street(1, "dorpstraat", 60, "ons dorp", [2,10,30,90,160,250], 50),
            AlgemeenFondsCard(2, "algemeen fonds 1", algemeenfondskaarten),
            Street(3, 'brink', 60, 'ons dorp', [4,20,60,180,320,450], 50),
            Tax(4, 'inkomstenbelasting', 200),
            Station(5, 'zuid', 200),
            Street(6, 'steenstraat', 100, 'arnhem', [6,30,90,270,400,550], 50),
            ChanceCard(7, 'kans 1', kanskaarten),
            Street(8, 'ketelstraat', 100, 'arnhem', [6,30,90,270,400,550], 50),
            Street(9, 'velperplein', 120, 'arnhem', [8,40,100,300,450,600], 50),
            FreeParking(10, 'bak'), # jail is like a free parking if you just step on it
            Street(11, 'barteljorisstraat', 140, 'haarlem', [10,50,150,450,625,750], 100),
            Utility(12, 'electriciteitsbedrijf', 150),
            Street(13, 'zijlweg', 140, 'haarlem', [10,50,150,450,625,750], 100),
            Street(14, 'houtstraat', 160, 'haarlem', [12,60,180,500,700,900], 100),
            Station(15, 'west', 200),
            Street(16, 'neude', 180, 'utrecht', [14,70,200,550,750,950], 100),
            AlgemeenFondsCard(17, 'algemeen fonds 2', algemeenfondskaarten),
            Street(18, 'biltstraat', 180, 'utrecht', [14,70,200,550,750,950], 100),
            Street(19, 'vreeburg', 200, 'utrecht', [16,80,220,600,800,1000], 100),
            FreeParking(20, 'free parking'),
            Street(21, 'a-kerkhof', 220, 'groningen', [18,90,250,700,875,1050], 150),
            ChanceCard(22, 'kans 2', kanskaarten),
            Street(23, 'grote markt', 220, 'groningen', [18,90,250,700,875,1050], 150),
            Street(24, 'herestraat', 240, 'groningen', [20,100,300,750,925,1100], 150),
            Station(25, 'noord', 200),
            Street(26, 'spui', 260, 'den haag', [22,110,330,800,975,1150], 150),
            Street(27, 'plein', 260, 'den haag', [22,110,330,800,975,1150], 150),
            Utility(28, 'waterleidingsbedrijf', 150),
            Street(29, 'lange poten', 280, 'den haag', [24,120,360,850,1025,1200], 150),
            GoToJail(),
            Street(31, 'hofplein', 300, 'rotterdam', [26,130,390,900,1100,1275], 200),
            Street(32, 'blaak', 300, 'rotterdam', [26,130,390,900,1100,1275], 200),
            AlgemeenFondsCard(33, 'algemeen fonds 3', algemeenfondskaarten),
            Street(34, 'coolsingel', 320, 'rotterdam', [28,150,450,1000,1200,1400], 200),
            Station(35, 'oost', 200),
            ChanceCard(36, 'kans 3', kanskaarten),
            Street(37, 'leidsche straat', 350, 'amsterdam', [35,175,500,1100,1300,1500], 200),
            Tax(38, 'extra belasting', 100),
            Street(39, 'kalverstraat', 400, 'amsterdam', [50,200,600,1400,1700,2000],200)
        ]
    def serialise(self)->dict:
        raise NotImplementedError()

if __name__ == "__main__":
    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")

    board = Board()

    cities = ['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam']
    for i, space in enumerate(board.spaces):
        print(space.name)
        if not i==space.position: print("wrong position")
        if isinstance(space, Street):
            if not space.city in cities:
                print("invalid city")
