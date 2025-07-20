import pygame
from monopoly_gamelogic_async import Connection, GameLogic_async
from typing import List, Optional
from monopoly_board import Space, Street, Station, Utility, Tax, CardSpace, FreeParking, GoToJail, GO, Property, Board
# from monopoly_player_actions import actionType


BLACK = (0,0,0)
WHITE =(255,255,255)
RED = (255,0,0)
BLUE = (0,0,255)
GREEN=(0,255,0)
YELLOW=(255,255,0)
PURPLE=(255,0,255)
CYAN=(0,255,255)
LIGHTGREY = (200,200,200)
SCREENSIZE = 1000

SPACE_SIZE = SCREENSIZE//12
# assert SPACE_SIZE * 11 == SCREENSIZE

FPS = 10

class Player_representation:  #NOTE doing this representaion is smart and I will do so in the future, but i wont do it right now
    def __init__(self, name:str, position:int, money:int, jailtime:int, has_lost:bool, properties:List[int]):
        self.name = name
        self.position= position
        self.money = money
        self.jailtime = jailtime
        self.has_lost = has_lost
        self.properties = properties # This is just tje Property.position

class Board_representation:
    def __init__(self, spaces:dict):
        # print("Making board represenstation")
        # print(spaces)
        # spaces: dict[int, space_representation]
        # Sort the spaces by their integer keys (0-39) and store as a list
        # self.spaces = [spaces[i] for i in sorted(spaces.keys())]
        self.spaces = list(spaces.values())
        # print("Making board represenstation, self.spaces")
        # print(self.spaces)
        


def draw_board_background(screen: pygame.Surface):
    screen.fill((200, 240, 200))  # light grey background

    board_size = min(screen.get_width(), screen.get_height())
    board_rect = pygame.Rect(0, 0, board_size, board_size)
    pygame.draw.rect(screen, BLACK, board_rect, 4)

# def draw_based_on_gamestate(gamestate):
#     pass

def initialise():
    pygame.init()
    screen = pygame.display.set_mode((900, 900))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 14)
    return screen, clock, font, None

class Text_plate:
    def __init__(self, text_color, x, y, text:str, background_color, font):
        self.text_color = text_color
        self.x = x
        self.y = y
        self.text = text
        self.background_color = background_color
        self.font = font
    def draw(self, screen:pygame.Surface):
        rect = pygame.Rect(self.x, self.y, 150, 30)
        pygame.draw.rect(screen, self.background_color, rect)

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        screen.blit(text_surface, text_rect)


class Button:
    def __init__(self, x, y, width, height, text:str, font, color:tuple[int], hover_color, text_color):
        self.rect:pygame.Rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color

    def draw(self, screen)->None:
        # Check if the mouse is over the button
        mouse_pos = pygame.mouse.get_pos()
        if self.rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, self.hover_color, self.rect)
        else:
            pygame.draw.rect(screen, self.color, self.rect)

        # Draw the text
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, event)->bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False
    
    def __repr__(self):
        return f'{self.text}'
    

#chatgpt type shit


# def draw_board(screen:pygame.Surface, board:dict, font:pygame.font.Font):     #outdated
#     # Draw all spaces in their correct positions
#     for key_position,v_space_repr in board.items():
#         rect = __calculate_space_rect(key_position)
#         __draw_space(screen, v_space_repr, rect, font)
def draw_board(screen:pygame.Surface, board_representation:Board_representation, font:pygame.font.Font):
    # Draw all spaces in their correct positions
    for space_repr in board_representation.spaces:
        rect = __calculate_space_rect(space_repr['position'])
        __draw_space(screen, space_repr, rect, font)

