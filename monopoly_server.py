# server.py
import asyncio
from websockets.asyncio.server import serve
import websockets.exceptions as wsException
import websockets
import json
from monopoly_gamelogic_async import GameLogic_async, Connection, Message, ClientDisconnectedError
from typing import Optional, Tuple
import uuid as Uuid
from monopoly_player_actions import PlayerActionRequest, PlayerActionReply
import sys

clients = set()


GAMESTATE_LOCK = asyncio.Lock()
# game.wait_for_players_to_join()
# game.startup()

VALID_MSG_TYPES = ['action reply', 'disconnect', 'request gamestate', 'i am alive', 'connect spectator']

placeholder_event = asyncio.Event()
placeholder_event.clear()

shutdown_event = asyncio.Event() # I do not know what stuff will need to trigger this, but if I add error handling, this would be interesting
shutdown_event.clear()


def do_sanity_check_on_myself():
    pass

async def game_loop(game:GameLogic_async, send_queue:asyncio.Event):
    assert send_queue == game.send_queue
    try:
        #game.play() # this function should be made async. At several moments, it needs to wait for player input. It does this by awaiting an asyncio.Event
        # a = input("Put input here to stop")
        await game.wait_for_players_to_join()
        game.startup()

        # await game.broadcast_gamestate()
        print("Sys", sys.argv)
        if not len(sys.argv) == 1:
            #  I want to backdoor for testing purposes
            if sys.argv[1] == 'start_with_streets':
                client = list(game.clients.values())[0]
                client.money = 100_000
                for i in range(40):
                    space = game.board.spaces[i]
                    if space.purchasable:
                        space.purchase(client)
        turn = 0
        running = True
        while running:
            print("[INFO] New turn is starting; Broadcasting gamestate")
            # await game.broadcast_gamestate()
            try:
                await game.do_1_turn_1_player()
            except ClientDisconnectedError as e:
                print("Client disconenctd, next player's turn")
                pass
            turn+=1
            game.check_finished()
            if game.finished:
                running = False
            await game.cleanup_disconnect()
            await asyncio.sleep(0)
    except Exception as e:
        print("[ERROR] an exception occured in the game loop, aborting...")
        shutdown_event.set()
        raise e
    print(f"[GAME] WE HAVE A WINNER: CONGRATZ TO {game.winner}")
    shutdown_event.set()
    return




async def sender(send_queue:asyncio.Queue,game:GameLogic_async):
    print("[INFO] Sender func active")
    while True:
        await asyncio.sleep(0)
        if shutdown_event.is_set():
            break  # Stop de lus als het shutdown-event is ingesteld
        try:
            message:dict = await send_queue.get()
            if isinstance(message, Message):
                message = message.msg
        except Exception:
            print("couldnt take from send_queue")
            continue
        try:
            target_uuid:Optional[str] = message.get("uuid", None)
            if target_uuid is None:
                raise Exception("I messed up while making a message")
            # print(f'[MESSAGE] to {game.clients[target_uuid].name} : content: {message}')
            print(f'[MESSAGE] to {game.clients[target_uuid].name}')
            target_client_ws = game.clients[target_uuid].ws
            await target_client_ws.send(json.dumps(message))
            send_queue.task_done()
        # except wsException.WebSocketException as e:
        #     print(f"Sender function ecountered errer {e} while trying to send {message} to {message.client}")
        #     shutdown_event.set()
        #     break
        except Exception as e:
            print(f"Error in server::sender: {e}")
            # this might be a little dangerous, but i think i should just mark the message as done and move on to the next
            send_queue.task_done()
            continue

def validate_incoming_msg(message, websocket:websockets.ServerProtocol, game:GameLogic_async, actual_uuid:str)->Optional[Tuple[dict, Connection]]:
    payload = json.loads(message)
    if not type(payload) == dict:
        print('received message is not of type dictionairy')
        return None, None
    typpe = payload.get('type', None)
    if typpe is None:
        print('message did not contain a type')
        return None, None
    if not typpe in VALID_MSG_TYPES:
        print("Invalid message type", typpe)
        return None, None
    client_uuid:Optional[str] = payload.get('uuid', None)
    if client_uuid is None:
        print("No uuid provided in message")
        return None, None
    if not client_uuid == actual_uuid:
        print("UUID not recognized")
        return None, None
    if game.clients[client_uuid].ws != websocket:
        print("the uuid of another client was provided?!?!?! SOMEONE IS MESSING WITH THE SYSTEM")
        raise RuntimeError()
    return payload, client_uuid
    

    # raise NotImplementedError("This needs to be redone")


