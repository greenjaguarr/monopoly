import websockets.connection
from monopoly_board_asyncfriendly import BoardAsync, Cards, Street, Property
from monopoly_player import Player
# from monopoly_player_actions import actionTypes
import random
from  itertools import cycle
from typing import Optional, List, Any, TYPE_CHECKING, Dict
import asyncio
import websockets
import json
from monopoly_message import Message
from monopoly_connection import Connection, ClientDisconnectedError
# TODO add gamestate lock, to stop race conditions from happening when the gamestate is modified and used at the same time
from monopoly_player_actions import PlayerActionRequest




class GameLogic_async:
    number_of_players_to_start = 3 # TODO make this not hard-coded
    def __init__(self, send_queue: asyncio.Queue): # do a little bit here, just enough to get off the ground
        self.board = BoardAsync(self)
        self.clients:Dict[str:Connection] = {}
        self.currently_playing_uuid:str = None
        self.currently_playing_client:Optional[Connection] = None
        self.finished = False
        self.winner = None
        self.gameReadyToStart = asyncio.Event()
        self.send_queue = send_queue # This queue should only be added to by this class. The queue should only contain type "Message"
        self.throw:int = 0
        self.players_iterator = None
        self.waiting_on_client:Optional[Connection] = None
        self.waiting_for_actionType:Optional[str] = None


    # websockets stuff
    def serialise(self)->dict:
        serialised_players:dict = {client_uuid:client.serialise() for client_uuid, client in self.clients.items()}
        serialised_board = self.board.serialise()
        waiting_for_client = self.waiting_on_client if self.waiting_on_client else None
        if self.currently_playing_client is None:
            return {
            # 'turn': self.turn,
            'n_players': len(self.clients.values()),
            'finished': self.finished,
            'currently playing': None,
            'players': serialised_players,
            'throw': self.throw,
            'board': serialised_board,
            'winner': self.winner,
            'waiting for player': waiting_for_client,
            'waiting for action type': self.waiting_for_actionType
        }
        else:
            return {
                # 'turn': self.turn,
                'n_players': len(self.clients.values()),
                'finished': self.finished,
                'currently playing': self.currently_playing_client.name,
                'players': serialised_players,
                'throw': self.throw,
                'board': serialised_board,
                'waiting for player': waiting_for_client,
                'waiting for action type': self.waiting_for_actionType
            }
    
    async def broadcast(self, msg_content:dict):
        print("[DEBUG] broadcasting")
        await asyncio.sleep(0.1)
        for client_uuid, client in self.clients.items():
            if client.soft_disconnected:
                print(f'[DEBUG] dont broadcast to client {client} because they are soft disconnected')
                continue
            print(f"[DEBUG] broadcast target: {client}")
            msg = Message(client, msg_content)
            await self.send_queue.put(msg.msg)
            await asyncio.sleep(0.1)


    async def broadcast_gamestate(self):
        print("[DEBUG] broadcasting gamestate to:", [client.name for client in self.clients.values()])
        msg_content = self.serialise()
        message = {'type': 'gamestate update',
                   'content': msg_content}
        await self.broadcast(message)

    
    async def add_client(self,client:Connection)->None:
        print(f"[INFO] Adding a client {client.name} with uuid {client.uuid}")
        self.clients.update({client.uuid: client})
        if len(self.clients.keys()) >= self.number_of_players_to_start:
            self.gameReadyToStart.set()
        await self.broadcast_gamestate()

    def mark_client_as_disconnected(self, client_uuid):
        # may raise keyError
        self.clients[client_uuid].soft_disconnected = True
        

    async def cleanup_disconnect(self):
        print("[GAME FLOW] cleaning up disconnects", f'There are {len(self.clients)} players remaining')
        if any(client.soft_disconnected for client in self.clients.values()):
            disconnected_uuids = [uuid for uuid, client in self.clients.items() if client.soft_disconnected]
            for uuid in disconnected_uuids:
                print(f"[INFO] Removing disconnected client: {self.clients[uuid].name} ({uuid})")
                for propertie in self.clients[uuid].properties:
                    assert isinstance(propertie, Property)
                    propertie.owner = None
                    propertie.house_count = 0
                self.clients.pop(uuid)
            # Rebuild the player iterator if needed
            if self.players_iterator is not None and self.clients:
                ordered_players = list(self.clients.keys())
                self.players_iterator = cycle(ordered_players)
                # If the current player was disconnected, advance to the next
                if self.currently_playing_uuid not in self.clients:
                    self.__next_turn()
            # Check if game should finish
            if len(self.clients) < 2:
                self.finished = True
                self.winner = next(iter(self.clients.values()), None)
            await self.broadcast_gamestate()
        print("[INFO] cleaning up disconnects", f'There are {len(self.clients)} players remaining')

    # Game startup
    async def wait_for_players_to_join(self):
        print("Waiting for players to join...")
        await self.gameReadyToStart.wait()
        print("Players have joined, starting game.") 
        # notify the players of this
        msg = {'type': 'game is starting'}
        await self.broadcast(msg)
        return

    def startup(self): # extra startup stuff
        # make an iterator
        # maybe make it so the order is based on something
        self.players_iterator = cycle(self.clients.keys())
        for _ in range(random.randint(1,50)):
            self.__next_turn()

   
    # Game logic and flow

    async def ____buysell_inner(self,locations:List[int]):
        print("[GAME FLOW] player is now in inner loop of buy sell houses")
                # Handle Ons Dorp city
        city_locations = locations
        city:List[Street] = [street for street in self.board.spaces if street.position in city_locations]
        assert all([isinstance(street, Street) for street in city])
        print(f"[GAME FLOW] {self.currently_playing_client.name} selected Ons Dorp for buy/sell houses")
        city_distribution:List[int] = [street.house_count for street in city]
        city_desired:List[int] = [street.house_count for street in city]
        action_houses_city = PlayerActionRequest(f'buy sell houses amount {len(city_locations)}')

        confirm_inner = False
        while True:
            extra_info = {
                'city': city[0].city,
                'city_distribution': city_distribution,
                'city_desired': city_desired,
                'house cost': city[0].HOUSE_COST
            }
            desired_change = await action_houses_city.take_player_input(self, extra_display_info=extra_info)
            match desired_change:
                case 'increase 1':
                    city_desired[0]+=1
                case 'decrease 1':
                    city_desired[0]-=1
                case 'increase 2':
                    city_desired[1]+=1
                case 'decrease 2':
                    city_desired[1]-=1
                case 'increase 3':
                    city_desired[2]+=1
                case 'decrease 3':
                    city_desired[2]-=1
                case 'back':
                    break
                case 'finish':
                    confirm_inner = True
                    break
                case _:
                    raise RuntimeError("Unreachable")
        if confirm_inner:
            print(f"[GAME FLOW] {self.currently_playing_client.name} confirmed the changes to the houses")
            print(f"[DEBUG] city distribution: {city_distribution}")
            print(f"[DEBUG] city desired: {city_desired}")
            difference = [int(desired) - int(current) for current, desired in zip(city_distribution, city_desired)]
            for i, diff in enumerate(difference):
                while not diff == 0:
                    if diff>0:
                        city[i].build_house()
                        self.currently_playing_client.pay(city[i].HOUSE_COST)
                        diff-=1
                    elif diff<0:
                        city[i].sell_house()
                        self.currently_playing_client.receive(city[i].HOUSE_COST // 2)
                        diff+=1
        else:
            pass # we dont execute the requested changes
        await self.broadcast_gamestate()
        print(f"[GAME FLOW] {self.currently_playing_client.name} exited the buy/sell houses inner loop")

    async def __buysell_houses(self):
        self.currently_playing_client.update_completed_sets()
        # raise NotImplementedError("[ERROR] buying and selling houses is not implemented")
        print(f"[GAME FLOW] {self.currently_playing_client.name} is entering the buy/sell houses menu")
        action_which_city_menu = PlayerActionRequest('buy sell houses city menu')
        
        finished = False
        while not finished:
            valid_choice_of_city = self.currently_playing_client.complete_sets
            choice: str = await action_which_city_menu.take_player_input(self)
            print(f"[DEBUG] player made achoice for which city to build on; they chose {choice}")

            match choice:
                case 'ons dorp':
                    # Handle Ons Dorp city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([1,3])
                case 'arnhem':
                    # Handle Arnhem city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([6,8,9])
                case 'haarlem':
                    # Handle Haarlem city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([11,13,14])
                case 'utrecht':
                    # Handle Utrecht city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([16,18,19])
                case 'groningen':
                    # Handle Groningen city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([21,23,24])
                case 'den haag':
                    # Handle Den Haag city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([26,27,29])
                case 'rotterdam':
                    # Handle Rotterdam city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([31,32,34])
                case 'amsterdam':
                    # Handle Amsterdam city
                    if choice not in valid_choice_of_city: continue
                    await self.____buysell_inner([37,39])
                case 'return':
                    finished = True
                case _:
                    print("Impossible city selected", choice)
                    raise RuntimeError("Unreachable")
        print("[GAME FLOW] Player is exiting the buy houses menu")


    async def __change_mortgages(self):
        # raise NotImplementedError("[ERROR] mortgaging is not implemented")
        print(f"[GAME FLOW] {self.currently_playing_client.name} is entering the mortgage menu")
        pass


    async def __offer_trade_what_inner(self, who_initiate_uuid: str, who_target_uuid: str) -> dict:
        """
        Inner loop for building a trade offer. Allows initiator to add/remove money and properties to give/get.
        Returns a dict with 'give' and 'get' keys.
        """
        initiator = self.clients[who_initiate_uuid]
        target = self.clients[who_target_uuid]

        trade = {
            'give': {'money': 0, 'properties': []},
            'get': {'money': 0, 'properties': []}
        }

        while True:
            # Prepare display info for the menu
            extra_info = {
                'your_money': initiator.money,
                'your_properties': [p.name for p in initiator.properties],
                'target_money': target.money,
                'target_properties': [p.name for p in target.properties],
                'trade': trade
            }
            action = PlayerActionRequest('offer trade build', extra_display_info=extra_info)
            choice = await action.take_player_input(self)

            def validate_is_a_number(choice:str):
                try:
                    result = int(choice)
                    return True
                except:
                    return False
            match choice:
                case 'add give money':
                    # Ask how much money to give
                    amount_action = PlayerActionRequest('offer trade give money amount', extra_display_info=extra_info, validate_response=validate_is_a_number)
                    amount = await amount_action.take_player_input(self)
                    try:
                        amount = int(amount)
                        if 0 <= amount <= initiator.money:
                            trade['give']['money'] = amount
                    except Exception:
                        pass
                case 'add get money':
                    amount_action = PlayerActionRequest('offer trade get money amount', extra_display_info=extra_info, validate_response=validate_is_a_number)
                    amount = await amount_action.take_player_input(self)
                    try:
                        amount = int(amount)
                        if 0 <= amount <= target.money:
                            trade['get']['money'] = amount
                    except Exception:
                        pass
                case 'add give property':
                    # Choose property to give
                    props = [p.name for p in initiator.properties if p not in trade['give']['properties']]
                    if not props:
                        continue
                    prop_action = PlayerActionRequest('offer trade give property select', valid_responses=props, extra_display_info=extra_info)
                    prop_name = await prop_action.take_player_input(self)
                    for p in initiator.properties:
                        if p.name == prop_name and p not in trade['give']['properties']:
                            trade['give']['properties'].append(p)
                            break
                case 'add get property':
                    props = [p.name for p in target.properties if p not in trade['get']['properties']]
                    if not props:
                        continue
                    prop_action = PlayerActionRequest('offer trade get property select', valid_responses=props, extra_display_info=extra_info)
                    prop_name = await prop_action.take_player_input(self)
                    for p in target.properties:
                        if p.name == prop_name and p not in trade['get']['properties']:
                            trade['get']['properties'].append(p)
                            break
                case 'remove give property':
                    props = [p.name for p in trade['give']['properties']]
                    if not props:
                        continue
                    prop_action = PlayerActionRequest('offer trade remove give property', valid_responses=props, extra_display_info=extra_info)
                    prop_name = await prop_action.take_player_input(self)
                    trade['give']['properties'] = [p for p in trade['give']['properties'] if p.name != prop_name]
                case 'remove get property':
                    props = [p.name for p in trade['get']['properties']]
                    if not props:
                        continue
                    prop_action = PlayerActionRequest('offer trade remove get property', valid_responses=props, extra_display_info=extra_info)
                    prop_name = await prop_action.take_player_input(self)
                    trade['get']['properties'] = [p for p in trade['get']['properties'] if p.name != prop_name]
                case 'reset':
                    trade = {
                        'give': {'money': 0, 'properties': []},
                        'get': {'money': 0, 'properties': []}
                    }
                case 'confirm':
                    return trade
                case 'cancel':
                    return None
                case _:
                    continue

    async def __offer_trade_what(self, who_initiate_uuid: str, who_target_uuid: str) -> dict:
        """
        Wrapper for the trade offer builder.
        """
        trade = await self.__offer_trade_what_inner(who_initiate_uuid, who_target_uuid)
        # validate that this trade is indeed possible: both parties have theright Property and money
        # Validate that initiator and target have the properties and money they are offering/requesting
        if trade:
            initiator = self.clients[who_initiate_uuid]
            target = self.clients[who_target_uuid]
            # Validate initiator has enough money and owns the properties they're giving
            if trade['give']['money'] > initiator.money:
                return {}
            if not all(p in initiator.properties for p in trade['give']['properties']):
                return {}
            # Validate target has enough money and owns the properties they're giving
            if trade['get']['money'] > target.money:
                return {}
            if not all(p in target.properties for p in trade['get']['properties']):
                return {}
        return trade if trade else {}

    async def __offer_trade_accept(self, who_initiate_uuid: str, who_target_uuid: str, trade_suggested: dict) -> bool:
        """
        Presents the trade to the target player and asks for accept/reject.
        """
        initiator = self.clients[who_initiate_uuid]
        target = self.clients[who_target_uuid]

        # Prepare a summary of the trade
        trade_summary = {
            'from': initiator.name,
            'to': target.name,
            'give_money': trade_suggested['give']['money'],
            'give_properties': [p.name for p in trade_suggested['give']['properties']],
            'get_money': trade_suggested['get']['money'],
            'get_properties': [p.name for p in trade_suggested['get']['properties']]
        }

        action_accept = PlayerActionRequest(
            'offer trade accept',
            valid_responses=['accept', 'reject'],
            extra_display_info=trade_summary,
            target_player=target
        )
        choice = await action_accept.take_player_input(self)
        return choice == 'accept'

    async def __offer_trade(self):
        print(f"[GAME FLOW] {self.currently_playing_client.name} is entering the trade offer menu")
        names = [client.name for client in self.clients.values() if client.uuid != self.currently_playing_uuid]
        options = {client.name: uuid for uuid, client in self.clients.items() if uuid != self.currently_playing_uuid}
        action_chose_who_to_trade_with = PlayerActionRequest('offer trade menu', valid_responses=[*names, 'cancel'])
        print(action_chose_who_to_trade_with)

        finished = False
        while not finished:
            # take user input
            choice: str = await action_chose_who_to_trade_with.take_player_input(self)
            # handle user input
            match choice:
                case _ if choice in names:
                    # Handle the case where the player chose a valid name
                    target_uuid: str = options[choice]
                    initiate_uuid: str = self.currently_playing_uuid
                    trade_suggestion: dict = await self.__offer_trade_what(initiate_uuid, target_uuid)
                    if not trade_suggestion:
                        continue  # Cancelled or empty trade

                    trade_get = trade_suggestion.get('get', None)
                    trade_give = trade_suggestion.get('give', None)
                    print(f"[INFO] player {self.clients[initiate_uuid].name} wants to trade with {self.clients[target_uuid].name}. They want to give {trade_give} and they want to get {trade_get}")

                    accepted: bool = await self.__offer_trade_accept(initiate_uuid, target_uuid, trade_suggestion)
                    if accepted:
                        # Execute the trade
                        initiator = self.clients[initiate_uuid]
                        target = self.clients[target_uuid]
                        # Transfer money
                        if trade_give and trade_give['money'] > 0:
                            initiator.pay(trade_give['money'])
                            target.receive(trade_give['money'])
                        if trade_get and trade_get['money'] > 0:
                            target.pay(trade_get['money'])
                            initiator.receive(trade_get['money'])
                        # Transfer properties
                        for p in trade_give['properties']:
                            if p in initiator.properties:
                                initiator.properties.remove(p)
                                p.owner = target
                                target.properties.append(p)
                        for p in trade_get['properties']:
                            if p in target.properties:
                                target.properties.remove(p)
                                p.owner = initiator
                                initiator.properties.append(p)
                        await self.broadcast_gamestate()
                        finished = True
                    else:
                        continue  # This will allow the initiator to pick a new person to try to trade with

                case 'cancel':
                    finished = True
                case _:
                    raise RuntimeError(f"Unreachable, I got choice {choice}, but I was expecting either cancel or {names}")

        


        # raise NotImplementedError("[ERROR] offering trades is not implemented")


    async def __before_throw_menu(self): # I made this function recursive for the lolz
        # Step 1: take and validate input action from the client whose turn it is to choose to maybe do something before throwing dice
        print(f"[GAME CONTROL FLOW INFO] {self.currently_playing_client.name} is entering the before throw menu")
        action_before_throw_menu = PlayerActionRequest('before throw menu')
        try:
            choice:str = await action_before_throw_menu.take_player_input(self)
        except ClientDisconnectedError as e:
            print("[INFO] before throw menu is endind because the current player disconnected")
            raise e
        if not choice == 'throw':
            handlers = {
                'buy/sell house': self.__buysell_houses,
                'mortgage': self.__change_mortgages,
                'request trade': self.__offer_trade
            }
            choice_func = handlers[choice]
            await choice_func()
            await self.__before_throw_menu() # recursive. The exit condition is when they want to throw dice
        return
    
    def __next_turn(self):
        self.currently_playing_uuid = self.players_iterator.__next__()
        self.currently_playing_client = self.clients[self.currently_playing_uuid]        
    

    async def do_1_turn_1_player(self):
        self.throw = 0
        print("[GAME FLOW] Start of next turn")
        self.__next_turn()
        assert isinstance(self.currently_playing_client, Connection)
        await self.broadcast_gamestate()
        print(f"[GAME FLOW] The current player is {self.currently_playing_client}. They are standing on space {self.board.spaces[self.currently_playing_client.position]}")
        print(f"[GAME FLOW] The current player has {self.currently_playing_client.money} money")
        # check if they are dead
        if self.currently_playing_client.money<0:
            print("This player is a broke boi so they cant play; NEXT")
            return
        
        try:
            await self.__before_throw_menu()
        except RuntimeError as e:
            raise e
            # since the execution escaped the above function, we know the player wants to throw the dice

        await asyncio.sleep(0)

        # check for player in jail
        if self.currently_playing_client.jailtime!= 0:
            print("This player is in Jail")
            self.currently_playing_client.jailtime-=1
            print("In this game, you dont get to escape jail")
            return

        # now the real turn can start
        self.throw = self.__throw_dice()
        self.currently_playing_client.most_recent_diceroll = self.throw
        await self.broadcast_gamestate()
        await asyncio.sleep(0.1)
        self.currently_playing_client.walk(steps = self.throw)
        landing_space = [space for space in self.board.spaces if space.position == self.currently_playing_client.position]
        if not len(landing_space) == 1: raise RuntimeError("")
        landing_space = landing_space[0]
        print(f"Player {self.currently_playing_client} landed on {landing_space}; sending broadcast to inform everyone")
        await self.broadcast_gamestate()
        await asyncio.sleep(0.1)
        try:
            await landing_space.on_land(self.currently_playing_client)
        except ClientDisconnectedError as e:
            print(f"[ERROR] While player {self.currently_playing_client} landed on {landing_space}, the player disconnected during the on_land function with errormessage: {e}")
            raise e
        except Exception as e:
            print(f"[ERROR] While player {self.currently_playing_client} landed on {landing_space}, an issue occures during the on_land function with errormessage: {e}")
            raise e


        # Send the clkient a message to inform them it is the end of their turn     #TODO make it such there is a clean short way to make a send to a client
        msg_content = {
            'type': 'game control flow',
            'content': 'your turn is up'
        }
        msg = Message(self.currently_playing_client, msg_content)
        await self.send_queue.put(msg.msg)
        # send final gamestate update
        await self.broadcast_gamestate()
        await asyncio.sleep(0)
        

    def check_finished(self):
        print("[GAME FLOW] checking if the game is finished")
        not_finished_count = 0
        for uuid, client in self.clients.items():
            if not client.has_lost:
                not_finished_count+=1
            else:
                for p in client.properties:
                    p.owner = None
        if not_finished_count<2:
            self.finished = True
            for client in self.clients.values():
                if not client.has_lost:
                    self.winner = client.name
                    print(f"[GAME FLOW] {client.name} has won the game")
                    break

    def __throw_dice(self)->int:
        throw = random.randint(1,6) + random.randint(1,6)
        print(f"[GAME FLOW] {throw} thrown by player: {self.currently_playing_client.name}")
        return throw



async def main():

    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")
    send_queue = asyncio.Queue()
    game = GameLogic_async(send_queue)
    await game.wait_for_players_to_join()
    game.startup()
    #
    
    running = True
    turn = 0
    while running:
        game.broadcast_gamestate()
        try:
            await game.do_1_turn_1_player()
        except Exception as e:
            # shutdown_event.set()
            raise e
        turn+=1
        game.check_finished()


if __name__ == "__main__":
    asyncio.run(main())