def __draw_space(screen:pygame.Surface, space_representation:dict, rect:pygame.rect.Rect, font:pygame.font.Font):
    # Choose color and details based on space type
    # TODO rework this functio to use space['space type'] instead of isinstance
    space_type = space_representation.get('space type', None)
    if space_type is None: return
    match space_type:
        case 'street':
            color = (255, 255, 200)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            # Draw name and house count
            name_surf = font.render(space_representation.get('name'), True, (0,0,0))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
            house_surf = font.render(f"Houses: {space_representation.get('house count')}", True, (0,128,0))
            screen.blit(house_surf, (rect.x+5, rect.y+25))
        case 'station':
            color = (200, 200, 255)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            name_surf = font.render(space_representation.get('name'), True, (0,0,0))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # elif isinstance(space, Utility):
        case 'utility':
            color = (200, 255, 255)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            name_surf = font.render(space_representation.get('name'), True, (0,0,0))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # elif isinstance(space, Tax):
        case 'tax':
            color = (255, 200, 200)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            name_surf = font.render(space_representation.get('name'), True, (128,0,0))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # elif isinstance(space, CardSpace):
        case "chance card" | "algemeen fonds card":
            color = (255, 255, 255)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            name_surf = font.render(space_representation.get('name'), True, (0,0,128))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # elif isinstance(space, FreeParking):
        case 'free parking':
            color = (255, 255, 255)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            if space_representation.get('position') == 20:
                name_surf = font.render("Free Parking", True, (128,128,128))
            elif space_representation.get('position') == 10:
                name_surf = font.render("Pliesiepossie", True, (128,128,128))
            else: raise RuntimeError("")
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # elif isinstance(space, GoToJail):
        case 'go to jail':
            color = (255, 128, 128)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            name_surf = font.render("Go To Jail", True, (128,0,0))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # elif isinstance(space, GO):
        case 'go':
            color = (255, 255, 128)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (0,0,0), rect, 2)
            name_surf = font.render("GO", True, (0,128,0))
            screen.blit(name_surf, (rect.x+5, rect.y+5))
    # else:
        case _:
            print(f"[ERROR] could not match space_type {space_type}")
            raise RuntimeError("Unreachable")

def __calculate_space_rect(position:int)->pygame.rect.Rect:
    # Return a pygame.Rect for the given board position
    # You need to implement this based on your board layout
    i = int(position)
    if 0<=i and i<11:
        return pygame.rect.Rect(0, 10* SPACE_SIZE -i*SPACE_SIZE, SPACE_SIZE, SPACE_SIZE)
    if 10 < i and i < 20:
        return pygame.rect.Rect(SPACE_SIZE * (i - 10), 0, SPACE_SIZE, SPACE_SIZE)
    if 20<=i and i<31:
        return pygame.rect.Rect(SCREENSIZE-SPACE_SIZE*2.095, (i-20)*SPACE_SIZE, SPACE_SIZE, SPACE_SIZE)
    if i>=31 and i<=39:
        return pygame.rect.Rect((27.95 - i) * SPACE_SIZE + SCREENSIZE,SCREENSIZE-SPACE_SIZE*2.05, SPACE_SIZE, SPACE_SIZE)



def draw_players(screen:pygame.Surface, players:List[Player_representation], font:pygame.font.Font, currently_playing_name:Optional[str], board):
    # Draw player tokens on their positions
    # players: List of dicts; dict: representation of a player
    # board[List:space_representation]]
    drawn_positions  = []
    for i, player in enumerate(players):
        # draw character
        if player.has_lost:
            player.color = RED
        elif player.name == currently_playing_name:
            player.color = CYAN
        else:
            player.color = BLACK
        rect = __calculate_space_rect(player.position)
        if player.position in drawn_positions: #we have multiple players at this space
            if drawn_positions.count(player.position) == 1:
                rect = rect.move(20, -20)
            elif drawn_positions.count(player.position) == 2:
                rect = rect.move(-20, +20)
            elif drawn_positions.count(player.position) == 3:
                rect = rect.move(+30, +30)
        pygame.draw.circle(screen, player.color, rect.center, 10)
        name_surf = font.render(player.name, True, player.color)
        screen.blit(name_surf, (rect.x+20, rect.y+15))
        drawn_positions.append(player.position)
        # draw player info
        __draw_player_info(player, i, font, screen, board)