async def handle_message(message:dict, client_uuid:str, send_queue:asyncio.Queue, game:GameLogic_async)->bool:
    # This function assumes input is valid
    client:Connection = game.clients[client_uuid]
    print(f"[DEBUG] handling incoming message from {client}")
    match message['type']:  # Where do we validate that the message type is the type of action taht the game is waiting on?
        case 'action reply':      #message contains at least: 'type': 'action', 'action type': any['before throw menu'], 'action': this depends on what the value of 'action type' is
            if not game.waiting_on_client == client:
                print("[WARNING] incorrect client")
                return False
            if not game.waiting_for_actionType == message['action type']:
                print(f"[WARNINIG] incorrect action type; I was waiting for {game.waiting_for_actionType}")
            try:
                reply = PlayerActionReply(message)
            except ValueError:
                # The messge was defective
                print("[WARNING] the message was defective")
                return False


            match reply.action_type_reply:
                # add special cases later
                case _:
                    print(f"[INFO] action type is: {reply.action_type_reply}")
                    player_action = {'choice': reply.choice,
                                     'action type': reply.action_type_reply}
                    client.most_recent_action = player_action
                    client.input_event.set()
            return True

        case 'disconnect':
            print(f"[DEBUG] handling incoming message from {client} with type disconnect")
            # await game.disconnect_client(client.uuid) # TODO lets just litterally not do this hahaaha
            try:
                game.mark_client_as_disconnected(client_uuid)
            except KeyError:
                pass
            msg = {'type': 'disconnect information',
                   'disconnected client': client.serialise()}
            await game.broadcast(msg)
            return True
        case 'request gamestate':
            print(f"[DEBUG] handling incoming message from {client} with type request gamestate")
            gamestate:dict = game.serialise()
            # gamestate.update({'type': 'reply gamestate'})
            content = {'type':'gamestate reply',
                       'content': gamestate}
            mesag = Message(client, content)
            # print(f"[DEBUG] sending a message:: {mesag}")
            await send_queue.put(mesag.msg)
            return True
        case 'i am alive':
            print(f"[DEBUG] handling incoming message from {client} with type i am alive")
            return True
            
        case 'connect spectator':
            print(f"[DEBUG] handling incoming message from {client} with type connect spectator")
            # make sure that the game is waiting for players.
            # TODO add functionality for others to watch the game
            return False
        case _:
            print(f"[DEBUG] handling incoming message from {client} with type <UNKNOWN>")
            raise NotImplementedError("This message type is not implemented")



async def receiver(websocket:websockets.ServerProtocol, send_queue:asyncio.Queue, game:GameLogic_async, name:str, actual_uuid:str):
    #NOTE one instance of this fucntion is spawned for each client
    # Asynchronously receives messages from a websocket connection and processes them.
    # Continuously listens for incoming messages on the provided websocket
    print(f"[INFO] Receiver func active for player {name}")
    while not shutdown_event.is_set():
        try:
            message = await websocket.recv()
            print(f"[INFO] Received a message from {name}, validating")
            valid_message, client_uuid = validate_incoming_msg(message, websocket, game,actual_uuid)
            print(f"[INFO] message from {name} is valid, handling...")
            succes:bool = await handle_message(valid_message, client_uuid, send_queue, game)
            if not succes: print("[WARNING] Handling message was unsuccesfull")
            if succes: print("[INFO] message handled succesfully")
        except wsException.ConnectionClosed:
            print(f"[ERROR] Receiver: Connection closed. Player {name} disconnected")
            # await game.disconnect_client(client_uuid)
            try:
                game.mark_client_as_disconnected(client_uuid)
            except KeyError:
                pass
            break
        except Exception as e:
            print(f"[ERROR] Receiver error: {e} In receiver function, aborting server")

            raise e
    print(f"[INFO] func:receiver is ending for client {name}: {actual_uuid}")

async def network_manager(websocket:websockets.ServerProtocol,send_queue:asyncio.Queue, game:GameLogic_async):
    # NOTE NOTE NOTE IMPORTANT: websocket is SPECIFIC FOR EACH CONNECTION # THis function is run once for each connection
    print(f"[INFO] New client connected from {websocket.remote_address}")
    # add client
    if game.gameReadyToStart.is_set():
        # we dont allow anyone to join anymore since the game has started
        return
    # make new player join the game
    client_input_event = asyncio.Event()
    # wait for message with name
    print("[INFO] a connection to the server has been made, waiting for name")
    name_received = False
    while not name_received:
        msg = await websocket.recv()    # I am not sure this is a real function? but sure I guess
        print("[INFO] received a message from a newly connecting client that may contain a name")
        payload = json.loads(msg)
        name = payload.get('name',None)
        if name is None: 
            print("[WARNING] received weird message")
            continue
        
        if not isinstance(name, str):
            continue
        if len(name) < 2:  continue
        if len(name) > 30: continue
        name_received = True

    print(f'[INFO] received name {name}')
    client_uuid = str(Uuid.uuid4())
    print(f"[INFO] Sending uuid {client_uuid} to new client {name}")
    await websocket.send(json.dumps({"type": "connect acknowledged", "uuid": client_uuid}))
    client = Connection(name, websocket, client_uuid, client_input_event)
    print(f"[DEBUG] Adding client {client} to the game. ")
    await game.add_client(client)
    print(f"[DEBUG] All current players are: {game.clients}")
    # go to steady state communication
    read_task = asyncio.create_task(receiver(websocket, send_queue, game, name, client_uuid))
    
    await asyncio.gather(read_task)
    # when I receive a message from a player, that is an action to do something, i will update the players "latest action" variable, and set a asyncio.Event
    print('[INFO] newtowrk manager is closing')

async def main():
    send_queue = asyncio.Queue()

    game = GameLogic_async(send_queue)  # Your Game class with players, board, etc.
    game_task = asyncio.create_task(game_loop(game, send_queue))  # Start de game loop
    # server_task = serve(network_manager,"IPV4 address", 8000)  # WebSocket server   # send_queue should be an argument but I dont know the syntax
    server_task = serve(lambda ws: network_manager(ws, send_queue, game), "0.0.0.0", 8000) # this lambda shit is some serious garmet shit from chatgpt
    send_task = asyncio.create_task(sender(send_queue, game))

    print("[INFO] Server gestart op ws://0.0.0.0:8000")
    await asyncio.gather(game_task, server_task, send_task)  # Voer beide taken parallel uit



if __name__ == "__main__":
    asyncio.run(main())
