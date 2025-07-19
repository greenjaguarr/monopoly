from monopoly_connection import Connection

class Message():    # TODO implement that this instance cleans itself up after sending? it may just go out of scope though after the asyncio.Queue.taks_complet
    def __init__(self, client:Connection, msg:dict):
        self.client = client
        self.msg = msg
        self.prepare_for_send()
    def prepare_for_send(self):
        self.msg.update({'uuid':self.client.uuid})
        assert self.msg.get('type', None) is not None # I should be strict for following my own conventions serverside
        # await self.client.ws.send(json.dumps(self.msg)) # THIS FUNCTION ISNT ALLOWED TO SEND, it must go through the network handler
    def __repr__(self):
        return f'[MESSAGE] to {self.client.name}: content: {self.msg}'