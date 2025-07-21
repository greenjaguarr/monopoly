import asyncio
import json
from typing import Optional, List
from monopoly_frontend import Player_representation, Board_representation, Button
from monopoly_player_actions import PlayerActionReply, PlayerActionRequest
import random
from monopoly_connection import Connection

class Bot:
    def __init__(self):
        print("[INFO] bot instantialted")
        self.completely_filled_cities:List[str] = []
        pass
    
    
    def choose_action(self, request: PlayerActionRequest, state:dict, buttons:List[Button])->int:
        currently_playing = state.get('currently playing', None)
        if currently_playing is None:
            return -1
        # currently_playing = the name of the current player
        players:List[Player_representation] = state.get('players', {})
        me = next((p for p in players if p.name == currently_playing), None)
        if me is None:
            return -1
        print(f'[DEBUG] the bot is thinking about request: {request.action_type}')
        match request.action_type:
            case 'before throw menu':
                if len(me.completed_sets) == 0: chance = 0.1
                else: chance = 0.5
                if random.random() < chance:
                    print("[INFO] bot decided to buy / sell houses")
                    return 1
                else:
                    print("[INFO] bot decided to throw dice")
                    return 0
            case 'want to buy property':
                if me.money > 300:
                    print("[INFO] bot decided to try to buy property")
                    return 0
                else:
                    print("[INFO] the bot decided not to buy the property")
                    return 1
            case 'buy sell houses city menu':
                if me.money < 200:
                    print('[INFO] the bot decided not to buy or sell houses cuz broke')
                    return request.valid_responses.index('return')
                if len(me.completed_sets) == 0:
                    print('[INFO] the bot decided not to buy or sell houses cuz no sets')
                    return request.valid_responses.index('return')
                for city in me.completed_sets:
                    if random.random() > 0.5:
                        continue
                    elif city in self.completely_filled_cities:
                        print("[DEBUG] This city is full, so we dotn build on it")
                        pass
                    else:
                        return request.valid_responses.index(city)
                    # correct_button = {i:b for i,b in enumerate(buttons) if city in b.text}
                    # assert len(correct_button) == 1
                    # i = correct_button.keys()
                    # i = i[0]
                    # return i
                print("[INFO] the bot decided to not buy houses")
                return request.valid_responses.index('return')



            case 'buy sell houses amount 2':
                additional_info:dict = request.extra_display_info
                city = additional_info['city']
                house_cost = additional_info['house cost']
                city_distribution = additional_info['city_distribution']
                city_desired = additional_info['city_desired']
                total_house_build_desire  = sum([ desired - current for current, desired in zip(city_distribution, city_desired)])
                if me.money - house_cost < 200:
                    print("[INFO] the bot didnt buy to save money")
                if me.money - house_cost * (total_house_build_desire + 1) < 200:
                    print("[INFO] the bot didnt buy  andy adiitional houses to save money")
                    return request.valid_responses.index('finish')
                if not city_desired[0] == 5:
                    print("[INFO] the bot wanted to buy houses")
                    return request.valid_responses.index('increase 1')
                if not city_desired[1] == 5:
                    print("[INFO] the bot wanted to buy houses")
                    return request.valid_responses.index('increase 2')
                # everything is fully built
                print("[INFO] everything here is fully build")
                self.completely_filled_cities.append(city)
                return request.valid_responses.index('finish')
                
            case 'buy sell houses amount 3':
                additional_info:dict = request.extra_display_info
                city = additional_info['city']
                house_cost = additional_info['house cost']
                city_distribution = additional_info['city_distribution']
                city_desired = additional_info['city_desired']
                total_house_build_desire  = sum([ desired - current for current, desired in zip(city_distribution, city_desired)])
                if me.money - house_cost < 200:
                    return request.valid_responses.index('finish')
                if me.money - house_cost * (total_house_build_desire + 1) < 200:
                    print("[INFO] the bot didnt buy  andy adiitional houses to save money")
                    return request.valid_responses.index('finish')
                if not city_desired[0] == 5:
                    print("[INFO] the bot wanted to buy houses")
                    return request.valid_responses.index('increase 1')
                if not city_desired[1] == 5:
                    print("[INFO] the bot wanted to buy houses")
                    return request.valid_responses.index('increase 2')
                if not city_desired[2] == 5:
                    print("[INFO] the bot wanted to buy houses")
                    return request.valid_responses.index('increase 3')
                # everything is fully built
                print("[INFO] everything here is fully build")
                self.completely_filled_cities.append(city)
                return request.valid_responses.index('finish')
            case _:
                print("[WARNING] bot encountered unknown action request", request.action_type)
        # Logic to choose an action based on the current state
        # This could involve checking the player's position, money, properties, etc.
        # return action_index