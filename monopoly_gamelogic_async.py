import websockets.connection
from monopoly_board_asyncfriendly import BoardAsync, Cards, Street
from monopoly_player import Player
# from monopoly_player_actions import actionTypes
import random
from  itertools import cycle
from typing import Optional, List, Any, TYPE_CHECKING
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
        self.clients:dict[str:Connection] = {}
        self.currently_playing_uuid:str = None
        self.currently_playing_client:Optional[Connection] = None
        self.finished = False
        self.winner = None
        self.gameReadyToStart = asyncio.Event()
        self.send_queue = send_queue # This queue should only be added to by this class. The queue should only contain type "Message"
        self.waiting_on_client:Optional[Connection] = None
        self.throw:int = 0
        self.players_iterator = None
        self.waiting_for_actionType:Optional[str] = None


    # websockets stuff
    def serialise(self)->dict:
        serialised_players:dict = {client_uuid:client.serialise() for client_uuid, client in self.clients.items()}
        serialised_board = self.board.serialise()
        if self.currently_playing_client is None:
            return {
            # 'turn': self.turn,
            'n_players': len(self.clients.values()),
            'finished': self.finished,
            'currently playing': None,
            'players': serialised_players,
            'throw': self.throw,
            'board': serialised_board
        }
        else:
            return {
                # 'turn': self.turn,
                'n_players': len(self.clients.values()),
                'finished': self.finished,
                'currently playing': self.currently_playing_client.name,
                'players': serialised_players,
                'throw': self.throw,
                'board': serialised_board
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
    # async def disconnect_client(self, client_uuid:str):
    #     print(f"Disconnecting a client")
    #     print(self.clients)
    #     print(f'Trying to disconnect uuid {client_uuid}')
    #     print(f"[DEBUG] {len(self.clients.keys())}")
    #     if client_uuid in self.clients.keys():
    #         self.clients.pop(client_uuid)
    #     print(f"[DEBUG] {len(self.clients.keys())}; Disconnected a client")
    #     # Remove a client from the player iterator cycle, preserving order and current position
    #     # Convert the current cycle to a list, preserving order from current position
    #     if self.players_iterator is None: return # if it isnt assigned yet, then we have not to do anything

    #     if self.currently_playing_uuid == client_uuid:
    #         self.__next_turn()
    #     # Reconstruct the player list from the current clients dict, preserving order from the iterator
    #     all_players = list(self.clients.keys())
    #     # Remove the client_uuid
    #     current_players = [uuid for uuid in all_players if uuid != client_uuid]
    #     if len(current_players) < 2:
    #         self.finished = True
    #         self.winner = current_players[0] if current_players else None
    #         return
    #     # Find the current position in the new list
    #     try:
    #         idx = current_players.index(self.currently_playing_uuid)
    #     except ValueError:
    #         idx = 0
    #     ordered_players = current_players[idx:] + current_players[:idx]
    #     self.players_iterator = cycle(ordered_players)
    #     await self.broadcast_gamestate()

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

   
    # Game logic and flow
    async def __buysell_houses(self):
        raise NotImplementedError("[ERROR] buying and selling houses is not implemented")
    async def __change_mortgages(self):
        raise NotImplementedError("[ERROR] mortgaging is not implemented")
    async def __offer_trade(self):
        raise NotImplementedError("[ERROR] offering trades is not implemented")


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
                'buy/sell house': await self.__buysell_houses(),
                'mortgage': await self.__change_mortgages(),
                'request trade': await self.__offer_trade()
            }
            choice_func = handlers[choice]
            choice_func()
            await self.__before_throw_menu() # recursive. The exit condition is when they want to throw dice
        return
    
    def __next_turn(self):
        self.currently_playing_uuid = self.players_iterator.__next__()
        self.currently_playing_client = self.clients[self.currently_playing_uuid]        
    

    async def do_1_turn_1_player(self):
        self.throw = 0
        print("Start of next turn")
        self.__next_turn()
        assert isinstance(self.currently_playing_client, Connection)
        await self.broadcast_gamestate()
        print(f"The current player is {self.currently_playing_client}. They are standing on space {self.board.spaces[self.currently_playing_client.position]}")
        print(f"The current player has {self.currently_playing_client.money} money")
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
        if not_finished_count<2:
            self.finished = True

    def __throw_dice(self)->int:
        throw = random.randint(1,6) + random.randint(1,6)
        print(f"{throw} thrown")
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