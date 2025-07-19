import websockets.connection
from monopoly_board_asyncfriendly import BoardAsync, Cards, Street
from monopoly_player import Player
from monopoly_player_actions import actionTypes
import random
from  itertools import cycle
from typing import Optional, List, Any
import asyncio
import websockets
import json
from monopoly_message import Message
from monopoly_connection import Connection
# TODO add gamestate lock, to stop race conditions from happening when the gamestate is modified and used at the same time






class GameLogic_async:
    number_of_players_to_start = 2 # TODO make this not hard-coded
    def __init__(self, send_queue: asyncio.Queue, actionType:actionTypes): # do a little bit here, just enough to get off the ground
        self.actionType = actionType
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

    async def disconnect_client(self, client_uuid:str):
        print(f"Disconnecting a client")
        print(self.clients)
        print(f'Trying to disconnect uuid {client_uuid}')
        print(f"[DEBUG] {len(self.clients.keys())}")
        if client_uuid in self.clients.keys():
            self.clients.pop(client_uuid)
        print(f"[DEBUG] {len(self.clients.keys())}; Disconnected a client")
        # Remove a client from the player iterator cycle, preserving order and current position
        # Convert the current cycle to a list, preserving order from current position
        if self.players_iterator is None: return # if it isnt assigned yet, then we have not to do anything

        if self.currently_playing_uuid == client_uuid:
            self.__next_turn()
        # Reconstruct the player list from the current clients dict, preserving order from the iterator
        all_players = list(self.clients.keys())
        # Remove the client_uuid
        current_players = [uuid for uuid in all_players if uuid != client_uuid]
        if len(current_players) < 2:
            self.finished = True
            self.winner = current_players[0] if current_players else None
            return
        # Find the current position in the new list
        try:
            idx = current_players.index(self.currently_playing_uuid)
        except ValueError:
            idx = 0
        ordered_players = current_players[idx:] + current_players[:idx]
        self.players_iterator = cycle(ordered_players)
        await self.broadcast_gamestate()

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
        input_is_valid = False
        while not input_is_valid:
            self.waiting_on_client = self.currently_playing_client
            self.waiting_for_actionType = self.actionType.before_throw_menu_reply
            # We must send to the client the notification that we are waiting for them to give us input
            msg = Message(self.currently_playing_client,
                           {'type': 'action request',
                            'action type': self.actionType.before_throw_menu})
            # await self.send_queue.put(msg) # This should be wrong but it appears to work
            await self.send_queue.put(msg.msg)
            player_action = await self.currently_playing_client.wait_for_client_input()
            assert isinstance(player_action, dict)
            if player_action.get('action type', None) != self.actionType.before_throw_menu_reply:
                print(f"[WARNING] player {self.currently_playing_client} sent an invalid action")           # TODO add more advances error feedback
                continue # Let them try again
            choice = player_action.get('choice')
            if not choice in self.actionType.before_throw_menu_valid:
                print(f"[WARNING] player {self.currently_playing_client} sent an invalid action")           # TODO add more advances error feedback
                continue
            input_is_valid = True # and fall out of the loop
        # reset some stuff ; agknowledge the correct action reply from the client
        assert self.waiting_on_client == self.currently_playing_client
        message = Message(client = self.waiting_on_client, msg = {'type': 'agnowledge correct action reply'})
        await self.send_queue.put(message.msg)
        self.waiting_on_client = None # we are not waiting on client input, we can continue executing
        self.waiting_for_actionType = None # There is no waiting so there is no actionType to wait for

        if not choice == 'throw':
            handlers = {
                'buy/sell house': await self.__buysell_houses(),
                'mortgage': await self.__change_mortgages(),
                'request trade': await self.__offer_trade()
            }
            choice_func = handlers[player_action]
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
        
        await self.__before_throw_menu()
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
        await asyncio.sleep(1)
        self.currently_playing_client.walk(steps = self.throw)
        landing_space = [space for space in self.board.spaces if space.position == self.currently_playing_client.position]
        if not len(landing_space) == 1: raise RuntimeError("")
        landing_space = landing_space[0]
        print(f"Player {self.currently_playing_client} landed on {landing_space}; sending broadcast to inform everyone")
        await self.broadcast_gamestate()
        await asyncio.sleep(1)
        try:
            await landing_space.on_land(self.currently_playing_client)
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
        await asyncio.sleep(1)
        

    def check_finished(self):
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
    
    actionTypeasdf = actionTypes()  

    kaartenkans = [f"kanskaart {i}" for i in range(10)]
    kaartenalgemeenfonds = [f"algemeen fondskaart {i}" for i in range(10)]
    kaartenkans.append("get out of jail kans")
    kaartenalgemeenfonds.append("get out of jail algemeenfonds")
    send_queue = asyncio.Queue()
    game = GameLogic_async(send_queue,actionTypeasdf)
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