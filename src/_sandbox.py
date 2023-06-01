import csv
import logging
import re
from pathlib import Path
from typing import Counter, Pattern, TypeAlias

from timer import Timer

PokerNow: TypeAlias = list[tuple[str, str, str]]
log_dir = Path('./src/Logs')
log_dir.mkdir(exist_ok=True)
time_log_file = Path('time_log').with_suffix('.log')
word_log_file = Path('words_log').with_suffix('.log')
time_log_path = log_dir / time_log_file
word_log_path = log_dir / word_log_file
logger_time = logging.getLogger('time')
logger_words = logging.getLogger('ignore words')
handler_time = logging.FileHandler(time_log_path)
handler_words = logging.FileHandler(word_log_path)
formatter = logging.Formatter(
    fmt='[{asctime}][{created}][{levelname}]{message}',
    style='{',
)
handler_time.setFormatter(formatter)
handler_words.setFormatter(formatter)
logger_time.addHandler(handler_time)
logger_words.addHandler(handler_words)
logger_time.setLevel(logging.DEBUG)
logger_words.setLevel(logging.DEBUG)
ignore_words = (
    'he player ',
    'chooses',
    'Remaining players',
    'choose to not',
    'Dead Small Blind',
    'IMPORTANT',
    'enqueued',
)
REPLACEMENTS = (
    ('10♥', 'Th'),
    ('10♠', 'Ts'),
    ('10♦', 'Td'),
    ('10♣', 'Tc'),
    ('♥', 'h'),
    ('♠', 's'),
    ('♦', 'd'),
    ('♣', 'c'),
)
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


def parse_file(
    hh_file: Path,
    table_id: str,
    counter: Counter[str],
    word_counter_total: Counter[str],
) -> tuple[PokerNow, Counter[str]]:
    """Read a CSV file and make substitutions according to the subs dictionary.

    Args:
        hh_file (Path): Path to the CSV file to be read.
        table_id (str): Name of the table.
        counter (Counter[str]): _description_
        word_counter_total (Counter[str]): _description_

    Returns:
        tuple[list[tuple[str, str, str]], Counter[str]]: Rows from the CSV file
        in reverse order.
    """
    rows: PokerNow = []

    with hh_file.open(mode='r', encoding='UTF-8') as csv_file:
        next(csv_file)
        for row in csv.reader(csv_file):
            entry = row[0]
            # Lines containing these strings will be ignored
            if ignore_line(entry, counter):
                continue
            entry = replace_string(entry)
            row[0] = entry.encode('ascii', 'ignore').decode()
            row = tuple(row)
            rows.append(row)
        word_counter_total += counter
        logger_words.info('[{0}][{1}]'.format(table_id, counter))
        rows.reverse()
        return rows, word_counter_total


def ignore_line(entry: str, counter: Counter[str]) -> bool:
    """_summary_.

    Args:
        entry (str): _description_
        counter (Counter[str]): _description_

    Returns:
        bool: _description_
    """
    for word in ignore_words:
        if word in entry:
            counter[word] += 1
            return True
    return False


def replace_string(entry: str):
    """_summary_.

    Args:
        entry (str): _description_

    Returns:
        _type_: _description_
    """
    for old, new in REPLACEMENTS:
        entry = entry.replace(old, new)
    return entry


@Timer(
    name='parse_files()',
    text='[parse_files()][Elapsed time: {0:0.6f} s]',
    logger=logger_time.info,
)
def parse_files(files: list[Path]) -> dict[str, PokerNow]:
    """_summary_.

    Args:
        files (list[Path]): _description_

    Returns:
        PokerNow: _description_
    """
    tables: dict[str, PokerNow] = {}
    word_counter_total = Counter()
    for path in files:
        table_id = path.stem.removeprefix('poker_now_log_')
        with Timer('parse_file()', logger=logger_time.info) as pfst:
            table, word_counter_total = parse_file(
                path, table_id, init_ignore_words(), word_counter_total,
            )
            tables[table_id] = table
            pfst.text = '[{0}][{1}][Elapsed time: {{:0.6f}} s]'.format(
                pfst.name,
                table_id,
            )
    logger_words.info('[ALL][{0}]'.format(word_counter_total))
    return tables


def init_ignore_words():
    """_summary_.

    Returns:
        _type_: _description_
    """
    word_counter: Counter[str] = Counter(ignore_words)
    for word in ignore_words:
        word_counter[word] = 0
    return word_counter


def match_all_line(
    line: tuple[str, str, str],
    pattern: Pattern[str],
) -> list[dict[str, str]]:
    """_summary_.

    Args:
        pattern (Pattern[str]): _description_
        line (tuple[str, str, str]): _description_

    Returns:
        _type_: _description_
    """
    return [match.groupdict() for match in pattern.finditer(line[0])]


def match_lines(
    line: tuple[str, str, str],
    patts: dict[str, Pattern[str]],
) -> tuple[str, list[dict[str, str]] | None]:
    """_summary_.

    Args:
        patts (list[Pattern[str]]): _description_
        line (tuple[str, str, str]): _description_

    Returns:
        _type_: _description_
    """
    for regex_id, pattern in patts.items():
        pattern_match = pattern.search(line[0])
        if pattern_match is not None:
            patt: list[dict[str, str]] = [pattern_match.groupdict()]
            if regex_id == 'seats':
                return regex_id, match_all_line(line, pattern)
            return regex_id, patt
    return 'none', None


def get_values(hand_histories: dict[str, PokerNow], rep: Timer):
    patts: list[list[dict[str, str]]] = []
    regex_counter_total: Counter[str] = Counter()
    for table_name, lines in hand_histories.items():
        for line in lines:
            count, patt = match_lines(line, regex_list)
            regex_dict[count] += 1
            patts.append(patt)
        rep.text = '[{0}][{1}][Elapsed time: {{:0.6f}} s]'.format(
            rep.name,
            table_name,
        )
    return patts


def init_regex():
    """_summary_.

    Returns:
        _type_: _description_
    """
    regex_counter: Counter[str] = Counter(regex_list.keys())
    for name in regex_counter:
        regex_counter[name] = 0
    return regex_counter


with Timer('regex', logger=logger_time.info) as rep:
    val = get_values(parse_files(csv_files), rep)

print(val[0::100])