def __draw_player_info(player:Player_representation, i:int, font, screen, board:Board_representation):
    y_start = 150 + 150*i
    text_name = Text_plate(RED, 200, y_start, f'PLayer {player.name}', LIGHTGREY, font)
    text_name.draw(screen)
    text_money = Text_plate(RED, 200, y_start + 30, f'Money: {player.money}', LIGHTGREY, font)
    text_money.draw(screen)
    this_players_properties_positions = sorted(player.properties)
    # print(f"[DEBUG] frontend: drawing player properties: {this_players_properties_positions}") # This value is correct, so the code works up until at least here
    if this_players_properties_positions:
        properties_names = []
        for pos in this_players_properties_positions:
            name = board.spaces[pos].get('name', None)
            properties_names.append(str(name))
        properties_str = ", ".join(properties_names)
    else:
        properties_str = "None"
    text_properties = Text_plate(RED, 200, y_start + 60, f'Properties: {properties_str}', LIGHTGREY, font)
    text_properties.draw(screen)

def draw_action_request(action_type_requested:str, font:pygame.font.Font, screen:pygame.Surface)->List[Button]:
    match action_type_requested:
        case 'before throw menu':
            # print("[DEBUG] Drawing buttons for menu: before throw")
            throw_dice_Button = Button(300, 600, 100, 100, 'throw dice', font, BLUE, CYAN, RED)
            throw_dice_Button.draw(screen)
            buysell_house_Button = Button(420, 600, 100, 100, 'manage buy/sell houses', font, BLUE, CYAN, RED)
            buysell_house_Button.draw(screen)
            mortgage_Button = Button(540, 600, 100, 100, 'mortgage properties', font, BLUE, CYAN, RED)
            mortgage_Button.draw(screen)
            offer_trade_to_player_Button = Button(660, 600, 100, 100, 'offer trade to other player', font, BLUE, CYAN, RED)
            offer_trade_to_player_Button.draw(screen)
            text = Text_plate(RED, 400, 500, 'Pick an option', LIGHTGREY, font)
            text.draw(screen)
            return throw_dice_Button, buysell_house_Button, mortgage_Button, offer_trade_to_player_Button
        case 'want to buy property':
            yes_button = Button(420, 600, 100, 100, 'yes', font, BLUE, CYAN, RED)
            no_button = Button(540, 600, 100, 100, 'no', font, BLUE, CYAN, RED)
            text = Text_plate(RED, 400, 500, 'Do you want to buy this property?', LIGHTGREY, font)
            text.draw(screen)
            yes_button.draw(screen)
            no_button.draw(screen)
            return yes_button, no_button
        
        case "buy sell houses city menu":
            text = Text_plate(RED, 435, 110, 'buy or sell houses at', LIGHTGREY, font)
            buttons = []
            for i,option in enumerate(['ons dorp', 'arnhem', 'haarlem', 'utrecht', 'groningen', 'den haag', 'rotterdam', 'amsterdam', 'return']):

                button = Button(550 + 150* (i%2), 180 + 100* (i//2), 120, 80, f'buy or sell houses at {option}', font, BLUE, CYAN, RED)
                button.draw(screen)
                buttons.append(button)
            return buttons
        
        case 'buy sell houses amount 2':
            NotImplemented
        case 'buy sell houses amount 3':
            NotImplemented

        case _:
            print("Unknown action type", action_type_requested)
            raise RuntimeError("action type that is requested is not recognised")



def draw_throw(screen:pygame.Surface, throw:int, font, name:str):
    throw_text = Text_plate(RED, 500, 180, f'Throw: {throw} by player {name}',LIGHTGREY, font)
    throw_text.draw(screen)
# Utility functions for buttons, popups, etc. (already present)

# You can add more functions as needed for cards, trades, etc.