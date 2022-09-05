# PokerNowToOHH.py
# Mark Sudduth sudduth.mark@gmail.com

"""
***********************************************************************************************************
WHAT THIS DOES

goal of this program is to process Poker Mavens hand history text and convert to JSON format
that matches the Standardized hand History format specified by PokerTracker and documented here:
https://hh-specs.handhistory.org/

To do this we will take the logs and first break it up into hand by hand

Then we can loop through each hand, and convert to the JSON format specified.
Finally, we output the new JSON.

KEY ASSUMPTIONS

Working with Ring games only, not tournaments

Change Log
***********************************************************************************************************
"""
"""
***********************************************************************************************************
MODULES
"""
# %%
import configparser
import csv
import os
import re
from tkinter import LAST

"""
end modules
***********************************************************************************************************
"""
"""
***********************************************************************************************************
CONSTANTS
"""
# OHH field name and known constant values
OPTIONS_FILE = "convertPokerNow.ini"
DATETIME = "datetime"
DEALER_NAME = "dealer_name"
TEXT = "text"
COUNT = "count"
LATEST = "latest"
TABLE = "table"
OHH = "ohh"
SPEC_VERSION = "spec_version"
SITE_NAME = "site_name"
NETWORK_NAME = "network_name"
INTERNAL_VERSION = "internal_version"
HH_VERSION = "hh_version"
GAME_NUMBER = "game_number"
START_DATE_UTC = "start_date_utc"
TABLE_NAME = "table_name"
TABLE_HANDLE = "table_handle"
GAME_TYPE = "game_type"
BET_TYPE = "bet_type"
BET_LIMIT = "bet_limit"
TABLE_SIZE = "table_size"
CURRENCY = "currency"
DEALER_SEAT = "dealer_seat"
SMALL_BLIND = "small_blind"
BIG_BLIND = "big_blind"
ANTE = "ante"
FLAGS = "flags"
PLAYERS = "players"
ID = "id"
SEAT = "seat"
DISPLAY = "display"
NAME = "name"
STARTING_STACK = "starting_stack"
ROUNDS = "rounds"
CARDS = "cards"
ACTIONS = "actions"
POTS = "pots"
# constants for processing INI and setting configurable defaults
HERO_NAME = "HeroName"
TIMEZONE = "TimeZone"
CURRENCY = "Currency"
# end script level constants

"""
configurable constants
these are constants that are meant to be configurable - they could be edited here,
or specified in a configuration file that is external to this script and checked for at run time
"""
DEFAULT_CONFIG = {
    HERO_NAME: "hero",
    TIMEZONE: "America/New York",
    CURRENCY: "USD",
}
"""
end constants
***********************************************************************************************************"""
"""
***********************************************************************************************************
DATA STRUCTURES
"""
hands = {}
"""
the hands dictionary
    - display
        - KEY - string - hand number
        - DATETIME - datetime - timestamp for the hand
        - TABLE - string - table where the hand happened
        - TEXT  - string - full text of hand, with newlines
"""
tables = {}
"""
the tables dictionary
    - structure
        - KEY - string - table name as found in log
        - COUNT - integer - number of hands processed for table
        - LATEST - datetime - the latest time stamp for a hand processed for this table
        - LAST - string - hand number for the latest hand processed for this table
            - LAST and LATEST are used to mark the "end" activity of players standing up
              they represent the last seen hand at the table from the processed logs
        - HANDLE - absolute value of the hash value of the name of the table, as a string
        - OHH - list of hand histories, each in JSON following the OHH format
"""

"""
Lookup Tables
"""
structures = {"Pot Limit": "PL", "No Limit": "NL"}

games = {
    "Texas Hold'em": "Holdem",
    "Omaha Hi/Lo 8 or Better": "OmahaHiLo",
    "Omaha High": "Omaha",
}

"""
end of data structures
*************************************************************************************************************
"""
"""
*************************************************************************************************************
FUNCTIONS
"""


def createConfig(path):
    """
    Create a config file
    """
    config = configparser.ConfigParser()
    config.add_section("HH Constants")
    config.set("HH Constants", "spec_version", "1.2.2")
    config.set("HH Constants", "internal_version", "1.2.2")
    config.set("HH Constants", "network_name", "PokerStars")
    config.set("HH Constants", "site_name", "PokerStars")
    config.set("HH Constants", "currency", "USD")

    with open(path, "w") as config_file:
        config.write(config_file)


def getConfig(path):
    """
    Returns the config object
    """
    if not os.path.exists(path):
        createConfig(path)

    config = configparser.ConfigParser()
    config.read(path)
    return config


def getSetting(path, section, setting):
    """
    Get setting
    """
    config = getConfig(path)
    value = config.get(section, setting)
    return value


def csv_reader(file_obj, rows, fields):
    """
    Read a CSV file
    """
    reader = csv.reader(file_obj)
    fields = next(reader)
    for row in reader:
        subs_dict = {"♥": "h", "♠": "s", "♦": "d", "♣": "c"}
        subs_regex = re.compile("|".join(subs_dict.keys()))
        row = [subs_regex.sub(lambda match: subs_dict[match.group(0)], i) for i in row]
        rows.append(row)
    return rows.reverse()


"""
end of functions
***********************************************************************************************************
"""
"""
***********************************************************************************************************
CODE
"""

