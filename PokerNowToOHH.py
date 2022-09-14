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
import configparser
import csv
import json
import os
import re

# end modules
# **************************************************************************************************

# **************************************************************************************************
# CONSTANTS

OPTIONS_FILE = "Config.ini"
TEXT = "text"
COUNT = "count"
LATEST = "latest"
LAST = "last"
OHH = "ohh"
HH_VERSION = "hh_version"
SHOW_DOWN = "Show Down"
PLAYER_STACKS = "Player stacks"


# OHH field name and known constant values
DATETIME = "datetime"
DEALER_NAME = "dealer_name"
TABLE = "table"
SPEC_VERSION = "spec_version"
SITE_NAME = "site_name"
NETWORK_NAME = "network_name"
INTERNAL_VERSION = "internal_version"
GAME_NUMBER = "game_number"
START_DATE_UTC = "start_date_utc"
TABLE_NAME = "table_name"
TABLE_HANDLE = "table_handle"
GAME_TYPE = "game_type"
BET_TYPE = "bet_type"
BET_LIMIT = "bet_limit"
BET_CAP = "bet_cap"
TABLE_SIZE = "table_size"
CURRENCY = "currency"
DEALER_SEAT = "dealer_seat"
SMALL_BLIND = "small_blind"
BIG_BLIND = "big_blind"
ANTE = "ante"
HERO = "hero_player_id"
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
ACTION = "action"
POTS = "pots"
STREET = "street"
ACTION_NUMBER = "action_number"
PLAYER_ID = "player_id"
AMOUNT = "amount"
IS_ALL_IN = "is_allin"
NUMBER = "number"
RAKE = "rake"
PLAYER_WINS = "player_wins"
WIN_AMOUNT = "win_amount"
CONTRIBUTED_RAKE = "contributed_rake"

# constants for processing INI and setting configurable defaults
HERO_NAME = "HeroName"
TIMEZONE = "TimeZone"
CURRENCY_ABBR = "CurrencyAbbr"
PREFIX = "OutputPrefix"
# end script level constants

# configurable constants
DEFAULT_CONFIG = {
    HERO_NAME: "hero",
    TIMEZONE: "America/New York",
    CURRENCY: "USD",
}
"""
these are constants that are meant to be configurable - they could be edited here,
or specified in a configuration file that is external to this script and checked for at run time
"""
# end constants
# **************************************************************************************************

# **************************************************************************************************
# DATA STRUCTURES

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


# Lookup Table

structures = {"Pot Limit": "PL", "No Limit": "NL"}

games = {
    "Texas Hold'em": "Holdem",
    "Omaha Hi/Lo 8 or Better": "OmahaHiLo",
    "Omaha High": "Omaha",
}

firstRounds = {
    "Holdem": "Preflop",
    "Omaha": "Preflop",
    "OmahaHiLo": "Preflop",
}

makeNewRound = {
    "Player stacks": "Preflop",
    "Flop": "Flop",
    "Turn": "Turn",
    "River": "River",
    "Show Down": "Showdown",
}

postTypes = {
    "posts an ante": "Post Ante",
    "posts a big blind": "Post BB",
    "posts a small blind": "Post SB",
    "posts a straddle": "Straddle",
}

verbToAction = {
    "bets": "Bet",
    "calls": "Call",
    "raises": "Raise",
    "folds": "Fold",
    "checks": "Check",
}


# end of data structures
# **************************************************************************************************

# **************************************************************************************************
# FUNCTIONS


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
        subs_regex = re.compile("|".join(subs_dict.keys()))
        row = [subs_regex.sub(lambda match: subs_dict[match.group(0)], i) for i in row]
        rows.append(row)
    return rows.reverse()


# end of functions
# **************************************************************************************************


# **************************************************************************************************
# CODE


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
heroPlayer = getSetting("config.ini", "HH Constants", "hero")

rows = []
fields = []
dealerNameList = []

