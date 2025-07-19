# client.py
import pygame
import asyncio
import websockets
import json
from typing import Optional, List
from monopoly_board_asyncfriendly import BoardAsync
import monopoly_frontend as frontend
from monopoly_gamelogic_async import GameLogic_async
from monopoly_player_actions import actionType


# globals
STATE_LOCK = asyncio.Lock()
shutdown_event = asyncio.Event()
start_pygame_event = asyncio.Event()
the_server_is_waiting_for_input_from_me = asyncio.Event()


async def draw_based_on_state(screen, font, state):
    # waht is the structure expected of state?
    # state is a dict
    # state has a key 'board'. The value is a list of dicts. These dicts are representations of spaces
    # state has a key 'players'
    async with STATE_LOCK:
        BOARD: List[dict] = state.get("board", None)
        players = state.get("players", None)

        finished = state.get('finished', None)
        currently_playing = state.get('currently playing', None)
        throw = state.get('throw', None)
    if not (BOARD is None):
        frontend.draw_board(screen, BOARD, font)
        if players:
            frontend.draw_players(screen, players, font, currently_playing, BOARD)
        if throw and currently_playing:
            frontend.draw_throw(screen, throw, font, currently_playing)


async def pygame_loop(websocket, send_queue: asyncio.Queue):
    print("[INFO] pygame is waiting to start")
    await start_pygame_event.wait()
    # state is a shared memory block, it gets updated a lot
    global state, name, action_type_requested
    screen, clock, font, buttons = frontend.initialise()

    if name:
        pygame.display.set_caption(f'Monopoly with client {name}')
    # get initial gamestate
    msg = {"type": "request gamestate"}
    await send_queue.put(msg)

    frame:int = 0
    running = True
    print("Starting event loop")
    while running:
        frame+=1
        if shutdown_event.is_set():
            running = False
            print('[DEBUG] pygmae loop is shutting down since it detected a shutdown event')
        # if frame%10 == 0:
        # print("Making new frame")
        await asyncio.sleep(0)
        clock.tick(frontend.FPS * 2)
        await asyncio.sleep(0)
        clock.tick(frontend.FPS * 2)
        # game logic ( i mean the input side()
        # if frame%10 == 0:
        # print("[DEBUG] checking for events")
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("[IFNO] pygame.QUIT event found")
                running = False
                await send_queue.put({'type': 'disconnect'})
                await asyncio.sleep(0.1)
                shutdown_event.set()
            if buttons:
                # button_clicked = None
                # if frame%10 == 0:
                # print("[DEBUG] checking for pressed buttons")
                for i, button in enumerate(buttons):
                    if button.is_clicked(event):
                        # if frame%10 == 0:
                        print(f"[DEBUG] A button is clicked: {button}")
                        # button_clicked = button
                        match action_type_requested:
                            case actionType.before_throw_menu:
                                await send_queue.put({'type': 'action',
                                              'action type': actionType.before_throw_menu_reply,
                                              'action': actionType.before_throw_menu_valid[i]})
                            case actionType.wannabuy_property:
                                await send_queue.put({'type': 'action',
                                                      'action': button.text,
                                                      'action type': actionType.wannabuy_property_reply})
                        break
        # draw
        await asyncio.sleep(0)
        frontend.draw_board_background(screen)
        await draw_based_on_state(screen, font, state)
        if the_server_is_waiting_for_input_from_me.is_set():
            buttons = frontend.draw_action_request(action_type_requested,font, screen)
        else:
            buttons = None
        if buttons and frame%10 == 0:
            print("[DEBUG] received buttons; waiting for input")
        pygame.display.flip()
    # do generic pygame stuff
    # if a player does something, we might need to tell this to the server. to do this, we put a message in the send_queue
    # read the global variable "state", and draw the board based on this information
    pygame.quit()


