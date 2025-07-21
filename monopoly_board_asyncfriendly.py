from  __future__  import annotations
from abc import ABC, abstractmethod
import random
from collections import deque
from typing import TYPE_CHECKING, Optional, List
import asyncio
from monopoly_message import Message
if TYPE_CHECKING:
    # from monopoly_player import Player
    from monopoly_gamelogic_async import Connection, GameLogic_async
from monopoly_player_actions import PlayerActionReply, PlayerActionRequest, ClientDisconnectedError


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
    def __init__(self, position:int, name:str, game:GameLogic_async):
        self.position = position
        self.name = name
        self.game = game

    def __repr__(self):
        return self.name

    @abstractmethod
    async def on_land(self, client:Connection):
        pass

    @property
    @abstractmethod
    def purchasable(self)->bool:
        pass

    @property
    @abstractmethod
    def space_type(self)->str:
        pass

    @abstractmethod
    def serialise(self)->dict:
        pass


    
class Property(Space, ABC):
    def __init__(self,position:int, name:str, price:int, game:GameLogic_async):
        super().__init__(position=position, name=name, game = game)
        self.price = price
        self.owner:Optional[Connection] = None
        self.morgaged = False
        
    @property
    def purchasable(self)->bool:
        return True

    def purchase(self, client:Connection):
        if self.owner is None and client.money >= self.price:
            client.pay(self.price)
            self.owner = client
            client.properties.append(self)
            print(f"{client.name} bought {self.name} for ${self.price}")
            client.update_completed_sets()
        else:
            print(f"{self.name} is not available for purchase for you.")


    @property
    @abstractmethod
    def buildable(self)->bool:
        pass

    @abstractmethod
    def serialise(self)->dict:
        pass

    @abstractmethod
    def calculate_rent(self, diceroll:Optional[int] = None)->int: # this function assumes no mortgages
        pass

    async def offer_purchase(self,client:Connection): # this funciton requires client input. fOllow the exaple set by GameLogic_async.__before_throw_menu
        print(f"[GAME CONTROL FLOW INFO] {client.name} can buy {self.name} for ${self.price}.")

        action_want_to_buy_property = PlayerActionRequest('want to buy property')
        try:
            choice:str = await action_want_to_buy_property.take_player_input(self.game)
        except ClientDisconnectedError as e:
            raise e
        match choice:
            case 'yes':
                self.purchase(client)
                return
            case 'no':
                return
            case _:
                raise RuntimeError("Unreachable")

    async def on_land(self,player:Connection):
        if self.owner is None:
            await self.offer_purchase(player)
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
    def mortgage(self, client:Connection):
        pass

    @abstractmethod
    def unmortgage(self, client:Connection):
        pass

class Street(Property):
    def __init__(self, position:int, name:str, price:int, city:str, base_rent:list[int], house_cost:int, game:GameLogic_async):
        super().__init__(position, name, price, game)
        self.city = city
        self.base_rent = base_rent# rent depending on number of houses, 0-5 ; 5 ==hotel; 0==empty
        self.house_count:int = 0
        self.HOUSE_COST = house_cost


    def serialise(self)->dict:
        if self.owner:
            return {
                'position': self.position,
                'name': self.name,
                'price': self.price,
                'city': self.city,
                'house count': self.house_count,
                'space type': self.space_type,
                'owner': self.owner.name
            }
        else:
            return {
                'position': self.position,
                'name': self.name,
                'price': self.price,
                'city': self.city,
                'house count': self.house_count,
                'space type': self.space_type,
                'owner': 'not purchased yet'
            }

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

    def mortgage(self,client:Connection):
        raise RuntimeError("Not implemented yet")
    
    def unmortgage(self,client:Connection):
        raise RuntimeError("Not implemented yet")