table_regex = re.compile(r"^.*poker_now_log_(?P<table_name>.*)\.csv$")
blind_regex = re.compile(
    r"The game's (?P<blind_type>.+) was changed from \d+\.\d+ to (?P<amount>\d+.\d+)"
)
start_regex = re.compile(
    r'^-- starting hand #(?P<game_number>\d+)  \((?P<bet_type>\w*\s*Limit) (?P<game_type>.+)\) \(dealer: "(?P<dealer_name>.+) @ .+"\) --'
)
hand_time_regex = re.compile(r"(?P<start_date_utc>.+\.\d+Z)")
seats_regex = re.compile(
    r"#(?P<seat>\d+) \"(?P<player>.+?) @ (?P<deviceID>.+?)\" \((?P<amount>[\d.]+)"
)
post_regex = re.compile(
    r'"(?P<player>.+) @ .+" (?P<type>posts a .+) of (?P<amount>[\d.]+)'
)
round_regex = re.compile(r"(?P<street>^[\w ]+):.+")
cards_regex = re.compile(r"\[(?P<cards>.+)\]")
addon_regex = re.compile(r".+ \"(?P<player>\w+) @ .+\" adding (?P<amount>[\d.]+)")
hero_hand_regex = re.compile(r"Your hand is (?P<cards>.+)")
non_bet_action_regex = re.compile(
    r"\"(?P<player>.+) @ (\w+)\" (?P<player_action>\w+(?![ a-z]+[ \d.]+))"
)
bet_action_regex = re.compile(
    r"\"(?P<player>.+) @ (\w+)\" (?!collected)(?!shows)(?P<player_action>\w+) [a-z]*\s*(?P<amount>[\d.]+)\s*(?P<all_in>[a-z ]+)*"
)
show_regex = re.compile(
    r"\"(?P<player>.+) @ (\w+)\" (?P<player_action>\w+) a (?P<cards>\w{2}, \w{2})"
)
winner_regex = re.compile(
    r"\"(?P<player>.+) @ (\w+)\" (?P<player_action>collected) (?P<amount>[\d.]+)"
)

with open("name-map.json", "r") as read_file:
    data = json.load(read_file)
    names = {}
    for key, values in data.items():
        for value in values:
            names[value] = key


with open(
    csv_directory + "\\" + "poker_now_log_pgl0GqBGvOdxwhT2K8IoVNxXL.csv",
    encoding="UTF-8",
) as f:
    x = csv_reader(f, rows, fields)
    table_name = re.match(table_regex, csv_path)
    tableName = table_name.group("table_name")
    bigBlind = 0.20
    smallBlind = 0.10
    ante = 0.00
    handNumber = "0"
    for i in range(len(rows)):
        row = rows[i][0]
        blinds = re.match(blind_regex, row)
        if blinds != None:
            blindType = blinds.group("blind_type")
            blindAmount = float(blinds.group("amount"))
            if blindType == "big blind":
                bigBlind = blindAmount
            elif blindType == "small blind":
                smallBlind = blindAmount
            elif blindType == "ante":
                ante = blindAmount
            continue

        hand_start = re.match(
            start_regex,
            row,
        )
        if hand_start != None:
            handNumber = hand_start.group("game_number")
            betType = hand_start.group("bet_type")
            gameType = hand_start.group("game_type")
            dealerName = hand_start.group("dealer_name")
            hand_time = re.match(hand_time_regex, rows[i][1])
            handTime = hand_time.group("start_date_utc")
            hands[handNumber] = {
                DATETIME: handTime,
                BET_TYPE: betType,
                GAME_TYPE: gameType,
                DEALER_NAME: dealerName,
                TABLE: tableName,
                BIG_BLIND: bigBlind,
                SMALL_BLIND: smallBlind,
                ANTE: ante,
                TEXT: "",
            }
            hands[handNumber][BET_TYPE] = structures[betType]
            hands[handNumber][GAME_TYPE] = games[gameType]
            i += 1

            # while re.search(r"-- ending hand #\d+ --", rows[i][0]) == None:
            while re.match(start_regex, rows[i][0]) == None:
                if not tableName in tables:
                    tables[tableName] = {COUNT: 0, LATEST: "", OHH: []}
                hands[handNumber][TEXT] = hands[handNumber][TEXT] + "\n" + rows[i][0]
                if i == len(rows) - 1:
                    break
                i += 1
        else:
            i += 1
handNumber = ""
# now that we have all hands from all the files,
# use the timestamps of the imported hands to process them in chronological order
# this is the place for processing the text of each hand and look for player actions

