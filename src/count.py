

import re
from typing import Counter, Pattern


ignore_words = (
    'he player ',
    'chooses',
    'Remaining players',
    'choose to not',
    'Dead Small Blind',
    'enqueued',
)
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
    (r'-- starting hand #{hand_num}  \((?P<bet_type>\w*\s*Limit) ' +
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
}


def init_counter(elements: dict[str, Pattern[str]]):
    return Counter(elements.keys())


print(init_counter(regex_list))
