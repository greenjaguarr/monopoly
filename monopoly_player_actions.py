# THIS NEEDS TO BE COMPLETELY REFACTORED ; it is now 17-7-2025 12:53; this is the minimum viable product
from typing import List, TYPE_CHECKING, Optional
from monopoly_message import Message
from monopoly_connection import ClientDisconnectedError
# from monopoly_gamelogic_async import GameLogic_async
# if TYPE_CHECKING:
#     from monopoly_gamelogic_async import GameLogic_async



class PlayerActionBase:
    # Central registry for action types and their valid responses
    valid_actions = {}
    valid_action_replys = {}

    def __init__(self):
        self.__add_action('before throw menu', ['throw', 'buy/sell house', 'mortgage', 'request trade'])
        self.__add_action('want to buy property', ['yes', 'no'])
        self.__add_action("buy sell houses city menu",  ['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam', 'return'])
        self.__add_action('buy sell houses amount 2', ['increase 1','increase 2', 'decrease 1', 'decrease 2', 'back','finish'])
        self.__add_action('buy sell houses amount 3', ['increase 1','increase 2','increase 3', 'decrease 1', 'decrease 2', 'decrease 3', 'back', 'finish'])
        # print('[DEBUG]', self.valid_actions)
        # print('[DEBUG]', self.valid_action_replys)

    def __add_action(self, action_type:str, valid_responses:List[str])->None:
        self.valid_actions.update({action_type: valid_responses})
        self.valid_action_replys.update({f'{action_type} reply': valid_responses})

    @classmethod
    def is_valid_action_type(cls, action_type: str) -> bool:
        return action_type in cls.valid_actions
    
    @classmethod
    def is_valid_action_type_reply(cls, action_type_reply: str) -> bool:
        return action_type_reply in cls.valid_action_replys

    @classmethod
    def get_valid_responses(cls, action_type: str) -> list[str]:
        return cls.valid_actions.get(action_type, [])
    @classmethod
    def get_valid_responses_reply(cls, action_type: str) -> list[str]:
        return cls.valid_action_replys.get(action_type, [])

class PlayerActionRequest(PlayerActionBase):
    def __init__(self, name: str):
        super().__init__()
        if not self.is_valid_action_type(name):
            raise ValueError(f"Invalid action type: {name}")
        self.action_type = name
        self.valid_responses = self.get_valid_responses(name)
        self.reply_type = f"{name} reply"
        self.choice = None

    def __repr__(self) -> str:
        return f"PlayerActionRequest(name={self.action_type!r}, valid_responses={self.valid_responses!r})"

    def serialise_request(self) -> dict:
        return {
            'type': 'action request',
            'action type': self.action_type,
            'valid responses': self.valid_responses
        }

    def validate_request(self, action_request: dict) -> bool:
        if not isinstance(action_request, dict):
            return False
        if action_request.get('action_type') != self.action_type:
            return False
        valid_responses = action_request.get('valid_responses')
        if not isinstance(valid_responses, list):
            return False
        return all(isinstance(item, str) for item in valid_responses)

    # async def take_player_input(self, game: GameLogic_async) -> str:
    async def take_player_input(self, game, extra_display_info:Optional[dict] = None) -> str:
        # if extra_display_info:
        #     raise NotImplementedError("appendign extra dta is not yet supported")
        game.waiting_on_client = game.currently_playing_client
        game.waiting_for_actionType = self.reply_type
        while True:
            content = self.serialise_request()
            if extra_display_info:
                print(f"[DEBUG] extra display info: {extra_display_info}")
                content.update({'extra display info': extra_display_info})

            msg = Message(game.waiting_on_client, content)
            await game.send_queue.put(msg.msg)
            try:
                player_action = await game.currently_playing_client.wait_for_client_input()
            except ClientDisconnectedError as e:
                print("This player disconnected so we stop waiting for their turn")
                raise e
            try:
                print("[DEBUG] received reply to player action request from player ", player_action)
                reply = PlayerActionReply(player_action)
                print("[DEBUG] received reply to player action request from player ", game.currently_playing_client.name)
            except ValueError:
                raise RuntimeError("[ERROR ]Could not instantiate PlayerActionReply")
            if reply.action_type_reply != self.reply_type:
                print("[WARNING] received incorrect action type reply, rejecting...")
                print(reply.action_type_reply, self.reply_type)
                continue
            break
        ack_msg = Message(game.currently_playing_client, {'type': 'acknowledge correct action reply'})
        await game.send_queue.put(ack_msg.msg)
        game.waiting_on_client = None
        game.waiting_for_actionType = None
        return reply.choice

class PlayerActionReply(PlayerActionBase):
    def __init__(self, action_reply:dict ):
        print(f'[DEBUG] attempting to instantiate PlayerActionReply using dictionairy {action_reply}')
        super().__init__()
        self.action_type_reply: str = action_reply.get('action type',None)
        self.choice:str = action_reply.get('choice', None)
        if not self.is_valid_action_type_reply(self.action_type_reply):
            raise ValueError(f"Invalid action type {self.action_type_reply}")
        self.valid_responses = self.get_valid_responses_reply(self.action_type_reply)
        print(f"[DEBUG] valid responses are {self.valid_responses}")
        self.__validate_reply()

    def __validate_reply(self) -> bool:
        if not isinstance(self.choice, str):
            print(f'choice {self.choice} is not a string')
        if self.choice not in self.valid_responses:
            raise ValueError("action_reply['choice'] is not a valid response")
        return True

    def serialise_reply(self) -> dict:
        return {
            'action type': self.action_type_reply,
            'choice': self.choice,
            'action': self.choice,
            'type': 'action reply'
        }
    def __repr__(self):
        return f"{self.action_type_reply}: {self.choice}"






if __name__ == "__main__":
    before_throw_menu = PlayerActionRequest("before throw menu")
    print(before_throw_menu)
    want_to_buy_property = PlayerActionRequest("want to buy property")
    print(want_to_buy_property)

    pass