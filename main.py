# PokerNowToOHH.py
# Mark Sudduth sudduth.mark@gmail.com

"""
****************************************************************************************************
WHAT THIS DOES

goal of this program is to process Poker Now (https://www.pokernow.club/) hand history csv files and
convert to JSON format that matches the standardized open hand History format specified by
PokerTracker and documented here: https://hh-specs.handhistory.org/

To do this we will take the logs and break it up hand by hand

Then we can loop through each hand, and convert to the JSON format specified.
Finally, we output the new JSON.

KEY ASSUMPTIONS

Working with Ring games only, not tournaments

Change Log
09-14-22 v 1.0.0 First Version
****************************************************************************************************
"""
# MODULES
from configparser import ConfigParser
import csv
import json
from logging import Logger
from pathlib import Path
import re

# END MODULES

# **************************************************************************************************

# **************************************************************************************************

# CONSTANTS
CONFIG_FILE = "config.ini"
TEXT = "text"
COUNT = "count"
LATEST = "latest"
LAST = "last"
OHH = "ohh"
HH_VERSION = "hh_version"
SHOW_DOWN = "Show Down"
PLAYER_STACKS = "Player stacks"
DEALER_NAME = "dealer_name"
TABLE = "table"

# OHH FIELD NAMES
SPEC_VERSION = "spec_version"
SITE_NAME = "site_name"
NETWORK_NAME = "network_name"
INTERNAL_VERSION = "internal_version"
GAME_NUMBER = "game_number"
DATETIME = "datetime"
START_DATE_UTC = "start_date_utc"
TABLE_NAME = "table_name"
GAME_TYPE = "game_type"
BET_LIMIT = "bet_limit"
BET_TYPE = "bet_type"
TABLE_SIZE = "table_size"
CURRENCY = "currency"
DEALER_SEAT = "dealer_seat"
SMALL_BLIND_AMOUNT = "small_blind_amount"
BIG_BLIND_AMOUNT = "big_blind_amount"
ANTE_AMOUNT = "ante_amount"
HERO_PLAYER_ID = "hero_player_id"
FLAGS = "flags"
PLAYERS = "players"
ID = "id"
SEAT = "seat"
NAME = "name"
DISPLAY = "display"
STARTING_STACK = "starting_stack"
ROUNDS = "rounds"
STREET = "street"
CARDS = "cards"
ACTIONS = "actions"
ACTION_NUMBER = "action_number"
PLAYER_ID = "player_id"
ACTION = "action"
AMOUNT = "amount"
IS_ALL_IN = "is_allin"
POTS = "pots"
NUMBER = "number"
RAKE = "rake"
PLAYER_WINS = "player_wins"
WIN_AMOUNT = "win_amount"
CONTRIBUTED_RAKE = "contributed_rake"
# END OF OHH FIELD NAMES

# CONSTANTS FOR PROCESSING INI
HERO_NAME = "hero_name"
PREFIX = "output_prefix"
# END SCRIPT LEVEL CONSTANTS

# CONFIGURABLE CONSTANTS
DEFAULT_CONFIG = {
    SPEC_VERSION: "1.2.2",
    INTERNAL_VERSION: "1.2.2",
    NETWORK_NAME: "PokerStars",
    SITE_NAME: "PokerStars",
    CURRENCY: "USD",
    PREFIX: "HHC",
    HERO_NAME: "hero",
}
"""
these are constants that are meant to be configurable - they could be edited here,
or specified in a configuration file that is external to this script and checked for at run time
"""
# END CONSTANTS
# **************************************************************************************************

# **************************************************************************************************

# DATA STRUCTURES
hands = {}
"""
the hands dictionary
    - structure
        - KEY: string - hand number
        - DATETIME: string - timestamp for the hand
        - BET_TYPE: string - The betting structure (Pot Limit, No Limit)
        - GAME_TYPE: string - The game type (Texas Hold'em, Omaha High, Omaha Hi/Lo 8 or Better)
        - DEALER_NAME: string - The name of the dealer
        - TABLE: string - table where the hand happened
        - BIG_BLIND_AMOuNT: float - Amount of the big blind 
        - SMALL_BLIND_AMOUNT: float - Amount of the small blind
        - ANTE_AMOUNT: float - Amount of the ante
        - TEXT: string - full text of hand, with newlines
"""
tables = {}
"""
the tables dictionary
    - structure
        - KEY: string - table name as found in log
        - COUNT: integer - number of hands processed for table
        - LATEST: datetime - the latest time stamp for a hand processed for this table
        - LAST: string - hand number for the latest hand processed for this table
            - LAST and LATEST are used to mark the "end" activity of players standing up
              they represent the last seen hand at the table from the processed logs
        - OHH: list - list of hand histories, each in JSON following the OHH format
"""
# END DATA STRUCTURES

