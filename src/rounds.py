from attrs import define, Factory
from action import Action


@define
class Round:
    """_summary_"""

    id: int = int()
    street: str = str()
    cards: list[str] = Factory(list)
    actions: list[Action] = Factory(list)
