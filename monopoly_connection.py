from monopoly_player import Player
import websockets
import asyncio
from typing import Optional

class Connection(Player):
    def __init__(self, naam:str, ws:websockets.ServerProtocol, uuid:str, input_event:asyncio.Event):
        super().__init__(naam)
        self.ws = ws # genuinely no idea what type this is
        self.uuid:str = uuid
        self.most_recent_action:Optional[dict] = None
        self.input_event = input_event
        self.input_event.clear()

    def __repr__(self):
        return f'{self.name}; uuid {self.uuid}'
    
    async def wait_for_client_input(self)->dict:
        print("THIS NEEDS TO BE UPDATED")
        await self.input_event.wait()
        self.input_event.clear()
        print(f"[INFO] received player {self.name} action {self.most_recent_action})this is the client.wait fro clint input func")
        return self.most_recent_action