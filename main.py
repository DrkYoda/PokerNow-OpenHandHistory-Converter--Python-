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

10-06-22 v 1.0.3
    - Added timers to parts of the code to benchmark performance
    - Made improvements to the way the program selects lines that should be ignored.
    - Made improvements to the logging feature.
        - Code performance will be logged.
        - Lines that don't get processed will be logged in order to add them to the ignore list.
        - It will be logged when the calculated pot amount is not equal to the the collected amount.
v 1.0.4
    - Made change to correctly handle dead blinds.
    - Corrected a problem that was causing become progressively slower with multiple files.
    - Added ability to parse hands that run it twice.
    - Fixed issue #4 where Omaha hands were being converted to 2 card hands.
    - Fixed issue #8 Dummy ohh object with "game_number": "0"
v 1.1.0
    - Fixed issue #13 and added the attribute "is_allin" to action objects that have an amount>0.00
    - Fixed issue #14 At showdown the action value is now the valid value "Shows Cards"
    - Fixed issue #15 removed the extra comma after cards in the text string
    - Fixed issue #19 game_number attribute is now a unique identifier for a hand.
v 1.1.1
    - Fixed issue #23 Unicode characters will be removed from names.
    - Fixed issue #25 Pots are now calculated correctly when the SB posts a missed BB
v 1.1.2
    - Fixed issue #26 The blind structure will initially be determined from the amounts posted in
      first hand, but if the blind structure is changed after the first hand the structure will be
      determined from the metadata after the first hand.
v 1.1.3
    - Fixed issue #30 If the information in the last hand is incomplete then it will not be parsed
      an converted into the OHH standard.
v 1.2.0
    - Fixed issue #10 The name-map data model is now handled programmatically so when an aliase or
      device ID is not in the data model the program will require input from the user and update the
      data model before continuing.
    - Fixed issue #31 If the hero is not dealt into the hand will have the flags value "Observed"
v 1.2.1
    - Fixed issue #32 After a Poker Now csv file is parsed the file is moved to an archive folder
    - Improved how the name-map data model is handled programmatically.
v 1.2.2
    - Fixed issue #38 If the hero name is an empty screen, the user will be propted to enter a name 
v 1.2.3
    - Fixed issue #43
v 1.2.4
    - Fixed issue #45