# LOOKUP TABLE
structures = {"Pot Limit": "PL", "No Limit": "NL"}

games = {
    "Texas Hold'em": "Holdem",
    "Omaha Hi/Lo 8 or Better": "OmahaHiLo",
    "Omaha Hi": "Omaha",
}

first_rounds = {
    "Holdem": "Preflop",
    "Omaha": "Preflop",
    "OmahaHiLo": "Preflop",
}

make_new_round = {
    "Player stacks": "Preflop",
    "Flop": "Flop",
    "Turn": "Turn",
    "River": "River",
    "Show Down": "Showdown",
}

post_types = {
    "posts an ante": "Post Ante",
    "posts a big blind": "Post BB",
    "posts a small blind": "Post SB",
    "posts a straddle": "Straddle",
    "posts a missing small blind": "Post Dead",
    "posts a missed big blind": "Poast Dead"
}

verb_to_action = {
    "bets": "Bet",
    "calls": "Call",
    "raises": "Raise",
    "folds": "Fold",
    "checks": "Check",
}
# END DATA STRUCTURES
# **************************************************************************************************

# **************************************************************************************************

# FUNCTIONS
# def create_config(path):
#     """
#     Create a config file
#     """
#     config = configparser.ConfigParser()
#     config.add_section("HH Constants")
#     for key, option in DEFAULT_CONFIG.items():
#         config.set("HH Constants", key, option)

#     with open(path, "w", encoding='utf-8') as config_file:
#         config.write(config_file)


# def get_config(path):
#     """
#     Returns the config object
#     """
#     if not Path(path).resolve().exists():
#         create_config(path)

#     config = configparser.ConfigParser()
#     config.read(path)
#     return config


# def get_setting(path, section, setting):
#     """
#     Get setting
#     """
#     config = get_config(path)
#     setting_value = config.get(section, setting)
#     return setting_value


def csv_reader(file_obj, rows):
    """
    Read a CSV file
    """
    reader = csv.reader(file_obj)
    next(reader)
    subs_dict = {
        "10♥": "Th",
        "10♠": "Ts",
        "10♦": "Td",
        "10♣": "Tc",
        "♥": "h",
        "♠": "s",
        "♦": "d",
        "♣": "c",
    }
    for row in reader:
        subs_regex = re.compile("|".join(subs_dict.keys()))
        row = [subs_regex.sub(lambda match: subs_dict[match.group(0)], i) for i in row]
        rows.append(row)
    return rows.reverse()


# end of functions
# **************************************************************************************************


# **************************************************************************************************
# CODE

# look for configuration file and read it into the config parser.  If the configuation file is not
# found then create a config file and write the default values to the file.
config = ConfigParser()
try:
    with open(CONFIG_FILE, encoding="utf-8") as config_file:
        config.read_file(config_file)
except FileNotFoundError:
    with open(CONFIG_FILE, mode="x", encoding="utf-8") as config_file:
        config["OHH Constants"] = DEFAULT_CONFIG
        config.write(config_file)
        config.read_file(config_file)
ohh_constants = config["OHH Constants"]
spec_version = ohh_constants[SPEC_VERSION]
internal_version = ohh_constants[INTERNAL_VERSION]
network_name = ohh_constants[NETWORK_NAME]
site_name = ohh_constants[SITE_NAME]
currency = ohh_constants[CURRENCY]
hero_name = ohh_constants[HERO_NAME]

csv_dir = Path("PokerNowHandHistory")
csv_file_list = [child for child in csv_dir.iterdir() if child.suffix == ".csv"]

# look for aliase->name map file (aliase-name_map.json) and parse it.  If the file is not found
# then create a json file.
try:
    with open("name-map.json", encoding="utf-8") as name_map:
        name_map = json.load(name_map)
