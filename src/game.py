"""_summary_.

Returns:
    _type_: _description_
"""
import csv
import logging
import re
from pathlib import Path
from typing import Tuple

from attrs import Factory, asdict, define
from rich.console import Console

from action import Action
from ohh import Ohh, hero_name
from player_wins import PlayerWins
from pot import Pot
from rounds import Round

DEALER_SEAT = 'dealer_seat'
# LOOKUP TABLE
structures = {'Pot Limit': 'PL', 'No Limit': 'NL'}

games = {
    "Texas Hold'em": 'Holdem',
    'Omaha Hi/Lo 8 or Better': 'OmahaHiLo',
    'Omaha Hi': 'Omaha',
}

first_rounds = {
    'Holdem': 'Preflop',
    'Omaha': 'Preflop',
    'OmahaHiLo': 'Preflop',
}

make_new_round = {
    'Player stacks': 'Preflop',
    'Flop': 'Flop',
    'Flop (second run)': 'Flop',
    'Turn': 'Turn',
    'Turn (second run)': 'Turn',
    'River': 'River',
    'River (second run)': 'River',
    'shows': 'Showdown',
}

post_types = {
    'posts an ante': 'Post Ante',
    'posts a big blind': 'Post BB',
    'posts a small blind': 'Post SB',
    'posts a straddle': 'Straddle',
    'posts a missing small blind': 'Post Dead',
    'posts a missed big blind': 'Post Extra Blind',
}

verb_to_action = {
    'bets': 'Bet',
    'calls': 'Call',
    'raises': 'Raise',
    'folds': 'Fold',
    'checks': 'Check',
}

subs_suits = {
    '10♥': 'Th',
    '10♠': 'Ts',
    '10♦': 'Td',
    '10♣': 'Tc',
    '♥': 'h',
    '♠': 's',
    '♦': 'd',
    '♣': 'c',
}

console = Console()

csv_dir = Path('PokerNowHandHistory/Archive')
csv_files = [child for child in csv_dir.iterdir() if child.suffix == '.csv']
patterns = {
    'name': r'\"(?P<player>.+?) @ (?P<device_id>[-\w]+)\"',
    'amount': r'\s*(?P<amount>\d+\.\d{2}|\d+)',
    'hand_num': r'(?P<hand_number>\d+)',
    'cards': r'(?P<cards>[\dAKQJTshcd, ]+)',
}
table_regex = re.compile('^.*poker_now_log_(?P<table_name>.*).csv$')
blind_regex = re.compile(
    r'The game\'s (?P<blind_type>.+) was changed from (\d+\.\d{2}|\d+)' +
    ' to{amount}'.format(**patterns),
)
start_regex = re.compile(
    (r'-- starting hand #{hand_num}.+\((?P<bet_type>\w*\s*Limit) ' +
     r'(?P<game_type>.+)\) \((dealer: {name}|dead button)\) --'
     ).format(**patterns),
)
end_regex = re.compile(
    '-- ending hand #{hand_num} --'.format(**patterns),
)
game_number_regex = re.compile(r'(?P<game_number>\d{13})')
hand_time_regex = re.compile(r'(?P<start_date_utc>.+:\d+)')
post_regex = re.compile(
    '{name} (?P<type>posts a .+) of'.format(**patterns) +
    r'{amount}\s*(?P<all_in>[a-z ]+)*'.format(**patterns),
)
seats_regex = re.compile(
    r'#(?P<seat>\d+) {name} \({amount}\)'.format(**patterns),
)
round_regex = re.compile(
    r'(?P<street>^\w.+):.*(?:\[{cards})'.format(**patterns),
)
addon_regex = re.compile(
    '{name} adding{amount}'.format(**patterns),
)
hero_hand_regex = re.compile('Your hand is {cards}'.format(**patterns))
non_bet_action_regex = re.compile(
    r'{name} (?P<action>\w+(?![ a-z]+\d+\.\d{{2}}))'.format(**patterns),
)
bet_action_regex = re.compile(
    r'{name} (?!collected)(?!shows)(?P<action>\w+) '.format(**patterns) +
    r'[a-z]*\s*{amount}\s*(?P<all_in>[a-z ]+)*'.format(**patterns),
)
uncalled_regex = re.compile(
    'Uncalled bet of{amount} .+ {name}'.format(**patterns),
)
show_regex = re.compile(
    r'{name} (?P<action>\w+) a {cards}'.format(**patterns),
)
winner_regex = re.compile(
    '{name} (?P<action>collected){amount}.+'.format(**patterns),
)
run_it_twice = re.compile(
    'All players in hand choose to (?P<flag>run it twice)',
)