async def read_messages(websocket):
    # read messages from the server. This message might be "gamestate"; then we need to modify the "state" variable
    # Another message from the server might be "disconnect", this means that we are getting kicked out
    EXPECTED_MESSAGES = [
        "gamestate reply",
        "gamestate update",
        "game is starting",
        "action request",
        "disconnect",
        'agnowledge correct action reply',
        'game control flow',
    ]
    global state
    while not shutdown_event.is_set():
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5)
        except asyncio.TimeoutError:
            continue  # Check shutdown_event again
        except websockets.ConnectionClosed:
            print("[INFO] WebSocket connection closed.")
            shutdown_event.set()
            break
        print("[DEBUG] received a message from the server")
        try:
            payload = json.loads(message)
            typpe = payload.get("type", None)
            print(
                f"[INFO] Receives message of type '{typpe}' from the server, message:: {payload}"
            )
            if not typpe in EXPECTED_MESSAGES:
                continue

            match typpe:
                case "gamestate reply" | "gamestate update":
                    print("[NEW GAMESTATE]", payload)
                    async with STATE_LOCK:
                        # reset
                        state.update({'board': None})
                        state.update({'players': None})
                        state.update({'throw': None})
                        state.update({'currently playing': None})
                        state.update({'finished': None})

                        # get new stuff
                        game_serialised = payload.get("content", None)
                        if game_serialised is None:
                            print("[ERROR] gamestate is incorrectly formatted")
                            continue
                        board = game_serialised.get('board', None)
                        players:dict = game_serialised.get('players', None)
                        most_recent_throw = game_serialised.get('throw',None)
                        currently_playing:str = game_serialised.get('currently playing', None) # name of the currently playing player
                        finished:bool = game_serialised.get('finished', None)

                        board_representation = frontend.Board_representation(board)
                        players_representation = [
                            frontend.Player_representation(
                                player.get('name', None),
                                player.get('position', None),
                                player.get('money', None),
                                player.get('jailtime', None),
                                player.get('has lost', None),
                                player.get('properties', None)
                            )
                            for player_uuid, player in players.items()
                        ]
                        state.update({'board': board_representation})
                        state.update({'players': players_representation})
                        state.update({'throw': most_recent_throw})
                        state.update({'currently playing': currently_playing})
                        state.update({'finished': finished})
                        print("[DEBUG] Summary of received gamestate:")
                        print("summary not implemented")
                case "game is starting":
                    print("[INFO] Game is starting!")
                case "action request":
                    global action_type_requested
                    action_type_requested = payload.get("action type")
                    print("[INFO] Action requested from server:", action_type_requested)
                    the_server_is_waiting_for_input_from_me.set()


                    # This is not yet implemented
                    raise NotImplementedError()
                case "disconnect":
                    print("[INFO] Disconnected by server.")
                    shutdown_event.set()
                    break
                case 'agnowledge correct action reply':
                    print("[INFO] got message type: 'agknowledge correct action reply'")
                    the_server_is_waiting_for_input_from_me.clear()
                case 'game control flow':
                    content = payload.get('content', None)
                    print(f'Received update about game control flow {content}')
                case _:
                    print(f"[WARNING] Unknown message type received: {typpe}")
                
        except Exception as e:
            print(f"[ERROR] Exception in read_messages: {e}")
            continue
    print("[INFO] func: read_messages is finished")


async def send_messages(websocket, send_queue: asyncio.Event, my_uuid: str):
    print("Sender func active")
    while True:
        await asyncio.sleep(0)
        if shutdown_event.is_set():
            break  # Stop de lus als het shutdown-event is ingesteld
        try:
            try:
                message: dict = await asyncio.wait_for(send_queue.get(), timeout=2)
            except asyncio.TimeoutError:
                continue  # Skip this iteration if no message is available within 5 seconds
            message.update({"uuid": my_uuid})

            # await websocket.send(json.dumps(message)) #THIS IS WRONG, we need to send it to message.client
            await websocket.send(json.dumps(message))
            send_queue.task_done()
        except Exception as e:
            print(
                f"Sender function ecountered errer {e} while trying to send {message} to the server"
            )
            shutdown_event.set()
            break
        except Exception as e:
            print(f"Error sending message: {e}")
            break
    print("[INFO] func:send_messages is finished")


async def handle_networking(websocket, send_queue: asyncio.Queue):
    # startup handshake
    global name
    handshake_complete = False
    while not handshake_complete:
        naam: str = input("Wat is jouw naam? Maximaal 10 characters ")[:20]
        if any(c in naam for c in ["'", '"', ",", ".", "\\", "/"]):
            print("Ongeldige karakters in naam.")
            exit()

        
        print("[INFO] sendinng message with name")
        await websocket.send(json.dumps({"name": naam}))
        await asyncio.sleep(1)
        # await websocket.send(json.dumps({"type": "connect agknowledged", "uuid": client_uuid}))
        print("[INFO] waiting for msg with my uuid")
        try:
            msg = await asyncio.wait_for(websocket.recv(), timeout=2)
        except asyncio.TimeoutError:
            # something went wrong, try again
            print("Something went wrong, try again \n")
            continue
        payload: dict = json.loads(msg)
        typpe = payload.get("type", None)
        if typpe is None:
            print("Something went wrong in the handshake.")
            print(payload)
            print("")
            continue
        my_uuid = payload.get("uuid", None)
        if my_uuid is None:
            print("Something went wrong in the handshake.")
            print(payload)
            print("")
            continue
        print(f"[INFO] received my uuid from the server, it is {my_uuid}")
        handshake_complete = True

    name = naam
    # go to steady state
    print("[INFO] going to steady state comms now")
    start_pygame_event.set()

    read_task = asyncio.create_task(read_messages(websocket))
    send_task = asyncio.create_task(send_messages(websocket, send_queue, my_uuid))
    await asyncio.gather(read_task, send_task)
    print("Network finished")


async def main():
    """
    Asynchronous main entry point for the Monopoly client.
    Initializes an asyncio queue for outgoing messages and establishes a WebSocket connection
    to the server at ws://localhost:8000. Launches two concurrent tasks: one for handling
    the Pygame event loop and another for managing network communication. Both tasks are
    run concurrently until completion.
    Returns:
        None
    """
    global state
    state = {}
    send_queue = asyncio.Queue()
    async with websockets.connect("ws://localhost:8000") as websocket:

        pygame_task = asyncio.create_task(pygame_loop(websocket, send_queue))
        network_task = asyncio.create_task(handle_networking(websocket, send_queue))

        # Run both tasks concurrently
        await asyncio.gather(pygame_task, network_task)


if __name__ == "__main__":
    asyncio.run(main())
