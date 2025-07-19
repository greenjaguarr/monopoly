from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from monopoly_board import Property, Street

class Player: # This is not for online play
    def __init__(self, naam:str):
        self.name = naam
        self.position = 0
        self.most_recent_diceroll:int = -1
        self.properties:list[Property] = []
        self.complete_sets:Set[str] = set([])
        self.money:int = 1500
        self.jailtime = 0
        self.has_lost = False
        

    def __repr__(self):
        return self.name
    
    def serialise(self)->dict:
        return {
            'name': self.name,
            'position': self.position,
            'money': self.money,
            'jailtime': self.jailtime,
            'has_lost': self.has_lost,
            'properties': [propertie.position for propertie in self.properties]
        }
        

    def pay(self, amount:int):
        if amount > self.money:
            print(f"Player {self.name} is about to go belly up")
            self.has_lost = True
        self.money-=amount
        print(f"Player {self.name} payed {amount} and is now left with {self.money}")

    def receive(self, amount:int):
        self.money+=amount
        print(f"Player {self.name} received {amount}")

    def update_completed_sets(self) -> None:
        from monopoly_board import Street
        from collections import defaultdict
        city_amounts: dict[str, int] = defaultdict(int)
        for p in self.properties:
            if not isinstance(p, Street): continue
            city = p.city
            city_amounts[city] += 1

        cities = ['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam']
        for city in cities:
            
            if city_amounts[city] == 3: self.complete_sets.add(city)
            if city_amounts[city] == 2 and city in ['ons dorp', 'amsterdam']: self.complete_sets.add(city)
        
        print(f"Updated completed sets for player {self.name}: {dict(city_amounts)}")

    def walk(self, steps:int):
        self.position+=steps
        if self.position >= 40:
            print(f"PLayer {self.name} passed GO, collecting 200")
            self.position-=40
            self.receive(200)