except FileNotFoundError:
    with open("name-map.json", mode="x", encoding="utf-8") as name_map:
        name_map = json.load(name_map)

# Players can choose a different alias every time they sit at the table; therefore, it is necissary
# to map the players real name to the aliases they have chosen. The information needed to
# create the aliase->name map is recorded in the file aliase-name_map.json where each player name
# has an array of aliases. The data will be parsed into a dictionary of lists where the keys are
# the names and the values are lists of aliases. The aliase->name map is created by flattening the
# aliase lists and switching the keys (names) and values (aliases)
names = {}
for key, values in name_map.items():
    for value in values:
        names[value] = key

# Compile regular expressions for matching to identifiable strings in the hand history
table_regex = re.compile(r"^.*poker_now_log_(?P<table_name>.*).csv$")
blind_regex = re.compile(
    r"The game's (?P<blind_type>.+) was changed from \d+\.\d+ to (?P<amount>\d+.\d+)"
)
start_regex = re.compile(
    r'-- starting hand #(?P<game_number>\d+)  \((?P<bet_type>\w*\s*Limit) (?P<game_type>.+)\) \((dealer: \"(?P<player>.+?) @ (?P<device_id>[-\w]+)\"|dead button)\) --'
)
hand_time_regex = re.compile(r"(?P<start_date_utc>.+\.\d+Z)")
seats_regex = re.compile(
    r' #(?P<seat>\d+) \"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" \((?P<amount>[\d.]+)\)'
)
post_regex = re.compile(
    r'\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<type>posts a .+) of (?P<amount>\d+.\d+)'
)
round_regex = re.compile(r"(?P<street>^[\w ]+):.+")
cards_regex = re.compile(r"\[(?P<cards>.+)\]")
addon_regex = re.compile(r"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" adding (?P<amount>[\d.]+)")
hero_hand_regex = re.compile(r"Your hand is (?P<cards>.+)")
non_bet_action_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<player_action>\w+(?![ a-z]+[ \d.]+))"
)
bet_action_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?!collected)(?!shows)(?P<player_action>\w+) [a-z]*\s*(?P<amount>[\d.]+)\s*(?P<all_in>[a-z ]+)*"
)
show_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<player_action>\w+) a (?P<cards>\w{2}, \w{2})"
)
winner_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<player_action>collected) (?P<amount>[\d.]+)"
)


