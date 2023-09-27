from attrs import define


@define
class PlayerWins:
    player_id: int = int(0)
    win_amount: float = 0.0
    cashout_amount: float = 0.0
    cashout_fee: float = 0.0
    bonus_amount: float = 0.0
    contributed_rake: float = 0.0