# config=configparser.ConfigParser(defaults=DEFAULT_CONFIG)
# try:
#     with open(OPTIONS_FILE, encoding="utf-8") as optionsFile:
#         config.read_file(optionsFile)
# except IOError:
#     optionInformation = "Could not read " + OPTIONS_FILE + ". Using default values from script."

"""
process each file listed on the command line
first loop through is just to parse and get each hand separated, and get basic hand
info into the hands dictionary
basic hand info is hand number, local hand number, hand time, and table
everything else goes into TEXT
"""
csv_directory = os.getcwd() + "\PokerNowHandHistory"
csv_file_list = os.listdir(csv_directory)
csv_path = csv_directory + "\\" + "poker_now_log_pgl0GqBGvOdxwhT2K8IoVNxXL.csv"

specVersion = getSetting("config.ini", "HH Constants", "spec_version")
internalVersion = getSetting("config.ini", "HH Constants", "internal_version")
networkName = getSetting("config.ini", "HH Constants", "network_name")
siteName = getSetting("config.ini", "HH Constants", "site_name")
currency = getSetting("config.ini", "HH Constants", "currency")

rows = []
fields = []
with open(
    csv_directory + "\\" + "poker_now_log_pgl0GqBGvOdxwhT2K8IoVNxXL.csv",
    encoding="UTF-8",
) as f:
    x = csv_reader(f, rows, fields)
    table = re.search(r"^.*poker_now_log_(?P<table_name>.*)\.csv$", csv_path)
    tableName = table.group("table_name")
    handNumber = "0"
    for i in range(len(rows)):
        row = rows[i][0]
        matches = re.search(
            r'^-- starting hand #(?P<game_number>\d+)  \((?P<bet_type>\w*\s*Limit) (?P<game_type>.+)\) \(dealer: "(?P<dealer_name>.+) @ .+"\) --',
            rows[i][0],
        )
        if matches != None:
            handNumber = matches.group("game_number")
            betType = matches.group("bet_type")
            gameType = matches.group("game_type")
            dealerName = matches.group("dealer_name")
            matches = re.search(r"(?P<start_date_utc>.+\.\d+Z)", rows[i][1])
            handTime = matches.group("start_date_utc")
            hands[handNumber] = {
                DATETIME: handTime,
                BET_TYPE: betType,
                GAME_TYPE: gameType,
                DEALER_NAME: dealerName,
                TABLE_NAME: tableName,
                TEXT: "",
            }
            hands[handNumber][GAME_TYPE] = games[gameType]
            hands[handNumber][BET_TYPE] = structures[betType]
            i += 1
            while re.search(r"-- ending hand #\d+ --", rows[i][0]) == None:
                if not tableName in tables:
                    tables[tableName] = {COUNT: 0, LATEST: "", OHH: []}
                hands[handNumber][TEXT] = hands[handNumber][TEXT] + "/n" + rows[i][0]
                i += 1
        else:
            i += 1
handNumber = ""
# now that we have all hands from all the files,
# use the timestamps of the imported hands to process them in chronological order
# this is the place for processing the text of each hand and look for player actions

for handNumber in hands.keys():
    table = hands[handNumber][TABLE_NAME]
    tables[table][COUNT] += 1
    tables[table][LATEST] = handTime
    tables[table][LAST] = handNumber

    ohh = {
        SPEC_VERSION: specVersion,
        SITE_NAME: siteName,
        NETWORK_NAME: networkName,
        INTERNAL_VERSION: internalVersion,
        GAME_NUMBER: handNumber,
        START_DATE_UTC: hands[handNumber][DATETIME],
        TABLE_NAME: tableName,
        GAME_TYPE: hands[handNumber][GAME_TYPE],
        BET_LIMIT: {},
        TABLE_SIZE: 10,
        CURRENCY: currency,
        DEALER_SEAT: 1,
        SMALL_BLIND: 0,
        BIG_BLIND: 0,
        ANTE: 0,
        FLAGS: [],
        PLAYERS: [],
        ROUNDS: [],
        POTS: [],
    }
    players = []
    playerIds = {}
    # Set some Boolean flags to indicate what we already know about the Hand
    # For instance processedSeats is set to False
    # but once we know we have seenSeats we can assume we are either in or past that
    # part of chat history and do not need to do text searches for Site, Game
    # Also a placeholder for current Round
    # processedSeats is a marker for the parsing logic to indicate we hace already
    # encountered the players in the hands and accounted for them
    # similar markers are used for cardsDealt and currentRound
    # the roundCommit dictionary keeps track of what players have already committed to the pot
    # so that re-raises can account for that in the raise action
    processedSeats = False
    cardsDealt = False
    currentRound = None
    heroPlaying = False
    winners = []
    roundNumber = 0
    actionNumber = 0
    rounds = {CARDS: [], ACTIONS: []}
    pots = {}
    roundCommit = {}
    for line in hands[handNumber][TEXT].splitlines():
        matches = re.findall(r"#(\d+) \"(.+?) @ .+?\((\d+\.\d{2})", line)
        if matches != None:
            i=0
            for player in matches:
                seatNumber = int(player[0])
                playerDisplay = player[1]
                playerStack = float(player[2])
                players.append(
                    {
                        ID: i,
                        SEAT: seatNumber,
                        NAME: "",
                        DISPLAY: playerDisplay,
                        STARTING_STACK: playerStack,
                    }
                )
                i+=1

        print(line)
    ohh[PLAYERS]=players
    print(ohh)
"""
end of code
***********************************************************************************************************
"""

# print(x)
# print(hands)


# %%