****************************************************************************************************
"""
# MODULES
from configparser import ConfigParser
import csv
from datetime import datetime
import json
import logging
from pathlib import Path
import re
from shutil import move
from time import perf_counter, process_time
from typing import List
from rich.console import Console

# END MODULES
# **************************************************************************************************

# **************************************************************************************************
timer_perf_start = perf_counter()
timer_proc_start = process_time()
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
OHH_CONSTANTS = "OHH Constants"
DIRECTORIES = "Directories"
CONFIG_DIR = "config_dir"
LOG_DIR = "log_dir"

DEFAULT_CONFIG = {
    OHH_CONSTANTS: {
        SPEC_VERSION: "1.2.2",
        INTERNAL_VERSION: "1.2.2",
        NETWORK_NAME: "PokerStars",
        SITE_NAME: "PokerStars",
        CURRENCY: "USD",
        PREFIX: "HHC",
        HERO_NAME: "",
    },
    DIRECTORIES: {CONFIG_DIR: "/Config", LOG_DIR: "/Logs"},
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
        - BIG_BLIND_AMOUNT: float - Amount of the big blind
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
    "Flop (second run)": "Flop",
    "Turn": "Turn",
    "Turn (second run)": "Turn",
    "River": "River",
    "River (second run)": "River",
    "Show Down": "Showdown",
}

post_types = {
    "posts an ante": "Post Ante",
    "posts a big blind": "Post BB",
    "posts a small blind": "Post SB",
    "posts a straddle": "Straddle",
    "posts a missing small blind": "Post Dead",
    "posts a missed big blind": "Post Extra Blind",
}

verb_to_action = {
    "bets": "Bet",
    "calls": "Call",
    "raises": "Raise",
    "folds": "Fold",
    "checks": "Check",
}

subs_suits = {
    "10♥": "Th",
    "10♠": "Ts",
    "10♦": "Td",
    "10♣": "Tc",
    "♥": "h",
    "♠": "s",
    "♦": "d",
    "♣": "c",
}
# END LOOKUP TABLES
# **************************************************************************************************


# **************************************************************************************************
# FUNCTIONS
def create_config(path: Path) -> None:
    """Create a config file with default configuation. If the parent path does not exist then
    create it.

    Args:
        path (Path): Path to the file to be created.

    Returns:
        None
    """
    if not path.parent.exists():
        path.parent.mkdir()
    config = ConfigParser()
    config.read_dict(DEFAULT_CONFIG)

    with path.open(mode="w", encoding="UTF-8") as config_file:
        config.write(config_file)


def get_config(path: Path) -> ConfigParser:
    """Get the config object from the .ini file at path. If the .ini file does not exist then create
    it.

    Args:
        path (Path): Path to the config file.

    Returns:
        ConfigParser: The main configuration parser, responsible for managing the parsed database.
    """
    if not path.exists():
        create_config(path)

    config = ConfigParser()
    config.read(path)
    return config


def update_setting(path: Path, section: str, setting: str, value: str) -> None:
    """Update a setting.

    Args:
        path (Path): Path to the file to be updated.
        section (str): Section where the setting to be updated is located.
        setting (str): Name of the setting to be updated.
        value (str): Value of the setting to be updated.

    Returns:
        None

    """
    config = get_config(path)
    config.set(section, setting, value)
    with path.open(mode="w", encoding="UTF-8") as config_file:
        config.write(config_file)


def csv_reader(file_obj: Path, subs: dict[str, str]) -> list[List[str]]:
    """Read a CSV file and make substitutions according to the subs dictionary.

    Args:
        file_obj (Path): Path to the CSV file to be read.
        subs (dict): Dictionary containg strings to substitute or replace in the data.

    Returns:
        List[List[str]]: The rows of data in the CSV file in reverse order.
    """
    rows: list[List[str]] = [[]]
    subs_regex = re.compile("|".join(subs.keys()))
    with file_obj.open(mode="r", encoding="UTF-8") as csv_file:
        reader = csv.reader(csv_file)
        next(reader)
        for row in reader:
            row = [subs_regex.sub(lambda match: subs[match.group(0)], i) for i in row]
            row[0] = row[0].encode("ascii", "ignore").decode()
            rows.append(row)
    rows.reverse()
    return rows


def load_name_map(file: Path):
    """Open aliase->name map file (aliase-name_map.json) and parse it.  If the file is not found
        then create a json file.

    Args:
        file (Path): Path to the input file to be parsed

    Returns:
        _type_: _description_
    """
    try:
        with open(file, mode="r", encoding="utf-8") as map_file:
            return json.load(map_file)
    except FileNotFoundError:
        with open(file, mode="a+", encoding="utf-8") as map_file:
            init_name_map: dict[str, dict[str, list[str]]] = {}
            save_name_map(file, init_name_map)
            return json.load(map_file)


def save_name_map(file: Path, name_map: dict[str, dict[str, list[str]]]):
    """_summary_

    Args:
        file (Path): Path to the input file to be parsed
        name_map (dict[str, dict[str, list[str]]]): _description_
    """
    try:
        with open(file, mode="w", encoding="utf-8") as map_file:
            json.dump(dict(sorted(name_map.items())), map_file, indent=4)
    except FileNotFoundError:
        with open(file, mode="a+", encoding="utf-8") as map_file:
            json.dump(name_map, map_file, indent=4)


def switch_key_and_values(name_map: dict[str, dict[str, list[str]]], key_txt: str):
    """Players can choose a different alias every time they sit at the table; therefore, it is
    necissary to map the players real name to the aliases they have chosen. The information
    needed to create the aliase->name map is recorded in the file aliase-name_map.json where
    each player name has an array of aliases. The data will be parsed into a dictionary of lists
    where the keys are the names and the values are lists of aliases. The aliase->name map is
    created by flattening the alias lists and switching the keys (names) and values (aliases)

    Args:
        name_map (dict[str, dict[str, list[str]]]): _description_
        key_txt (str): _description_

    Returns:
        dict[str, str]: _description_
    """
    names: dict[str, str] = {}
    for key, values in name_map.items():
        for value in values[key_txt]:
            names[value] = key
    return names


# END OF FUNCTIONS
# **************************************************************************************************


# **************************************************************************************************
# CODE
name_map_path = Path("Config/name-map.json")
console = Console()
config_path = Path("Config/config.ini")
config = get_config(config_path)
ohh_constants = config["OHH Constants"]
spec_version = ohh_constants[SPEC_VERSION]
internal_version = ohh_constants[INTERNAL_VERSION]
network_name = ohh_constants[NETWORK_NAME]
site_name = ohh_constants[SITE_NAME]
currency = ohh_constants[CURRENCY]
hero_name = ohh_constants[HERO_NAME]
# Check if hero_name is an empty string, if True then prompt the user to input a name for the hero
# and save the name to config.ini
if not hero_name.strip():
    hero_name = console.input("Type in a name for the hero and press <ENTER>")
    ohh_constants[HERO_NAME] = hero_name
    update_setting(config_path, "OHH Constants", HERO_NAME, hero_name)

csv_dir = Path("PokerNowHandHistory")
csv_file_list = [child for child in csv_dir.iterdir() if child.suffix == ".csv"]
csv_archive_dir = csv_dir / "Archive"
players_map = load_name_map(name_map_path)
aliases_names = switch_key_and_values(players_map, "nicknames")
device_ids = switch_key_and_values(players_map, "devices")


# Compile regular expressions for matching to identifiable strings in the hand history
table_regex = re.compile(r"^.*poker_now_log_(?P<table_name>.*).csv$")
blind_regex = re.compile(
    r"The game's (?P<blind_type>.+) was changed from (\d+\.\d{2}|\d+) to "
    r"(?P<amount>\d+\.\d{2}|\d+)\."
)
start_regex = re.compile(
    r"-- starting hand #(?P<hand_number>\d+).+\((?P<bet_type>\w*\s*Limit) (?P<game_type>.+)\)"
    r" \((dealer: \"(?P<player>.+?) @ (?P<device_id>[-\w]+)\"|dead button)\) --"
)
end_regex = re.compile(r"-- ending hand #(?P<hand_number>\d+) --")
game_number_regex = re.compile(r"(?P<game_number>\d{13})")
hand_time_regex = re.compile(r"(?P<start_date_utc>.+:\d+)")
seats_regex = re.compile(
    r" #(?P<seat>\d+) \"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" \((?P<amount>\d+\.\d{2})\)"
)
post_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<type>posts a .+) "
    r"of (?P<amount>\d+\.\d{2})\s*(?P<all_in>[a-z ]+)*"
)
round_regex = re.compile(r"(?P<street>^\w.+):.+")
cards_regex = re.compile(r"\[(?P<cards>.+)\]")
addon_regex = re.compile(
    r"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" adding (?P<amount>\d+\.\d{2})"
)
hero_hand_regex = re.compile(r"Your hand is (?P<cards>.+)")
non_bet_action_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<player_action>\w+(?![ a-z]+\d+\.\d{2}))"
)
bet_action_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?!collected)(?!shows)(?P<player_action>\w+) "
    r"[a-z]*\s*(?P<amount>\d+\.\d{2})\s*(?P<all_in>[a-z ]+)*"
)
uncalled_regex = re.compile(
    r"Uncalled bet of (?P<amount>\d+\.\d{2}) .+ \"(?P<player>.+?) @ (?P<device_id>[-\w]+)\""
)
show_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" "
    r"(?P<player_action>\w+) a (?P<cards>[\dAKQJTshcd, ]+)\."
)
winner_regex = re.compile(
    r"\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\" (?P<player_action>collected) "
    r"(?P<amount>\d+\.\d{2}).+"
)
log_dir = Path("./Logs")
log_dir.mkdir(exist_ok=True)
log_file = Path("log_" + datetime.now().strftime("%Y%m%d-%H%M%S")).with_suffix(".log")
log_path = log_dir / log_file
logging.basicConfig(
    filename=log_path,
    format="[%(asctime)s][%(created)f][%(levelname)s]:%(message)s",
    level=logging.DEBUG,
)

# Process each file in the Poker Now hand history folder
for poker_now_file in csv_file_list:
    perf_start_1 = perf_counter()
    proc_start_1 = process_time()
    # Initialize variables to their default starting values
    big_blind: float = 20.00
    small_blind: float = 10.00
    ante: float = 0.00
    dealer_name: str = ""
    table_name: str = ""
    game_number: str = "0"
    hand_number: str = "0"
    end_hand_number: str = "0"
    hands = {}
    lines_ignored: int = 0
    lines_parsed: int = 0
    lines_saved: int = 0
    hand_count: int = 0
    table = []
    # The text match to look for table name.
    table_name_match = re.match(table_regex, poker_now_file.name)
    if table_name_match is not None:
        table_name = table_name_match.group("table_name")
        # Open and parse the hand history with csv reader
        lines = csv_reader(poker_now_file, subs_suits)
        logging.info(f"[{table_name}] ***STARTING HAND SEPERATION***")
        logging.info(f"[{table_name}] has {len(lines)} lines to parse.")
        # Parse and get each hand separated, and get basic hand info into the hands dictionary basic
        # hand info is hand number, hand time, bet type, game type, dealer name, table name, big
        # blind, small blind, and ante. Everything else goes into TEXT.
        for i, line in enumerate(lines):
            if i == len(lines) - 1:
                if hand_number != end_hand_number:
                    hands.pop(game_number)
                break
            entry: str = line[0]
            if table_name not in tables:
                tables[table_name] = {COUNT: 0, LATEST: "", OHH: []}
            # The text match to look for what the blinds are set at
            blinds_match = re.match(blind_regex, entry)
            if blinds_match is not None:
                blind_type = blinds_match.group("blind_type")
                blind_amount = float(blinds_match.group("amount"))
                if blind_type == "big blind":
                    big_blind = blind_amount
                elif blind_type == "small blind":
                    small_blind = blind_amount
                elif blind_type == "ante":
                    ante = blind_amount
                lines_parsed += 1
                continue
            # The hand "begins" when the "--- starting hand #X ---" log line is read, however the
            # hand does not "end" until the following "--- starting hand #X+1 ---" log line is
            # observed (or the end of the file is reached). This is because some actions such as a
            # player voluntarily showing their cards at the end of the hand are reported between the
            # "--- end hand #X ---" and the "--- stating hand #X+1 ---" lines
            hand_start_match = re.match(start_regex, entry)
            hand_end_match = re.match(end_regex, entry)
            if hand_start_match is not None:
                game_number_match = re.match(game_number_regex, line[2])
                hand_number = hand_start_match.group("hand_number")
                if game_number_match is not None:
                    game_number = game_number_match.group("game_number")
                bet_type = hand_start_match.group("bet_type")
                game_type = hand_start_match.group("game_type")
                # If the button is dead, keep the dealer the same as the previous hand. Technically
                # this is incorrect because a dead button is located at an empty seat, but
                # effectively it is the same because the player who had the button previously will
                # have position.
                if "dead button" not in entry:
                    dealer_name = hand_start_match.group("player")
                # the text match to look for the time the hand started
                hand_time_match = re.match(hand_time_regex, line[1])
                if hand_time_match is not None:
                    hand_time = hand_time_match.group("start_date_utc") + "Z"
                    # Add the information extracted from the start of the hand to the hands
                    # dictionary
                    hands[game_number] = {
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
                    hands[game_number][BET_TYPE] = structures[bet_type]
                    hands[game_number][GAME_TYPE] = games[game_type]
                    lines_parsed += 1
                    hand_count += 1
            elif hand_end_match is not None:
                end_hand_number = hand_end_match.group("hand_number")
            # Lines containing these strings will be ignored
            elif any(
                i in entry
                for i in [
                    "The admin",
                    "joined",
                    "requested",
                    "canceled the seat",
                    "authenticated",
                    "quits",
                    "stand up",
                    "sit back",
                    "Remaining players",
                    "chooses",
                    "choose to not",
                    "Dead Small Blind",
                    "room ownership",
                    "IMPORTANT:",
                    "WARNING:",
                ]
            ):
                lines_ignored += 1
            else:
                if hand_number == "1":
                    post = re.match(post_regex, entry)
                    if post is not None:
                        post_type = post.group("type")
                        if post_type == "posts a small blind":
                            small_blind = float(post.group("amount"))
                            hands[game_number][SMALL_BLIND_AMOUNT] = small_blind
                        elif post_type == "posts a big blind":
                            big_blind = float(post.group("amount"))
                            hands[game_number][BIG_BLIND_AMOUNT] = big_blind
                        elif post_type == "posts an ante":
                            ante = float(post.group("amount"))
                            hands[game_number][ANTE_AMOUNT] = ante
                # Any line that has made it this far without being processed will be added to text
                # in the hands dictionary and be proccesed later
                hands[game_number][TEXT] = hands[game_number][TEXT] + "\n" + entry
                lines_saved += 1
        move(poker_now_file, csv_archive_dir)
        logging.info(f"[{table_name}] ***FINISHED HAND SEPERATION***")
        logging.info(f"[{table_name}] {lines_parsed} lines were parsed.")
        logging.info(f"[{table_name}] {lines_ignored} lines were ignored.")
        logging.info(f"[{table_name}] {lines_saved} lines were saved.")
        logging.info(f"[{table_name}] {hand_count} hands were seperated.")
        logging.info(
            f"[{table_name}] {round(lines_saved/hand_count, 2)} average number of lines per hand."
        )
        logging.info(
            f"[{table_name}][{perf_counter() - perf_start_1}] Performance counter for hand"
            "seperation."
        )
        logging.info(
            f"[{table_name}][{process_time() - proc_start_1}] Process time for hand seperation."
        )
        perf_start_2 = perf_counter()
        proc_start_2 = process_time()
        logging.info(f"[{table_name}] ***STARTING HAND PROCESSING***")
        unprocessed_count: int = 0
        # Now that we have all hands from all the files, use the hand number of the imported hands
        # to process them in sequential order. This is the place for processing the text of each
        # hand and look for player actions
        for game_number, hand in hands.items():
            hand_time = hand[DATETIME]
            tables[table_name][COUNT] += 1
            tables[table_name][LATEST] = hand_time
            tables[table_name][LAST] = game_number
            # initialize the OHH JSON populating as many fields as possible and initializing arrays.
            ohh = {
                SPEC_VERSION: spec_version,
                SITE_NAME: site_name,
                NETWORK_NAME: network_name,
                INTERNAL_VERSION: internal_version,
                GAME_NUMBER: game_number,
                START_DATE_UTC: hand[DATETIME],
                TABLE_NAME: hand[TABLE],
                GAME_TYPE: hand[GAME_TYPE],
                BET_LIMIT: {BET_TYPE: hand[BET_TYPE]},
                TABLE_SIZE: 10,
                CURRENCY: currency,
                DEALER_SEAT: 1,
                SMALL_BLIND_AMOUNT: hand[SMALL_BLIND_AMOUNT],
                BIG_BLIND_AMOUNT: hand[BIG_BLIND_AMOUNT],
                ANTE_AMOUNT: hand[ANTE_AMOUNT],
                HERO_PLAYER_ID: None,
                FLAGS: [],
                PLAYERS: [],
                ROUNDS: [],
                POTS: [],
            }
            # initialize variables, lists, and dictionaries for a new hand
            players = []
            player_ids = {}
            current_round = first_rounds[ohh[GAME_TYPE]]
            hero_playing: bool = bool(False)
            winners = []
            round_number: int = int(0)
            action_number: int = int(0)
            pot_number: int = int(0)
            total_pot = float(0.00)
            round_obj = {ID: 0, STREET: "", CARDS: [], ACTIONS: []}
            pot_obj = {}
            round_commit = {}
            hand_text: str = hand[TEXT]
            # Split the hand text and loop through it line by line looking for regular expressions
            # to parse.
            for line in hand_text.strip().splitlines(False):
                # The text match to look for a seated player and see their starting chip amount.
                seats = re.finditer(seats_regex, line)
                if seats is not None:
                    player_id: int = 0
                    for player in seats:
                        seat_number = int(player.group("seat"))
                        player_display: str = player.group("player")
                        device_id: str = player.group("device_id")
                        player_stack = float(player.group("amount"))
                        try:
                            name = aliases_names[player_display]
                            if device_id not in device_ids:
                                console.print(
                                    f"- The aliase [green]{player_display}[/green] is associated "
                                    f"with [blue]{name}[/blue] but the device "
                                    f"[magenta]{device_id}[/magenta] is not in the data model "
                                    f"for this player. Adding [magenta]{device_id}[/magenta] to the"
                                    f" data model for [blue]{name}[/blue]>>>"
                                )
                                players_map[name]["devices"].append(device_id)
                                device_ids = switch_key_and_values(
                                    players_map, "devices"
                                )
                        except KeyError:
                            if device_id not in device_ids:
                                name_input = console.input(
                                    f"\n- The alias [green]{player_display}[/green] and device "
                                    f"[magenta]{device_id}[/magenta] is not in the data model. Type"
                                    f" the name to associate with [green]{player_display}[/green] "
                                    "in the data model and press ENTER>>>"
                                )
                                try:
                                    players_map[name_input]["nicknames"].append(
                                        player_display
                                    )
                                    players_map[name_input]["devices"].append(device_id)
                                    device_ids = switch_key_and_values(
                                        players_map, "devices"
                                    )
                                    aliases_names = switch_key_and_values(
                                        players_map, "nicknames"
                                    )
                                except KeyError:
                                    players_map.update(
                                        {
                                            name_input: {
                                                "nicknames": [player_display],
                                                "devices": [device_id],
                                            }
                                        }
                                    )
                                    device_ids = switch_key_and_values(
                                        players_map, "devices"
                                    )
                                    aliases_names = switch_key_and_values(
                                        players_map, "nicknames"
                                    )
                            else:
                                name = device_ids[device_id]
                                bool_input = console.input(
                                    f"\n- The alias [green]{player_display}[/green] is not in "
                                    f"data model but the device [magenta]{device_id}[/magenta] has "
                                    f"been used by [blue]{name}[/blue]. If "
                                    f"[green]{player_display}[/green] is [blue]{name}[/blue] type "
                                    f"[yellow]'Y'[/yellow], if this is not [blue]{name}[/blue] "
                                    "[yellow]'N'[/yellow] and press ENTER>>>"
                                )
                                if bool_input == "Y":
                                    players_map[name]["nicknames"].append(
                                        player_display
                                    )
                                    aliases_names = switch_key_and_values(
                                        players_map, "nicknames"
                                    )
                                elif bool_input == "N":
                                    name_input = console.input(
                                        "\n[red]IMPORTANT:[/red] If different players are playing "
                                        "from the same device then there is the potential for "
                                        "cheating. Please type the name to associate alias "
                                        f"[green]{player_display}[/green] and press ENTER>>>"
                                    )
                                    try:
                                        players_map[name_input]["nicknames"].append(
                                            player_display
                                        )
                                        players_map[name_input]["devices"].append(
                                            device_id
                                        )
                                        device_ids = switch_key_and_values(
                                            players_map, "devices"
                                        )
                                        aliases_names = switch_key_and_values(
                                            players_map, "nicknames"
                                        )
                                    except KeyError:
                                        players_map.update(
                                            {
                                                name_input: {
                                                    "nicknames": [player_display],
                                                    "devices": [device_id],
                                                }
                                            }
                                        )
                            name = aliases_names[player_display]
                        players.append(
                            {
                                ID: player_id,
                                SEAT: seat_number,
                                NAME: name,
                                DISPLAY: player_display,
                                STARTING_STACK: player_stack,
                            }
                        )
                        name = aliases_names[player_display]
                        # If the player is the dealer, set the value of the dealers seat number in
                        # the ohh dictionary
                        if hand[DEALER_NAME] == player_display:
                            ohh[DEALER_SEAT] = seat_number
                        # If the player is the hero, set the value of players ID in the ohh
                        # dictionary.
                        if name == hero_name:
                            ohh[HERO_PLAYER_ID] = player_id
                            hero_playing: bool = True
                        # The OHH standard has a unique identifier for every player within the hand.
                        # This id is used to identify the player in all other locations of the hand
                        # history. Therefore, it is convenient to creat a dictionary to easily pull
                        # out the id of each player when needed.
                        player_ids[player_display] = player_id
                        player_id += 1
                        continue
                # the text to match for a post this also indicates that the dealing is happening and
                # we should move to the phase of assembling rounds of actions.
                post = re.match(post_regex, line)
                if post is not None:
                    player = post.group("player")
                    post_type = post.group("type")
                    amount = float(post.group("amount"))
                    all_in = post.group("all_in")
                    round_obj[ID] = round_number
                    round_obj[STREET] = current_round
                    action = {}
                    action[ACTION_NUMBER] = action_number
                    action[PLAYER_ID] = player_ids[player]
                    action[ACTION] = post_types[post_type]
                    # Poker now records the amounts associated with actions such as bets, raises,
                    # calls, and posting blinds as the the sum total of the current and all previous
                    # actions of the player during the round. However, the OHH standard requires the
                    # amount put in from the current action rather than the sum total of the round.
                    # This difference in accounting methods requires the amount commited by each
                    # player in the round to be rcorded in a dictionary
                    # {player1: amount, player2: amount, ...}.
                    # The amount the player has commited to the round can then be subtracted from
                    # the current amount to get the amount commited in the action, that OHH
                    # requires. There is one exception to this rule, in the case of a dead blind
                    # being posted by a player who missed the blinds. Posting a missed SB is
                    # considered a "dead" and is not considered to be a amount commited, but a
                    # missed BB is a "live"blind and should be added to the amount commited to the
                    # round.
                    if action[ACTION] != "Post Dead":
                        amount = round(amount - round_commit[player], 2)
                        round_commit[player] += amount
                    action[AMOUNT] = amount
                    if all_in is not None:
                        action[IS_ALL_IN] = True
                    else:
                        action[IS_ALL_IN] = False
                    round_obj[ACTIONS].append(action)
                    total_pot += amount
                    action_number += 1
                    continue
                # look for round markers note that cards dealt are melded together with opening
                # round and do not necessarily mark a new round
                round_marker = re.match(round_regex, line)
                cards_match = re.search(cards_regex, line)
                if round_marker is not None:
                    label = round_marker.group("street")
                    if label == PLAYER_STACKS:
                        action_number: int = 0
                        round_obj[ID] = round_number
                        current_round = first_rounds[ohh[GAME_TYPE]]
                        round_obj[STREET] = current_round
                        action = {}
                        round_commit = {}
                        for p in player_ids:
                            round_commit[p] = float(0)
                    elif label in make_new_round:
                        # Make new round we need to add current round object to the OHH JSON and
                        # make a clean one increment round number and reset action number
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
                            for card in cards.split(", "):
                                round_obj[CARDS].append(card)
                        else:
                            continue
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
                    action[ACTION] = "Shows Cards"
                    action[CARDS] = []
                    for card in cards.split(", "):
                        action[CARDS].append(card)
                    action[IS_ALL_IN] = False
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
                    for card in cards.split(", "):
                        action[CARDS].append(card)
                    action[IS_ALL_IN] = False
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
                    action[AMOUNT] = 0.00
                    action[IS_ALL_IN] = False
                    round_obj[ACTIONS].append(action)
                    action_number += 1
                    continue
                bet_action = re.match(bet_action_regex, line)
                if bet_action is not None:
                    player = bet_action.group("player")
                    does = bet_action.group("player_action")
                    amount = float(bet_action.group("amount"))
                    all_in = bet_action.group("all_in")
                    action = {}
                    action[ACTION_NUMBER] = action_number
                    action[PLAYER_ID] = player_ids[player]
                    action[ACTION] = verb_to_action[does]
                    if does in ("raises", "calls"):
                        amount = round(amount - round_commit[player], 2)
                    action[AMOUNT] = amount
                    round_commit[player] += amount
                    total_pot += amount
                    if all_in is not None:
                        action[IS_ALL_IN] = True
                    else:
                        action[IS_ALL_IN] = False
                    round_obj[ACTIONS].append(action)
                    action_number += 1
                    continue
                uncalled_bet_match = re.match(uncalled_regex, line)
                if uncalled_bet_match is not None:
                    amount = round(float(uncalled_bet_match.group("amount")), 2)
                    total_pot -= amount
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
                    continue
                # Hands with the option to run it twice there are several lines in the
                # csv file that will contain the string "run it twice" but the only line
                # that will have made it this far will indicat that all players approved.
                if "run it twice" in line:
                    ohh[FLAGS].append("Run_It_Twice")
                    continue
                unprocessed_count += 1
                logging.debug(
                    f"[{table_name}][{game_number}] '{line}' was not processed."
                )

            for pot_number, pot in pot_obj.items():
                amt = round(pot[AMOUNT], 2)
                rake = pot[RAKE]
                potObj = {NUMBER: pot_number, AMOUNT: amt, RAKE: rake, PLAYER_WINS: []}
                for player_id in pot[PLAYER_WINS]:
                    win_amount = round(pot[PLAYER_WINS][player_id][WIN_AMOUNT], 2)
                    rake_contribution = pot[PLAYER_WINS][player_id][CONTRIBUTED_RAKE]
                    player_win_obj = {
                        PLAYER_ID: player_id,
                        WIN_AMOUNT: win_amount,
                        CONTRIBUTED_RAKE: rake_contribution,
                    }
                    potObj[PLAYER_WINS].append(player_win_obj)
                if round(pot[AMOUNT], 2) != round(total_pot, 2):
                    logging.debug(
                        f"[{table_name}][{game_number}] Calculated pot ({round(total_pot, 2)})"
                        f"does not equal collected pot ({round(pot[AMOUNT], 2)})"
                    )

                ohh[POTS].append(potObj)
            if hero_playing is False:
                ohh[FLAGS].append("Observed")
            ohh[PLAYERS] = players
            ohh[ROUNDS].append(round_obj)
            table.append(ohh)
        logging.info(f"[{table_name}] ***FINISHED HAND PARSING***")
        logging.info(f"[{table_name}] {unprocessed_count} lines were not parsed.")
        ohh_directory = Path("OpenHandHistory")
        with open(
            ohh_directory / poker_now_file.with_suffix(".ohh").name,
            "w",
            encoding="utf-8",
        ) as f:
            for ohh in table:
                wrapped_ohh = {}
                wrapped_ohh[OHH] = ohh
                f.write(json.dumps(wrapped_ohh, indent=4))
                f.write("\n")
                f.write("\n")
        logging.info(
            f"[{table_name}][{perf_counter() - perf_start_2}] Performance counter for hand parsing."
        )
        logging.info(
            f"[{table_name}][{process_time() - proc_start_2}] Process time for hand parsing."
        )
        percent_complete = round(
            ((csv_file_list.index(poker_now_file) + 1) / len(csv_file_list)) * 100, 2
        )
        console.print(
            f"Completed processing [magenta]{csv_file_list.index(poker_now_file) + 1}[/magenta] "
            f"of [magenta]{len(csv_file_list)}[/magenta] files, "
            f"[cyan]{percent_complete}%[/cyan] "
            f"complete. Time to process table [green]{table_name}[/green]"
        )
        console.print(
            f"[blue]{round(perf_counter() - perf_start_2, 6)} sec[/blue] Performance counter."
        )
        console.print(f"[blue]{process_time() - proc_start_2} sec[/blue] Process time.")
save_name_map(name_map_path, players_map)
logging.info(
    f"[ALL][{perf_counter() - timer_perf_start}] Performance counter for all hands."
)
logging.info(f"[ALL][{process_time() - timer_proc_start}] Process time for all hands.")
console.print(
    f"[cyan]{round(perf_counter() - timer_perf_start, 2)} sec[/cyan] Performance counter for all "
    "hands."
)
console.print(
    f"[cyan]{process_time() - timer_proc_start} sec[/cyan] Process time for all hands."
)
# end of code
# *************************************************************************************************
