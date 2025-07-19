# THIS NEEDS TO BE COMPLETELY REFACTORED ; it is now 17-7-2025 12:53; this is the minimum viable product
from typing import Any

class actionTypes():
    def __init__(self):
        self.before_throw_menu = "before throw menu"
        self.before_throw_menu_valid = ['throw', 'buy/sell house', 'mortgage', 'request trade']
        self.before_throw_menu_reply = 'before throw menu reply'
        # self.before_throw_continue = "before throw continue"
        self.wannabuy_property = 'want to buy property?'
        self.wannabuy_property_valid = ['yes', 'no'] # maybe add auction later? that is a lot of networking, and it is not important for now
        self.wannabuy_property_reply = 'wannabuy property reply'
        self.build_houses = 'build houses?'
        self.build_houses_valid = ['yes', 'no']

    def validate_action(self, action_type:str, action:Any)->bool:
        match action_type:
            case self.before_throw_menu:
                choice = action.get('choice', None)
                if choice is None: return False
                if not choice in self.before_throw_menu_valid: return False
                return True
            case self.before_throw_menu_reply:
                if action is None: return False
                if not action in self.before_throw_menu_valid: return False
                return True
            case self.build_houses:
                raise NotImplementedError("validating message actiong build hjouses is nt implemented")
            case self.wannabuy_property:
                raise NotImplementedError("validating message action buy property is not implemented")
            case self.wannabuy_property_reply:
                if not action in self.wannabuy_property_valid: return False
                return True
                # raise NotImplementedError("validating message action buy property is not implemented")
            case _:
                print(f"[WARNING] couldnt verify unknown action type {action_type}")
                return False

class PlayerActionRequest:
    def __init__(self, name: str, valid_responses: list[str]):
        self.name = name
        self.valid_responses = valid_responses
        self.reply = name + ' reply'

    def validate_response(self, response: str) -> bool:
        return response in self.valid_responses

    def __repr__(self)->str:
        return f"PlayerActionRequest(name={self.name!r}, valid_responses={self.valid_responses!r})"
    
    def serialise(self)->dict:
        # the output of this function should be a valid input for json.dumps()
        pass

    def validate_cmp_myself(self, test:dict)->bool:
        pass

    def validate_reply(self)->bool:
        pass


global actionType
actionType = actionTypes()

if __name__ == "__main__":
    pass