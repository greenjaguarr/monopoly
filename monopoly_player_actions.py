# THIS NEEDS TO BE COMPLETELY REFACTORED ; it is now 17-7-2025 12:53; this is the minimum viable product
from typing import List, TYPE_CHECKING, Optional
from monopoly_message import Message
from monopoly_connection import ClientDisconnectedError, Connection
# from monopoly_gamelogic_async import GameLogic_async
# if TYPE_CHECKING:
#     from monopoly_gamelogic_async import GameLogic_async



class PlayerActionBase:
    # Central registry for action types and their valid responses
    valid_actions = {}
    valid_action_replys = {}

    def __init__(self, name, valid_responses:Optional[List[str]] = None, validate_response:Optional[callable] = None):
        self.__add_action('before throw menu', ['throw', 'buy/sell house', 'mortgage', 'request trade'])
        self.__add_action('want to buy property', ['yes', 'no'])
        self.__add_action("buy sell houses city menu",  ['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam', 'return'])
        self.__add_action('buy sell houses amount 2', ['increase 1','increase 2', 'decrease 1', 'decrease 2', 'back','finish'])
        self.__add_action('buy sell houses amount 3', ['increase 1','increase 2','increase 3', 'decrease 1', 'decrease 2', 'decrease 3', 'back', 'finish'])
        self.__add_action('offer trade give money amount', ['increase 1', 'decrease 1','increase 10', 'decrease 10','increase 100', 'decrease 100',])
        self.__add_action('offer trade get money amount', ['increase 1', 'decrease 1','increase 10', 'decrease 10','increase 100', 'decrease 100',])


        # self.__add_action('confirm trade proposal', ['confirm', 'cancel', 'edit'])
        # self.__add_action('respond to trade offer', ['accept', 'reject', 'counter'])
        self.__add_action('offer trade build', # This is for offer_trade_what_inner
                          ['add give money', 'add get money', 'add give property', 'add get property', 'remove give property', 'remove get property','reset','confirm', 'cancel'])

        if valid_responses:
            self.__add_action(name, valid_responses)
            # self.__add_action('offer trade give money amount', ['__OPEN__'])
            # self.__add_action('select request assets', valid_responses)  # dynamically set
            # self.__add_action('select trade partner', valid_responses)  # dynamically set
            # self.__add_action('select offer assets', valid_responses)
            # self.__add_action('counter offer menu', valid_responses)  # dynamically set
            # self.__add_action('offer trade menu', valid_responses)
        # print('[DEBUG]', self.valid_actions)
        # print('[DEBUG]', self.valid_action_replys)

        if validate_response:
            self.__add_action(name, [])

    def __add_action(self, action_type:str, valid_responses:List[str])->None:
        self.valid_actions.update({action_type: valid_responses})
        self.valid_action_replys.update({f'{action_type} reply': valid_responses})

    @classmethod
    def is_valid_action_type(cls, action_type: str) -> bool:
        # print("[DEBUG] euhm", action_type,  cls.valid_actions)
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

class PlayerActionRequest(PlayerActionBase):  # maybe instead of valid-responses, the user should supply a validate_reply:Callable function
    def __init__(
        self,
        name: str,
        valid_responses: Optional[List[str]] = None,
        extra_display_info: Optional[dict] = None,
        validate_response: Optional[callable] = None,
        target_player: Optional[Connection] = None
    ):
        super().__init__(name, validate_response = validate_response, valid_responses = valid_responses)
        self.action_type = name
        self.reply_type = f"{name} reply"
        self.choice = None
        self.extra_display_info = extra_display_info
        self.validate_request = validate_response
 
        self.target = target_player

        # Try to get valid_responses from lookup if not provided
        if valid_responses is not None:
            self.valid_responses = valid_responses
        else:
            self.valid_responses = self.get_valid_responses(name)

        # Check if at least one of the three cases is met
        if (
            (self.valid_responses and isinstance(self.valid_responses, list) and len(self.valid_responses) > 0)
            or callable(validate_response)
        ):
            pass
        else:
            raise ValueError(
                "PlayerActionRequest requires at least one of: "
                "a non-empty valid_responses list, a validate_response function, "
                "or a valid_responses lookup for the given action type."
            )

        if not self.is_valid_action_type(name):
            print("[ERROR] invalid action type, the valid action types are ", self.valid_actions)
            raise ValueError(f"Invalid action type: {name}")

    def __repr__(self) -> str:
        return f"PlayerActionRequest(name={self.action_type!r}, valid_responses={self.valid_responses!r})"

    def serialise_request(self) -> dict:
        data = {
            'type': 'action request',
            'action type': self.action_type,
            'extra display info': self.extra_display_info
        }
        if self.valid_responses is not None:
            data['valid responses'] = self.valid_responses
        if callable(self.validate_request):
            data['validation'] = 'callable'
        return data

    def validate_request(self, action_request: dict) -> bool:
        if not isinstance(action_request, dict):
            return False
        if action_request.get('action_type') != self.action_type:
            return False
        valid_responses = action_request.get('valid_responses')
        if not isinstance(valid_responses, list):
            return False
        return all(isinstance(item, str) for item in valid_responses)

    async def take_player_input(self, game, extra_display_info: Optional[dict] = None) -> str:
        if not self.target:
            target_client = game.currently_playing_client
        else:
            target_client = self.target
        game.waiting_on_client = target_client
        game.waiting_for_actionType = self.reply_type
        while True:
            print('[INFO] sending message to client with request to reply, action:', self)
            content = self.serialise_request()
            if extra_display_info:
                print(f"[DEBUG] extra display info: {extra_display_info}")
                content.update({'extra display info': extra_display_info})

            msg = Message(target_client, content)
            await game.send_queue.put(msg.msg)
            try:
                player_action = await target_client.wait_for_client_input()
            except ClientDisconnectedError as e:
                print("This player disconnected so we stop waiting for their turn")
                raise e
            try:
                print("[DEBUG] received reply to player action request from player ", player_action)
                reply = PlayerActionReply(player_action)
                print("[DEBUG] received reply to player action request from player ", target_client)
            except ValueError:
                raise RuntimeError("[ERROR ]Could not instantiate PlayerActionReply")
            if reply.action_type_reply != self.reply_type:
                print("[WARNING] received incorrect action type reply, rejecting...")
                print(reply.action_type_reply, self.reply_type)
                continue
            break
        ack_msg = Message(target_client, {'type': 'acknowledge correct action reply'})
        await game.send_queue.put(ack_msg.msg)
        game.waiting_on_client = None
        game.waiting_for_actionType = None
        return reply.choice

class PlayerActionReply(PlayerActionBase):
    def __init__(self, action_reply:dict ):
        print(f'[DEBUG] attempting to instantiate PlayerActionReply using dictionairy {action_reply}')
        # super().__init__()
        self.action_type_reply: str = action_reply.get('action type',None)
        self.choice:str = action_reply.get('choice', None)
        if not self.is_valid_action_type_reply(self.action_type_reply):
            raise ValueError(f"Invalid action type {self.action_type_reply}")
        self.valid_responses = self.get_valid_responses_reply(self.action_type_reply)
        print(f"[DEBUG] valid responses are {self.valid_responses}")
        # self.__validate_reply()

    # def __validate_reply(self) -> bool: # This one is for serverside?
    #     if not isinstance(self.choice, str):
    #         print(f'choice {self.choice} is not a string')
    #     if self.choice not in self.valid_responses:
    #         raise ValueError("action_reply['choice'] is not a valid response")
    #     return True

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