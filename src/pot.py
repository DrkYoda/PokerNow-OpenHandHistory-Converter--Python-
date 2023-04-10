from attrs import define, Factory

from player_wins import PlayerWins


@define
class Pot:
    number: int = int(0)
    amount: float = 0.0
    rake: float = 0.0
    jackpot: float = 0.0
    player_wins: list[PlayerWins] = Factory(list)