# Process each file in the Poker Now hand history folder
for poker_now_file in csv_file_list:
    # Initialize variables to their default starting values
    lines = [[]]
    fields = []
    big_blind: float = 0.20
    small_blind: float = 0.10
    ante: float = 0.00
    # Open and parse the hand history with csv reader
    with open(poker_now_file, encoding="UTF-8") as f:
        csv_reader(f, lines)
    # The text match to look for table name.
    table_name_match = re.match(table_regex, poker_now_file.name)
    table_name = table_name_match.group("table_name")
    # Parse and get each hand separated, and get basic hand info into the hands dictionary basic
    # hand info is hand number, hand time, bet type, game type, dealer name, table name, big blind,
    # small blind, and ante. Everything else goes into TEXT.
    for i, line in enumerate(lines):
        if i == len(lines) - 1:
            break
        entry = line[0]
        #print(i, table_name)
        # The hand "begins" when the "--- begin hand #X ---" log line is read, however the hand
        # does not "end" until the following "--- begin hand #X+1 ---" log line is observed (or
        # the end of the file is reached). This is because some actions such as a player
        # voluntarily showing their cards at the end of the hand are reported between the
        # "--- end hand #X ---" and the "--- begin hand #X+1 ---" lines
        # Now increment the iterator and add lines to the TEXT key in the hands dictionary
        # until the next hand is started
        if not table_name in tables:
            tables[table_name] = {COUNT: 0, LATEST: "", OHH: []}
        # The text match to look for what the blinds are set at
        if "The game's" in entry:
            blinds_match = re.match(blind_regex, entry)
            blind_type = blinds_match.group("blind_type")
            blind_amount = float(blinds_match.group("amount"))
            if blind_type == "big blind":
                big_blind = blind_amount
            elif blind_type == "small blind":
                small_blind = blind_amount
            elif blind_type == "ante":
                ante = blind_amount
        # the text match to look for the start of a hand
        elif "-- starting hand " in entry:
            hand_start_match = re.match(start_regex, entry)
            hand_number = hand_start_match.group("game_number")
            bet_type = hand_start_match.group("bet_type")
            game_type = hand_start_match.group("game_type")
            if not "dead button" in entry:
                dealer_name = hand_start_match.group("player")
            # the text match to look for the time the hand started
            hand_time_match = re.match(hand_time_regex, line[1])
            hand_time = hand_time_match.group("start_date_utc")
            # Add the information extracted from the start of the hand to the the hands dictionary
            hands[hand_number] = {
                DATETIME: hand_time,
                BET_TYPE: bet_type,
                GAME_TYPE: game_type,
                DEALER_NAME: dealer_name,
                TABLE: table_name,
                BIG_BLIND_AMOUNT: big_blind,
                SMALL_BLIND_AMOUNT: small_blind,
                ANTE_AMOUNT: ante,
                TEXT: "",
            }
            # Translate values from lookup tables
            hands[hand_number][BET_TYPE] = structures[bet_type]
            hands[hand_number][GAME_TYPE] = games[game_type]
        elif (
            "joined" in entry
            or "requested" in entry
            or "quits" in entry
            or "created" in entry
            or "approved" in entry
            or "changed" in entry
            or "enqueued" in entry
            or " stand up " in entry
            or " sit back " in entry
            or " canceled the seat " in entry
            or " decide whether to run it twice" in entry
            or "chooses to  run it twice." in entry
            or "Dead Small Blind" in entry
            or "The admin updated the player " in entry
            or "the admin queued the stack change " in entry
        ):
            pass
        else:
            hands[hand_number][TEXT] = (
                hands[hand_number][TEXT] + "\n" + entry
            )
    # now that we have all hands from all the files, use the hand number of the imported hands to
    # process them in sequential order. This is the place for processing the text of each hand
    # and look for player actions
    hand_number: str = 0
    for hand_number in hands:
        print(hand_number)
        table = hands[hand_number][TABLE]
        hand_time = hands[hand_number][DATETIME]
        tables[table][COUNT] += 1
        tables[table][LATEST] = hand_time
        tables[table][LAST] = hand_number
        # initialize the OHH JSON populating as many fields as possible and initializing key arrays
        ohh = {
            SPEC_VERSION: spec_version,
            SITE_NAME: site_name,
            NETWORK_NAME: network_name,
            INTERNAL_VERSION: internal_version,
            GAME_NUMBER: hand_number,
            START_DATE_UTC: hands[hand_number][DATETIME],
            TABLE_NAME: hands[hand_number][TABLE],
            GAME_TYPE: hands[hand_number][GAME_TYPE],
            BET_LIMIT: {BET_TYPE: hands[hand_number][BET_TYPE]},
            TABLE_SIZE: 10,
            CURRENCY: currency,
            DEALER_SEAT: 1,
            SMALL_BLIND_AMOUNT: hands[hand_number][SMALL_BLIND_AMOUNT],
            BIG_BLIND_AMOUNT: hands[hand_number][BIG_BLIND_AMOUNT],
            ANTE_AMOUNT: hands[hand_number][ANTE_AMOUNT],
            HERO_PLAYER_ID: 0,
            FLAGS: [],
            PLAYERS: [],
            ROUNDS: [],
            POTS: [],
        }
        # initialize variables, lists, and dictionaries for a new hand
        players = []
        player_ids = {}
        current_round: str = None
        hero_playing: bool = False
        winners = []
        round_number: int = 0
        action_number: int = 0
        pot_number: int = 0
        round_obj = {ID: 0, STREET: "", CARDS: [], ACTIONS: []}
        pot_obj = {}
        round_commit = {}
        hand_text: str = hands[hand_number][TEXT]
        # Split the hand text loop through it line by line looking for regular expressions to parse
        for line in hand_text.strip().splitlines(False):
            # The text match to look for a seated player and see their starting chip amount.
            seats = re.finditer(seats_regex, line)
            if seats is not None:
                player_id = int(0)
                for player in seats:
                    seat_number = int(player.group("seat"))
                    player_display = str(player.group("player"))
                    player_stack = float(player.group("amount"))
                    players.append(
                        {
                            ID: player_id,
                            SEAT: seat_number,
                            NAME: names[player_display],
                            DISPLAY: player_display,
                            STARTING_STACK: player_stack,
                        }
                    )
                    player_ids[player_display] = player_id
                    # If the player is the dealer, set the value of the dealers seat number in the
                    # ohh dictionary
                    if hands[hand_number][DEALER_NAME] == player_display:
                        ohh[DEALER_SEAT] = seat_number
                    # If the player is the hero, set the value of players ID in the ohh dictionary.
                    if names[player_display] == hero_name:
                        ohh[HERO_PLAYER_ID] = player_id
                        hero_playing: bool = True
                    player_id += 1
            # the text to match for a post this also indicates that the dealing is happening and we
            # should move to the phase of assembling rounds of actions.
            post = re.match(post_regex, line)
            if post is not None:
                player = post.group("player")
                post_type = post.group("type")
                amount = float(post.group("amount"))
                #########################################################################################################
                # if current_round is not None:
                #     rounds[ID] = round_number
                #     current_round = first_rounds[ohh[GAME_TYPE]]
                #     rounds[STREET] = current_round
                #     round_commit[player] = amount
                #########################################################################################################
                round_obj[ID] = round_number
                current_round = first_rounds[ohh[GAME_TYPE]]
                round_obj[STREET] = current_round
                round_commit[player] = amount
                action = {}
                action[ACTION_NUMBER] = action_number
                action[PLAYER_ID] = player_ids[player]
                action[ACTION] = post_types[post_type]
                action[AMOUNT] = amount
                round_obj[ACTIONS].append(action)
                action_number += 1
            # look for round markers note that cards dealt are melded together with opening round and do
            # not necessarily mark a new round
            round_marker = re.match(round_regex, line)
            cards_match = re.search(cards_regex, line)
            if round_marker is not None:
                label = round_marker.group("street")
                if label == PLAYER_STACKS:
                    if current_round is None:
                        action_number: int = 0
                        round_obj[ID] = round_number
                        current_round = first_rounds[ohh[GAME_TYPE]]
                        round_obj[STREET] = current_round
                        action = {}
                        round_commit = {}
                        for p in player_ids:
                            round_commit[p] = float(0)
                elif label in make_new_round:
                    # cards = Cards.group("cards")
                    # make new round
                    # we need to add current round object to the OHH JSON
                    # and make a clean one
                    # increment round number and reset action number
                    ohh[ROUNDS].append(round_obj)
                    round_obj = {}
                    round_number += 1
                    action_number: int = 0
                    current_round = make_new_round[label]
                    round_obj[ID] = round_number
                    round_obj[STREET] = current_round
                    round_obj[CARDS] = []
                    round_obj[ACTIONS] = []
                    round_commit = {}
                    for p in player_ids:
                        round_commit[p] = 0
                    if cards_match is not None:
                        cards = cards_match.group("cards")
                        for card in cards.split():
                            round_obj[CARDS].append(card)
                    else:
                        continue
            show_hand = re.search(show_regex, line)

            if show_hand is not None:
                player = show_hand.group("player")
                does = show_hand.group("player_action")
                cards = show_hand.group("cards")
                if current_round != SHOW_DOWN:
                    ohh[ROUNDS].append(round_obj)
                    round_obj = {}
                    round_number += 1
                    action_number: int = 0
                    current_round: str = SHOW_DOWN
                    round_obj[ID] = round_number
                    round_obj[STREET] = make_new_round[SHOW_DOWN]
                    round_obj[ACTIONS] = []
                action = {}
                action[ACTION_NUMBER] = action_number
                action[PLAYER_ID] = player_ids[player]
                action[ACTION] = "Shows Hand"
                action[CARDS] = []
                for card in cards.split():
                    action[CARDS].append(card)
                round_obj[ACTIONS].append(action)
                action_number += 1
                round_commit = {}
                for p in player_ids:
                    round_commit[p] = 0
                continue
            # the text to match for an add on
            add_on = re.match(addon_regex, line)

            if add_on is not None:
                player = add_on.group("player")
                additional = float(add_on.group("amount"))
                if current_round is not None and player in player_ids:
                    action = {}
                    action[ACTION_NUMBER] = action_number
                    action[PLAYER_ID] = player_ids[player]
                    action[AMOUNT] = additional
                    action[ACTION] = "Added Chips"
                    round_obj[ACTIONS].append(action)
                    action_number += 1
                continue
            # the text to match for cards dealt
            hero_hand = re.match(hero_hand_regex, line)
            if hero_hand is not None:
                cards = hero_hand.group("cards")
                action = {}
                action[ACTION_NUMBER] = action_number
                action[PLAYER_ID] = ohh[HERO_PLAYER_ID]
                action[ACTION] = "Dealt Cards"
                action[CARDS] = []
                for card in cards.split():
                    action[CARDS].append(card)
                round_obj[ACTIONS].append(action)
                action_number += 1
                continue
            non_bet_action = re.match(non_bet_action_regex, line)
            if non_bet_action is not None:
                player = non_bet_action.group("player")
                does = non_bet_action.group("player_action")
                action = {}
                action[ACTION_NUMBER] = action_number
                action[PLAYER_ID] = player_ids[player]
                action[ACTION] = verb_to_action[does]
                round_obj[ACTIONS].append(action)
                action_number += 1
                continue

            bet_action = re.match(bet_action_regex, line)
            if bet_action is not None:
                player = bet_action.group("player")
                does = bet_action.group("player_action")
                amount = float(bet_action.group("amount"))
                allIn = bet_action.group("all_in")
                action = {}
                action[ACTION_NUMBER] = action_number
                action[PLAYER_ID] = player_ids[player]
                action[ACTION] = verb_to_action[does]
                if does in ("raises", "calls"):
                    amount = round(amount - round_commit[player], 2)
                action[AMOUNT] = amount
                round_commit[player] += amount
                if allIn is not None:
                    action[IS_ALL_IN] = True
                round_obj[ACTIONS].append(action)
                action_number += 1
                continue
            winner = re.match(winner_regex, line)
            if winner is not None:
                player = winner.group("player")
                does = winner.group("player_action")
                amount = float(winner.group("amount"))
                player_id = player_ids[player]
                winners.append(player_id)
                if pot_number not in pot_obj:
                    pot_obj[pot_number] = {
                        NUMBER: pot_number,
                        AMOUNT: 0.00,
                        RAKE: 0.00,
                        PLAYER_WINS: {},
                    }
                if not player_id in pot_obj[pot_number][PLAYER_WINS]:
                    pot_obj[pot_number][PLAYER_WINS][player_id] = {
                        PLAYER_ID: player_id,
                        WIN_AMOUNT: 0.00,
                        CONTRIBUTED_RAKE: 0.00,
                    }
                pot_obj[pot_number][AMOUNT] += amount
                pot_obj[pot_number][PLAYER_WINS][player_id][WIN_AMOUNT] += amount

        for pot_number in pot_obj:
            amt = pot_obj[pot_number][AMOUNT]
            rake = pot_obj[pot_number][RAKE]
            potObj = {NUMBER: pot_number, AMOUNT: amt, RAKE: rake, PLAYER_WINS: []}
            for player_id in pot_obj[pot_number][PLAYER_WINS]:
                win_amount = pot_obj[pot_number][PLAYER_WINS][player_id][WIN_AMOUNT]
                rake_contribution = pot_obj[pot_number][PLAYER_WINS][player_id][
                    CONTRIBUTED_RAKE
                ]
                player_win_obj = {
                    PLAYER_ID: player_id,
                    WIN_AMOUNT: win_amount,
                    CONTRIBUTED_RAKE: rake_contribution,
                }
                potObj[PLAYER_WINS].append(player_win_obj)
            ohh[POTS].append(potObj)

            # print(line)
            # print(hands[handNumber][TEXT].strip().splitlines(False))
        ohh[PLAYERS] = players
        ohh[ROUNDS].append(round_obj)
        tables[table][OHH].append(ohh)

        # print(ohh)
    ohh_directory = Path("OpenHandHistory")
    for table in tables:
        with open(
            ohh_directory / poker_now_file.with_suffix(".ohh").name,
            "w",
            encoding="utf-8",
        ) as f:
            for ohh in tables[table][OHH]:
                wrapped_ohh = {}
                wrapped_ohh[OHH] = ohh
                f.write(json.dumps(wrapped_ohh, indent=4))
                f.write("\n")
                f.write("\n")

# end of code
# *************************************************************************************************
