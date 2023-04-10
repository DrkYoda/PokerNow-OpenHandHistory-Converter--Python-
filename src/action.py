from attrs import define, Factory


@define
class Action:
    """_summary_"""

    action_number: int = int()
    player_id: int = int()
    action: str = str()
    amount: float = 0.0
    is_allin: bool = bool(False)
    cards: list[str] = Factory(list)