for handNumber in hands.keys():
    table = hands[handNumber][TABLE]
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
        TABLE_NAME: hands[handNumber][TABLE],
        GAME_TYPE: hands[handNumber][GAME_TYPE],
        BET_LIMIT: {BET_CAP: 0.00, BET_TYPE: hands[handNumber][BET_TYPE]},
        TABLE_SIZE: 10,
        CURRENCY: currency,
        DEALER_SEAT: 1,
        SMALL_BLIND: hands[handNumber][SMALL_BLIND],
        BIG_BLIND: hands[handNumber][BIG_BLIND],
        ANTE: hands[handNumber][ANTE],
        HERO: 0,
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
    showDown = False
    heroPlaying = False
    winners = []
    roundNumber = 0
    actionNumber = 0
    potNumber = 0
    rounds = {ID: 0, STREET: "", CARDS: [], ACTIONS: []}
    pots = {}
    roundCommit = {}
    for line in hands[handNumber][TEXT].strip().splitlines(False):
        # the text match to look for a seated player and see their chip amount
        # specifically for the hero player, make sure that the player is not
        # waiting or sitting out, and then mark the hand appropriately
        # for the ID for Hero or the Flag for Observed
        seats = re.finditer(seats_regex, line)
        if seats != None:
            i = 0
            for player in seats:
                seatNumber = int(player.group("seat"))
                playerDisplay = player.group("player")
                playerStack = float(player.group("amount"))
                players.append(
                    {
                        ID: i,
                        SEAT: seatNumber,
                        NAME: names[playerDisplay],
                        DISPLAY: playerDisplay,
                        STARTING_STACK: playerStack,
                    }
                )
                playerIds[playerDisplay] = i
                if hands[handNumber][DEALER_NAME] == playerDisplay:
                    ohh[DEALER_SEAT] = seatNumber
                    # print(ohh[DEALER_SEAT])
                if names[playerDisplay] == heroPlayer:
                    ohh[HERO] = i
                    hero = playerDisplay
                    heroPlaying = True
                processedSeats = True
                i += 1
        # the text to match for a post
        # this also indicates that the dealing is happening and we should
        # move to the phase of assembling rounds of actions
        # currently do not use the OHH action of "Post Extra Blind" or "Post Dead"
        # TODO test scenarios with dead blind or additional blind
        # TODO Check if an allin post results in comment on the post line itself
        post = re.match(post_regex, line)
        if post is not None:
            player = post.group("player")
            postType = post.group("type")
            amount = float(post.group("amount"))
            # ohh[SMALL_BLIND] = float(post.group('small_blind'))
            # bigBlind = re.search(
            #     r'".+ @ .+" (posts a big blind of (?P<big_blind>\d+.\d+)', line)
            # if (bigBlind!=None):
            #     ohh[BIG_BLIND] = float(bigBlind.group('big_blind'))
            cardsDealt = True
            if currentRound is not None:
                # actionNumber = 0
                rounds[ID] = roundNumber
                currentRound = firstRounds[ohh[GAME_TYPE]]
                rounds[STREET] = currentRound
                roundCommit[player] = amount
            action = {}
            action[ACTION_NUMBER] = actionNumber
            action[PLAYER_ID] = playerIds[player]
            action[ACTION] = postTypes[postType]
            action[AMOUNT] = amount
            rounds[ACTIONS].append(action)
            actionNumber += 1
        # look for round markers
        # note that cards dealt are melded together with opening round and do not necessarily mark a new round
        roundMarker = re.match(round_regex, line)
        Cards = re.search(cards_regex, line)

        if roundMarker is not None:
            label = roundMarker.group("street")

            if label == PLAYER_STACKS:
                if currentRound is None:
                    actionNumber = 0
                    rounds[ID] = roundNumber
                    currentRound = firstRounds[ohh[GAME_TYPE]]
                    rounds[STREET] = currentRound
                    action = {}
                    roundCommit = {}
                    for p in playerIds:
                        roundCommit[p] = 0
                continue
            elif label in makeNewRound:
                # cards = Cards.group("cards")
                # make new round
                # we need to add current round object to the OHH JSON
                # and make a clean one
                # increment round number and reset action number
                ohh[ROUNDS].append(rounds)
                rounds = {}
                roundNumber += 1
                actionNumber = 0
                currentRound = makeNewRound[label]
                rounds[ID] = roundNumber
                rounds[STREET] = currentRound
                rounds[CARDS] = []
                rounds[ACTIONS] = []
                roundCommit = {}
                for p in playerIds:
                    roundCommit[p] = 0
                if Cards is not None:
                    cards = Cards.group("cards")
                    for card in cards.split():
                        rounds[CARDS].append(card)
                else:
                    continue
        showHand = re.search(show_regex, line)

        if showHand != None:
            player = showHand.group("player")
            does = showHand.group("player_action")
            cards = showHand.group("cards")
            if currentRound != SHOW_DOWN:
                ohh[ROUNDS].append(rounds)
                rounds = {}
                roundNumber += 1
                actionNumber = 0
                currentRound = SHOW_DOWN
                rounds[ID] = roundNumber
                rounds[STREET] = makeNewRound[SHOW_DOWN]
                rounds[ACTIONS] = []
            action = {}
            action[ACTION_NUMBER] = actionNumber
            action[PLAYER_ID] = playerIds[player]
            action[ACTION] = "Shows Hand"
            action[CARDS] = []
            for card in cards.split():
                action[CARDS].append(card)
            rounds[ACTIONS].append(action)
            actionNumber += 1
            roundCommit = {}
            for p in playerIds:
                roundCommit[p] = 0
            continue
        # the text to match for an add on
        addOn = re.match(addon_regex, line)

        if addOn is not None:
            player = addOn.group("player")
            additional = float(addOn.group("amount"))
            if currentRound is not None and player in playerIds:
                action = {}
                action[ACTION_NUMBER] = actionNumber
                action[PLAYER_ID] = playerIds[player]
                action[AMOUNT] = additional
                action[ACTION] = "Added Chips"
                rounds[ACTIONS].append(action)
                actionNumber += 1
            continue
        # the text to match for cards dealt
        heroHand = re.match(hero_hand_regex, line)
        if heroHand is not None:
            cards = heroHand.group("cards")
            action = {}
            action[ACTION_NUMBER] = actionNumber
            action[PLAYER_ID] = ohh[HERO]
            action[ACTION] = "Dealt Cards"
            action[CARDS] = []
            for card in cards.split():
                action[CARDS].append(card)
            rounds[ACTIONS].append(action)
            actionNumber += 1
            continue
        nonBetAction = re.match(non_bet_action_regex, line)
        if nonBetAction is not None:
            player = nonBetAction.group("player")
            does = nonBetAction.group("player_action")
            action = {}
            action[ACTION_NUMBER] = actionNumber
            action[PLAYER_ID] = playerIds[player]
            action[ACTION] = verbToAction[does]
            rounds[ACTIONS].append(action)
            actionNumber += 1
            continue

        betAction = re.match(bet_action_regex, line)
        if betAction is not None:
            player = betAction.group("player")
            does = betAction.group("player_action")
            amount = float(betAction.group("amount"))
            allIn = betAction.group("all_in")
            action = {}
            action[ACTION_NUMBER] = actionNumber
            action[PLAYER_ID] = playerIds[player]
            action[ACTION] = verbToAction[does]
            if does == "raises" or does == "calls":
                amount = round(amount - roundCommit[player], 2)
            action[AMOUNT] = amount
            roundCommit[player] += amount
            if allIn != None:
                action[IS_ALL_IN] = True
            rounds[ACTIONS].append(action)
            actionNumber += 1
            continue
        winner = re.match(winner_regex, line)
        if winner is not None:
            player = winner.group("player")
            does = winner.group("player_action")
            amount = float(winner.group("amount"))
            playerId = playerIds[player]
            winners.append(playerId)
            if not potNumber in pots:
                pots[potNumber] = {
                    NUMBER: potNumber,
                    AMOUNT: 0.00,
                    RAKE: 0.00,
                    PLAYER_WINS: {},
                }
            if not playerId in pots[potNumber][PLAYER_WINS]:
                pots[potNumber][PLAYER_WINS][playerId] = {
                    PLAYER_ID: playerId,
                    WIN_AMOUNT: 0.00,
                    CONTRIBUTED_RAKE: 0.00,
                }
            pots[potNumber][AMOUNT] += amount
            pots[potNumber][PLAYER_WINS][playerId][WIN_AMOUNT] += amount

    for potNumber in pots.keys():
        amt = pots[potNumber][AMOUNT]
        rake = pots[potNumber][RAKE]
        potObj = {NUMBER: potNumber, AMOUNT: amt, RAKE: rake, PLAYER_WINS: []}
        for playerId in pots[potNumber][PLAYER_WINS]:
            winAmount = pots[potNumber][PLAYER_WINS][playerId][WIN_AMOUNT]
            rakeContribution = pots[potNumber][PLAYER_WINS][playerId][CONTRIBUTED_RAKE]
            playerWinObj = {
                PLAYER_ID: playerId,
                WIN_AMOUNT: winAmount,
                CONTRIBUTED_RAKE: rakeContribution,
            }
            potObj[PLAYER_WINS].append(playerWinObj)
        ohh[POTS].append(potObj)

        # print(line)
        # print(hands[handNumber][TEXT].strip().splitlines(False))
    ohh[PLAYERS] = players
    ohh[ROUNDS].append(rounds)
    tables[table][OHH].append(ohh)

    # print(ohh)
ohh_directory = os.getcwd() + "\OpenHandHistory"
for table in tables.keys():
    with open(
        ohh_directory + "\\" + "poker_now_log_pgl0GqBGvOdxwhT2K8IoVNxXL.ohh", "w"
    ) as f:
        for ohh in tables[table][OHH]:
            wrapped_ohh = {}
            wrapped_ohh[OHH] = ohh
            f.write(json.dumps(wrapped_ohh, indent=4))
            f.write("\n")
            f.write("\n")

# end of code
# ***********************************************************************************************************

# print(x)
# print(hands)


# %%