class Utility(Property):
    def __init__(self, position:int, name:str, price:int, game:GameLogic_async):
        super().__init__(position, name, price, game)

    @property
    def buildable(self)->bool:
        return False
    
    @property
    def space_type(self)->str:
        return "utility"
    
    def mortgage(self,client:Connection):
        raise RuntimeError("Not implemented yet")
    
    def unmortgage(self,client:Connection):
        raise RuntimeError("Not implemented yet")
    
    def serialise(self)->dict:
        if self.owner:
            return {
                'position': self.position,
                'name': self.name,
                'price': self.price,
                'space type': self.space_type,
                'owner': self.owner.name
            }
        else:
            return {
                'position': self.position,
                'name': self.name,
                'price': self.price,
                'space type': self.space_type,
                'owner': 'not purchased yet'
            }

    
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
    def __init__(self, position:int, name:str, price:int, game:GameLogic_async):
        super().__init__(position, name, price, game)

    @property
    def buildable(self)->bool:
        return False
    
    @property
    def space_type(self)->str:
        return "station"
    
    def serialise(self)->dict:
        if self.owner:
            return {
                'position': self.position,
                'name': self.name,
                'price': self.price,
                'space type': self.space_type,
                'owner': self.owner.name
            }
        else:
            return {
                'position': self.position,
                'name': self.name,
                'price': self.price,
                'space type': self.space_type,
                'owner': 'not purchased yet'
            }

    def mortgage(self,client:Connection):
        raise RuntimeError("Not implemented yet")
    
    def unmortgage(self,client:Connection):
        raise RuntimeError("Not implemented yet")
    
    def calculate_rent(self, diceroll:Optional[int] = None)->int:
        if self.owner is None: raise RuntimeError("This property had its rent calculated but it doesnt have an owner")
        owner_station_count = sum(1 for eigendom in self.owner.properties if isinstance(eigendom, Station))
        rents = [0,25,50,100,200]
        rent = rents[owner_station_count]
        return rent


class CardSpace(Space, ABC):            # THIS NEEDS TO BE COMPLETELY REFACTORED. THE CARDS ARE GLOBAL AND BELONG TO THE BOARD, NOT THE INDIVIDUAL SPACE
    def __init__(self, position:int, name:str, cards:Cards, game:GameLogic_async):
        super().__init__(position, name, game)
        self.deck = cards
    
    async def on_land(self, client:Connection): # TODO make this actually do something
        card:str = self.deck.draw()
        print(f"Player {client.name} drew a card that says: {card}")
        
    @property
    def purchasable(self)->bool:
        return False

    def serialise(self)->dict:
        return {
            'position': self.position,
            'name': self.name,
            'space type': self.space_type
        }
    
class ChanceCard(CardSpace):
    def __init__(self, position:int, name:str, cards:Cards, game:GameLogic_async):
        super().__init__(position, name, cards, game)

    @property
    def space_type(self)->str:
        return "chance card"
    

class AlgemeenFondsCard(CardSpace):
    def __init__(self, position:int, name:str, cards:Cards, game:GameLogic_async):
        super().__init__(position, name, cards, game)

    @property
    def space_type(self)->str:
        return "algemeen fonds card"
    

class Tax(Space):
    def __init__(self, position:int, name:str, amount:int, game:GameLogic_async):
        super().__init__(position, name, game)
        self.amount = amount

    async def on_land(self, client:Connection):
        client.pay(self.amount)
    
    @property
    def purchasable(self)->bool:
        return False
    @property
    def space_type(self)->str:
        return "tax"
    
    def serialise(self)->dict:
        return {
            'position': self.position,
            'name': self.name,
            'space type': self.space_type
        }
        

class GO(Space):
    def __init__(self, game:GameLogic_async):
        super().__init__(position=0, name="GO", game = game)

    async def on_land(self,client:Connection):
        return

    @property
    def purchasable(self)->bool:
        return False

    @property
    def space_type(self)->str:
        return "go"

    def serialise(self)->dict:
        return {
            'position': self.position,
            'name': self.name,
            'space type': self.space_type
        }
    

class GoToJail(Space):
    JailPosition = 10
    def __init__(self, game:GameLogic_async):
        super().__init__(position = 30, name = "Go to jail", game=game)
    async def on_land(self, client:Connection):
        client.position = self.JailPosition
        client.jailtime = 3

    @property
    def purchasable(self)->bool:
        return False
    @property
    def space_type(self)->str:
        return "go to jail"
    
    def serialise(self)->dict:
        return {
            'position': self.position,
            'name': self.name,
            'space type': self.space_type
        }


class FreeParking(Space):
    def __init__(self, position:int, name:str, game:GameLogic_async):
        super().__init__(position, name, game)
    
    async def on_land(self, client:Connection):
        print(f"Player {client.name} landed on a free space and does nothing")
    @property
    def space_type(self)->str:
        return "free parking"
    @property
    def purchasable(self)->bool:
        return False
    
    def serialise(self)->dict:
        return {
            'position': self.position,
            'name': self.name,
            'space type': self.space_type
        }



