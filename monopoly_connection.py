from monopoly_player import Player
import websockets
import asyncio
from typing import Optional

class ClientDisconnectedError(Exception):
    """Raised when a client disconnects from the server."""
    pass


class Connection(Player):
    def __init__(self, naam:str, ws:websockets.ServerProtocol, uuid:str, input_event:asyncio.Event):
        super().__init__(naam)
        self.ws = ws # genuinely no idea what type this is
        self.uuid:str = uuid
        self.most_recent_action:Optional[dict] = None
        self.input_event = input_event
        self.input_event.clear()
        self.soft_disconnected = False

    def __repr__(self):
        return f'{self.name}; uuid {self.uuid}'
    
    async def wait_for_client_input(self) -> dict:
        while True:
            try:
                print("[DEBUG] waiting for input from player", self)
                await asyncio.wait_for(self.input_event.wait(), timeout=5)
            except asyncio.TimeoutError:
                if self.soft_disconnected:
                    raise ClientDisconnectedError(f"Player {self.name} soft disconnected.")
                continue
            self.input_event.clear()
            print(f"[INFO] received player {self.name} action {self.most_recent_action} (client.wait_for_client_input)")
            return self.most_recent_action