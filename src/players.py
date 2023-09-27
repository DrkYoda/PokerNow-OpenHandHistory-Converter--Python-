import json
from pathlib import Path
from re import Pattern
from attrs import define
from rich.console import Console


console = Console()


def load_name_map(file: Path) -> dict[str, dict[str, list[str]]]:
    """Open aliase->name map file (aliase-name_map.json) and parse it.  If the file is not found
        then create a json file.

    Args:
        file (Path): Path to the input file to be parsed

    Returns:
        dict[str, dict[str, list[str]]]: _description_
    """
    try:
        with file.open(mode="r", encoding="utf-8") as map_file:
            return json.load(map_file)
    except FileNotFoundError:
        with file.open(mode="a+", encoding="utf-8") as map_file:
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
        with file.open(mode="w", encoding="utf-8") as map_file:
            json.dump(dict(sorted(name_map.items())), map_file, indent=4)
    except FileNotFoundError:
        with file.open(mode="a+", encoding="utf-8") as map_file:
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


name_map_path = Path("Config/name-map.json")
players_map = load_name_map(name_map_path)
aliases_names = switch_key_and_values(players_map, "nicknames")
device_ids = switch_key_and_values(players_map, "devices")


@define
class Player:
    """_summary_"""

    id: int = int()
    seat: int = int()
    name: str = str()
    display: str = str()
    starting_stack: float = 0.0
    player_bounty: float = 0.0

    def check_player(
        self,
        device_id: str,
        players_map: dict[str, dict[str, list[str]]] = players_map,
        aliases_names: dict[str, str] = aliases_names,
        device_ids: dict[str, str] = device_ids,
    ):
        try:
            self.name = aliases_names[self.display]
            if device_id not in device_ids:
                console.print(
                    f"- The aliase [green]{self.display}[/green] is associated "
                    f"with [blue]{self.name}[/blue] but the device "
                    f"[magenta]{device_id}[/magenta] is not in the data model "
                    f"for this player. Adding [magenta]{device_id}[/magenta] to the"
                    f" data model for [blue]{self.name}[/blue]>>>"
                )
                players_map[self.name]["devices"].append(device_id)
                device_ids = switch_key_and_values(players_map, "devices")
        except KeyError:
            if device_id not in device_ids:
                name_input = console.input(
                    f"\n- The alias [green]{self.display}[/green] and device "
                    f"[magenta]{device_id}[/magenta] is not in the data model. Type"
                    f" the name to associate with [green]{self.display}[/green] "
                    "in the data model and press ENTER>>>"
                )
                try:
                    players_map[name_input]["nicknames"].append(self.display)
                    players_map[name_input]["devices"].append(device_id)
                    device_ids = switch_key_and_values(players_map, "devices")
                    aliases_names = switch_key_and_values(players_map, "nicknames")
                except KeyError:
                    players_map.update(
                        {
                            name_input: {
                                "nicknames": [self.display],
                                "devices": [device_id],
                            }
                        }
                    )
                    device_ids = switch_key_and_values(players_map, "devices")
                    aliases_names = switch_key_and_values(players_map, "nicknames")
            else:
                self.name = device_ids[device_id]
                bool_input = console.input(
                    f"\n- The alias [green]{self.display}[/green] is not in "
                    f"data model but the device [magenta]{device_id}[/magenta] has "
                    f"been used by [blue]{self.name}[/blue]. If "
                    f"[green]{self.display}[/green] is [blue]{self.name}[/blue] type "
                    f"[yellow]'Y'[/yellow], if this is not [blue]{self.name}[/blue] "
                    "[yellow]'N'[/yellow] and press ENTER>>>"
                )
                if bool_input == "Y":
                    players_map[self.name]["nicknames"].append(self.display)
                    aliases_names = switch_key_and_values(players_map, "nicknames")
                elif bool_input == "N":
                    name_input = console.input(
                        "\n[red]IMPORTANT:[/red] If different players are playing "
                        "from the same device then there is the potential for "
                        "cheating. Please type the name to associate alias "
                        f"[green]{self.display}[/green] and press ENTER>>>"
                    )
                    try:
                        players_map[name_input]["nicknames"].append(self.display)
                        players_map[name_input]["devices"].append(device_id)
                        device_ids = switch_key_and_values(players_map, "devices")
                        aliases_names = switch_key_and_values(players_map, "nicknames")
                    except KeyError:
                        players_map.update(
                            {
                                name_input: {
                                    "nicknames": [self.display],
                                    "devices": [device_id],
                                }
                            }
                        )
            self.name = aliases_names[self.display]
        return aliases_names