class BoardAsync:
    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")
    def __init__(self, game:GameLogic_async, kanskaarte:Optional[List[str]] = None, algemeenfondskaarte:Optional[List[str]] = None):
        if kanskaarte is None:
            kanskaarte = self.kaartenkans
        if algemeenfondskaarte is None:
            algemeenfondskaarte = self.kaartenalgemeenfonds
        kanskaarten = Cards(kanskaarte)
        algemeenfondskaarten =Cards(algemeenfondskaarte)
        self.spaces:list[Space] = [
            GO(game),
            Street(1, "dorpstraat", 60, "ons dorp", [2,10,30,90,160,250], 50, game),
            AlgemeenFondsCard(2, "algemeen fonds 1", algemeenfondskaarten, game),
            Street(3, 'brink', 60, 'ons dorp', [4,20,60,180,320,450], 50, game),
            Tax(4, 'inkomstenbelasting', 200, game),
            Station(5, 'zuid', 200, game),
            Street(6, 'steenstraat', 100, 'arnhem', [6,30,90,270,400,550], 50, game),
            ChanceCard(7, 'kans 1', kanskaarten, game),
            Street(8, 'ketelstraat', 100, 'arnhem', [6,30,90,270,400,550], 50, game),
            Street(9, 'velperplein', 120, 'arnhem', [8,40,100,300,450,600], 50, game),
            FreeParking(10, 'bak', game), # jail is like a free parking if you just step on it
            Street(11, 'barteljorisstraat', 140, 'haarlem', [10,50,150,450,625,750], 100, game),
            Utility(12, 'electriciteitsbedrijf', 150, game),
            Street(13, 'zijlweg', 140, 'haarlem', [10,50,150,450,625,750], 100, game),
            Street(14, 'houtstraat', 160, 'haarlem', [12,60,180,500,700,900], 100, game),
            Station(15, 'west', 200, game),
            Street(16, 'neude', 180, 'utrecht', [14,70,200,550,750,950], 100, game),
            AlgemeenFondsCard(17, 'algemeen fonds 2', algemeenfondskaarten, game),
            Street(18, 'biltstraat', 180, 'utrecht', [14,70,200,550,750,950], 100, game),
            Street(19, 'vreeburg', 200, 'utrecht', [16,80,220,600,800,1000], 100, game),
            FreeParking(20, 'free parking', game),
            Street(21, 'a-kerkhof', 220, 'groningen', [18,90,250,700,875,1050], 150, game),
            ChanceCard(22, 'kans 2', kanskaarten, game),
            Street(23, 'grote markt', 220, 'groningen', [18,90,250,700,875,1050], 150, game),
            Street(24, 'herestraat', 240, 'groningen', [20,100,300,750,925,1100], 150, game),
            Station(25, 'noord', 200, game),
            Street(26, 'spui', 260, 'den haag', [22,110,330,800,975,1150], 150, game),
            Street(27, 'plein', 260, 'den haag', [22,110,330,800,975,1150], 150, game),
            Utility(28, 'waterleidingsbedrijf', 150, game),
            Street(29, 'lange poten', 280, 'den haag', [24,120,360,850,1025,1200], 150, game),
            GoToJail(game),
            Street(31, 'hofplein', 300, 'rotterdam', [26,130,390,900,1100,1275], 200, game),
            Street(32, 'blaak', 300, 'rotterdam', [26,130,390,900,1100,1275], 200, game),
            AlgemeenFondsCard(33, 'algemeen fonds 3', algemeenfondskaarten, game),
            Street(34, 'coolsingel', 320, 'rotterdam', [28,150,450,1000,1200,1400], 200, game),
            Station(35, 'oost', 200, game),
            ChanceCard(36, 'kans 3', kanskaarten, game),
            Street(37, 'leidsche straat', 350, 'amsterdam', [35,175,500,1100,1300,1500], 200, game),
            Tax(38, 'extra belasting', 100, game),
            Street(39, 'kalverstraat', 400, 'amsterdam', [50,200,600,1400,1700,2000],200, game)
        ]
    def serialise(self)->dict:
        print("[DEBUG] Serialising board")
        representation = {}
        for space in self.spaces:
            representation.update({space.position: space.serialise()})
        return representation

if __name__ == "__main__":
    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")

    board = BoardAsync()

    cities = ['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam']
    for i, space in enumerate(board.spaces):
        print(space.name)
        if not i==space.position: print("wrong position")
        if isinstance(space, Street):
            if not space.city in cities:
                print("invalid city")
