from configparser import ConfigParser
from pathlib import Path
from re import Pattern
from typing import Any, Optional, Tuple
from attr import Factory
from attrs import define, Factory

from players import Player
from pot import Pot
from rounds import Round

SPEC_VERSION = "spec_version"
SITE_NAME = "site_name"
NETWORK_NAME = "network_name"
INTERNAL_VERSION = "internal_version"
CURRENCY = "currency"

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


@define
class BetLimit:
    bet_cap: Optional[float] = None
    bet_type: str = str()


config_path = Path("Config/config.ini")
config = get_config(config_path)
spec_version = config.get(OHH_CONSTANTS, SPEC_VERSION)
internal_version = config.get(OHH_CONSTANTS, INTERNAL_VERSION)
network_name = config.get(OHH_CONSTANTS, NETWORK_NAME)
site_name = config.get(OHH_CONSTANTS, SITE_NAME)
currency = config.get(OHH_CONSTANTS, CURRENCY)
hero_name = config.get(OHH_CONSTANTS, HERO_NAME)


@define
class Ohh:
    """_summary_

    Returns:
        _type_: _description_
    """

    spec_version: str = str()
    internal_version: str = str()
    network_name: str = str()
    site_name: str = str()
    game_type: str = str()
    table_name: str = str()
    table_size: int = int(10)
    game_number: str = str()
    start_date_utc: str = str()
    game_type: str = str()
    currency: str = str()
    dealer_seat: int = int()
    small_blind_amount: float = 0.0
    big_blind_amount: float = 0.0
    bet_limit: BetLimit = BetLimit()
    ante_amount: float = 0.0
    hero_player_id: Optional[int] = None
    flags: list[str] = Factory(list)
    players: list[Player] = Factory(list)
    rounds: list[Round] = Factory(list)
    pots: list[Pot] = Factory(list)

    @classmethod
    def from_config(cls):
        return cls(
            spec_version=spec_version,
            internal_version=internal_version,
            network_name=network_name,
            site_name=site_name,
            currency=currency,
        )

    def parse_players(
        self,
        regex: Pattern[str],
        player_ids: dict[str, int],
        dealer_name: str,
        entry: str,
        hero_name: str = hero_name,
    ):
        seats_match = regex.finditer(entry)
        if seats_match is not None:
            player_id = int()
            for player in seats_match:
                player_obj = Player()
                player_obj.id = player_id
                player_obj.seat = int(player.group("seat"))
                player_obj.display = str(player.group("player"))
                player_obj.starting_stack = float(player.group("amount"))
                device_id = str(player.group("device_id"))
                aliases_names = player_obj.check_player(
                    device_id,
                )
                player_obj.name = aliases_names[player_obj.display]
                self.players.append(player_obj)
                # If the player is the dealer, set the value of the dealers seat number in
                # the ohh dictionary
                if dealer_name == player_obj.display:
                    self.dealer_seat = player_obj.seat
                    # If the player is the hero, set the value of players ID in the ohh
                    # dictionary.
                if player_obj.name == hero_name:
                    self.hero_player_id = player_id
                    hero_playing: bool = True
                    # The OHH standard has a unique identifier for every player within the hand.
                    # This id is used to identify the player in all other locations of the hand
                    # history. Therefore, it is convenient to creat a dictionary to easily pull
                    # out the id of each player when needed.
                player_ids[player_obj.display] = player_id
                player_id += 1
                continue

    def parse_blinds(self, regex: Pattern[str], entry: str):
        blind_match = regex.match(entry)
        if blind_match:
            return blind_match.groupdict()


x = Ohh(big_blind_amount=0.25).from_config()
print(x.__class__)
y = Ohh()
print(y)