regex_list = {
    'blind': blind_regex,
    'start': start_regex,
    'end': end_regex,
    'game': game_number_regex,
    'hand_time': hand_time_regex,
    'post': post_regex,
    'seats': seats_regex,
    'round': round_regex,
    'addon': addon_regex,
    'hero_hand': hero_hand_regex,
    'non_bet_action': non_bet_action_regex,
    'bet_action': bet_action_regex,
    'uncalled': uncalled_regex,
    'show': show_regex,
    'winner': winner_regex,
    'run_it_twice': run_it_twice,
}


@define
class Game(object):
    """_summary_.

    Returns:
        _type_: _description_
    """

    hands: list[Ohh] = Factory(list)

    def parse_hands(self, file_name: Path) -> list[Ohh]:
        """_summary_.

        Args:
            file_name (Path): _description_

        Returns:
            list[Ohh]: _description_
        """
        round_commit: dict[str, float] = {}
        total_pot: float = 0
        player_ids: dict[str, int] = {}
        hand_number: int = 0
        end_hand_number: int = 0
        dealer_name: str = ''
        unprocessed_count: int = 0
        big_blind: float = 20.0
        small_blind: float = 10.0
        ante: float = 0
        action_id: int = 0
        round_id: int = 0
        hand_obj = Ohh().from_config()
        round_obj = Round()
        action_obj = Action()
        pot_obj = Pot()

        # The text match to look for table name.
        table_name_match = table_regex.match(file_name.name)
        if table_name_match is not None:
            table_name = str(table_name_match.group('table_name'))
            # Open and parse the hand history with csv reader
            lines = self.parse_file(file_name, subs_suits)
            logging.info(
                f'[{hand_obj.table_name}] ***STARTING HAND SEPERATION***')
            logging.info(
                f'[{hand_obj.table_name}] has {len(lines)} lines to parse.')
            # Parse and get each hand separated, and get basic hand info into
            # the hands dictionary basic hand info is hand number, hand time,
            # bet type, game type, dealer name, table name, big blind, small
            # blind, and ante. Everything else goes into TEXT.
            for i, line in enumerate(lines):
                entry = line[0]
                hand_end_match = end_regex.match(entry)
                if i == len(lines) - 1:
                    if hand_number != end_hand_number:
                        self.hands.pop()
                    break
                elif hand_end_match is not None:
                    end_hand_number = hand_end_match.group('hand_number')
                # The text match to look for what the blinds are set at
                if hand_obj.parse_blinds(blind_regex, entry) is not None:
                    continue
                # The hand "begins" when the "--- starting hand #X ---" log
                # line is read, however the hand does not "end" until the
                # following "--- starting hand #X+1 ---" log line is observed
                # (or the end of the file is reached). This is because some
                # actions such as a player voluntarily showing their cards at
                # the end of the hand are reported between the
                # "--- end hand #X ---" and the "--- stating hand #X+1 ---"
                # lines
                hand_start_match = start_regex.match(entry)
                if hand_start_match is not None:
                    self.hands.append(hand_obj)
                    hand_obj = Ohh().from_config()
                    pot_obj = Pot()
                    hand_obj.pots.append(pot_obj)
                    hand_obj.table_name = table_name
                    hand_obj.big_blind_amount = big_blind
                    hand_obj.small_blind_amount = small_blind
                    hand_obj.ante_amount = ante

                    game_number_match = game_number_regex.match(line[2])
                    hand_number = hand_start_match.group('hand_number')
                    if game_number_match is not None:
                        hand_obj.game_number = game_number_match.group(
                            'game_number')
                    hand_obj.bet_limit.bet_type = structures[
                        hand_start_match.group('bet_type')
                    ]
                    hand_obj.game_type = games[
                        hand_start_match.group('game_type')
                    ]
                    # If the button is dead, keep the dealer the same as the
                    # previous hand. Technically this is incorrect because a
                    # dead button is located at an empty seat, but effectively
                    # it is the same because the player who had the button
                    # previously will have position.
                    if 'dead button' not in entry:
                        dealer_name = hand_start_match.group('player')
                    # the text match to look for the time the hand started
                    hand_time_match = hand_time_regex.match(line[1])
                    if hand_time_match is not None:
                        hand_obj.start_date_utc = (
                            hand_time_match.group('start_date_utc') + 'Z'
                        )
                elif hand_number == '1':
                    post_match = post_regex.match(entry)
                    if post_match is not None:
                        post_type = post_match.group('type')
                        if post_type == 'posts a small blind':
                            small_blind = float(post_match.group('amount'))
                            Ohh(small_blind_amount=small_blind)
                        elif post_type == 'posts a big blind':
                            big_blind = float(post_match.group('amount'))
                            Ohh(big_blind_amount=big_blind)
                        elif post_type == 'posts an ante':
                            ante = float(post_match.group('amount'))
                            Ohh(ante_amount=ante)
                hand_obj.parse_players(
                    seats_regex, player_ids, dealer_name, entry, hero_name,
                )
                # the text to match for a post this also indicates that the
                # dealing is happening and we should move to the phase of
                # assembling rounds of actions.
                post_match = post_regex.match(entry)
                if post_match is not None:
                    action_obj = Action()
                    player = post_match.group('player')
                    post_type = post_match.group('type')
                    amount = float(post_match.group('amount'))
                    all_in = post_match.group('all_in')
                    action_obj.player_id = player_ids[player]
                    action_obj.action = post_types[post_type]
                    # Poker now records the amounts associated with actions
                    # such as bets, raises, calls, and posting blinds as the
                    # the sum total of the current and all previous actions of
                    # the player during the round. However, the OHH standard
                    # requires the amount put in from the current action rather
                    # than the sum total of the round. This difference in
                    # accounting methods requires the amount commited by each
                    # player in the round to be rcorded in a dictionary
                    # {player1: amount, player2: amount, ...}.
                    # The amount the player has commited to the round can then
                    # be subtracted from the current amount to get the amount
                    # commited in the action, that OHH requires. There is one
                    # exception to this rule, in the case of a dead blind being
                    # posted by a player who missed the blinds. Posting a
                    # missed SB is considered a "dead" and is not considered to
                    # be a amount commited, but a missed BB is a "live"blind
                    # and should be added to the amount commited to the round.
                    if action_obj.action != 'Post Dead':
                        amount = round(amount - round_commit[player], 2)
                        round_commit[player] += amount
                    action_obj.amount = amount
                    if all_in is not None:
                        action_obj.is_allin = True
                    else:
                        action_obj.is_allin = False
                    round_obj.actions.append(action_obj)
                    total_pot += amount
                    action_obj.action_number = action_id
                    action_id += 1
                    continue
                # look for round markers note that cards dealt are melded
                # together with opening round and do not necessarily mark
                # a new round
                round_match = round_regex.match(entry)
                cards_match = cards_regex.search(entry)
                if round_match is not None:
                    current_round = make_new_round[round_match.group('street')]
                    round_obj = Round()
                    action_obj = Action()
                    round_obj.street = current_round
                    round_commit = {}

                    for player_id in player_ids:
                        round_commit[player_id] = float(0)

                    if current_round == 'Preflop':
                        action_id = 0
                        round_id = 0
                    else:
                        # Make new round we need to add current round object
                        # to the OHH JSON and make a clean one increment round
                        # number and reset action number
                        round_id += 1
                        action_id = 0
                        round_obj.id = round_id
                        if cards_match is not None:
                            cards = cards_match.group('cards')
                            for card in cards.split(', '):
                                round_obj.cards.append(card)
                        else:
                            continue
                    hand_obj.rounds.append(round_obj)
                    continue
                show_hand = show_regex.search(entry)
                if show_hand is not None:
                    player = show_hand.group('player')
                    does = show_hand.group('player_action')
                    cards = show_hand.group('cards')
                    if round_obj.street != 'Showdown':
                        round_obj = Round()
                        hand_obj.rounds.append(round_obj)
                        round_id += 1
                        action_id = 0
                        round_obj.id = round_id
                        round_obj.street = make_new_round[does]
                        current_round = round_obj.street
                    action_obj = Action()
                    action_obj.action_number = action_id
                    action_obj.player_id = player_ids[player]
                    action_obj.action = 'Shows Cards'
                    for card in cards.split(', '):
                        action_obj.cards.append(card)
                    round_obj.actions.append(action_obj)
                    action_id += 1
                    round_commit = {}
                    for player_id in player_ids:
                        round_commit[player_id] = 0
                    continue
                # the text to match for cards dealt
                hero_hand = hero_hand_regex.match(entry)
                if hero_hand is not None:
                    cards = hero_hand.group('cards')
                    action_obj = Action()
                    action_obj.action_number = action_id
                    action_obj.player_id = hand_obj.hero_player_id
                    action_obj.action = 'Dealt Cards'
                    for card in cards.split(', '):
                        action_obj.cards.append(card)
                    round_obj.actions.append(action_obj)
                    action_id += 1
                    continue
                non_bet_action = non_bet_action_regex.match(entry)
                if non_bet_action is not None:
                    player = non_bet_action.group('player')
                    does = non_bet_action.group('player_action')
                    action_obj = Action()
                    action_obj.action_number = action_id
                    action_obj.player_id = player_ids[player]
                    action_obj.action = verb_to_action[does]
                    round_obj.actions.append(action_obj)
                    action_id += 1
                    continue
                bet_action = bet_action_regex.match(entry)
                if bet_action is not None:
                    player = bet_action.group('player')
                    does = bet_action.group('player_action')
                    amount = float(bet_action.group('amount'))
                    all_in = bet_action.group('all_in')
                    action_obj = Action()
                    action_obj.action_number = action_id
                    action_obj.player_id = player_ids[player]
                    action_obj.action = verb_to_action[does]
                    if does in ('raises', 'calls'):
                        amount = round(amount - round_commit[player], 2)
                    action_obj.amount = amount
                    round_commit[player] += amount
                    total_pot += amount
                    if all_in is not None:
                        action_obj.is_allin = True
                    round_obj.actions.append(action_obj)
                    action_id += 1
                    continue
                uncalled_bet_match = uncalled_regex.match(entry)
                if uncalled_bet_match is not None:
                    amount = round(
                        float(uncalled_bet_match.group('amount')),
                        2,
                    )
                    total_pot -= amount
                    continue
                winner = winner_regex.match(entry)
                if winner is not None:
                    player_wins_obj = PlayerWins()
                    pot_obj.player_wins.append(player_wins_obj)
                    player = winner.group('player')
                    does = winner.group('player_action')
                    amount = float(winner.group('amount'))
                    player_wins_obj.player_id = player_ids[player]
                    pot_obj.amount += amount
                    player_wins_obj.win_amount += amount
                    continue
                # Hands with the option to run it twice there are several
                # lines in the csv file that will contain the string
                # "run it twice" but the only line that will have made it this
                # far will indicat that all players approved.
                if 'run it twice' in entry:
                    hand_obj.flags.append('Run_It_Twice')
                    continue
                unprocessed_count += 1
                logging.debug(
                    f'[{table_name}][{hand_number}] "{line}" was not processed.'
                )

            # if hero_playing is False:
            #     ohh[FLAGS].append("Observed")
            # ohh[PLAYERS] = players
            # ohh[ROUNDS].append(round_obj)
            # table.append(ohh)

        return self.hands

    def parse_file(self, file_name: Path, subs: dict[str, str]):
        """Read a CSV file and make substitutions according to the subs dictionary.

        Args:
            file_obj (Path): Path to the CSV file to be read.
            subs (dict): Dictionary containg strings to substitute or replace in the data.

        Returns:
            List[List[str]]: The rows of data in the CSV file in reverse order.
        """
        rows: list[Tuple[str, str, str]] = []
        subs_regex = re.compile('|'.join(subs.keys()))
        lines_ignored: int = 0

        with file_name.open(mode='r', encoding='UTF-8') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                # Lines containing these strings will be ignored
                if any(
                    i in row[0]
                    for i in [
                        'The admin',
                        'joined',
                        'requested',
                        'canceled the seat',
                        'authenticated',
                        'quits',
                        'stand up',
                        'sit back',
                        'Remaining players',
                        'chooses',
                        'choose to not',
                        'Dead Small Blind',
                        'room ownership',
                        'IMPORTANT:',
                        'WARNING:',
                    ]
                ):
                    lines_ignored += 1
                else:
                    row = [
                        subs_regex.sub(lambda match: subs[match.group(0)], i)
                        for i in row
                    ]
                    row[0] = row[0].encode('ascii', 'ignore').decode()
                    row = tuple(row)
                    rows.append(row)
        rows.reverse()
        return rows


game = Game().parse_hands(csv_files[0])

for hand in game:
    print(asdict(hand))
