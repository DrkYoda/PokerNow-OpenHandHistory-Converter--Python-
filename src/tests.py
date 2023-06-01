import csv
import logging
from pathlib import Path
from typing import Tuple

from timer import Timer

log_dir = Path("./src/Logs")
log_dir.mkdir(exist_ok=True)
time_log_file = Path("time_log").with_suffix(".log")
word_log_file = Path("words_log").with_suffix(".log")
time_log_path = log_dir / time_log_file
word_log_path = log_dir / word_log_file
logger_time = logging.getLogger("time")
logger_words = logging.getLogger("ignore words")
handler_time = logging.FileHandler(time_log_path)
handler_words = logging.FileHandler(word_log_path)
formatter = logging.Formatter(
    "[%(asctime)s][%(created)f][%(levelname)s]:%(message)s")
handler_time.setFormatter(formatter)
handler_words.setFormatter(formatter)
logger_time.addHandler(handler_time)
logger_words.addHandler(handler_words)
logger_time.setLevel(logging.DEBUG)
logger_words.setLevel(logging.DEBUG)


ignore_words = ("he player ", "chooses", "Remaining players",
                "choose to not", "Dead Small Blind", 'enqueued')
REPLACEMENTS = (
    ("10♥", "Th"),
    ("10♠", "Ts"),
    ("10♦", "Td"),
    ("10♣", "Tc"),
    ("♥", "h"),
    ("♠", "s"),
    ("♦", "d"),
    ("♣", "c"))

csv_dir = Path("PokerNowHandHistory")
csv_files = [child for child in csv_dir.iterdir() if child.suffix == ".csv"]


def parse_file(file: Path, ignore_dict: dict[str, int]):
    """Read a CSV file and make substitutions according to the subs dictionary.

    Args:
        file_obj (Path): Path to the CSV file to be read.
        subs (dict): Dictionary containg strings to substitute or replace in the data.

    Returns:
        List[List[str]]: The rows of data in the CSV file in reverse order.
    """
    rows: list[Tuple[str, str, str]] = []
    for ignore_word in ignore_words:
        ignore_dict[ignore_word] = 0
    lines_ignored: int = 0

    with file.open(mode="r", encoding="UTF-8") as csv_file:
        reader = csv.reader(csv_file)
        next(reader)
        for row in reader:
            # Lines containing these strings will be ignored
            for j in ignore_words:
                if j in row[0]:
                    ignore_dict[j] += 1
                    lines_ignored += 1
                    break
            for old, new in REPLACEMENTS:
                row[0] = row[0].replace(old, new)
            row[0] = row[0].encode("ascii", "ignore").decode()
            row = tuple(row)
            rows.append(row)
        logger_words.info(
            f"[{file.stem.removeprefix('poker_now_log_')}][Words: {ignore_dict}]")
        rows.reverse()
        return rows


def parse_files(files: list[Path], ignore_words: Tuple[str, ...]):
    lines: list[Tuple[str, str, str]] = []
    ignore_dict = {}
    for ignore_word in ignore_words:
        ignore_dict[ignore_word] = 0
    for file in files:
        with Timer('accumulate', logger=logger_time.info) as t:
            t.text = f"[{file.stem.removeprefix('poker_now_log_')}][Elapsed time: {{:0.6f}} s]"
            lines = parse_file(file, ignore_dict)
    return lines


with Timer('accumulate', logger=logger_time.info) as t:
    parse_files(csv_files, ignore_words)
    print(t.timers)
