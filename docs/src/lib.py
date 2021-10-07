from typing import List


class Knight:
    limbs: int = 4
    taunts: List[str] = [
        "None shall pass!",
        "'Tis but a scratch!",
        "It's just a flesh wound... Chicken!",
        "Right, I'll do you for that!",
        "Oh, I see, running away?",
    ]

    def scratch(self) -> None:
        """Scratch the knight."""
        self.limbs -= 1

    def taunt(self) -> str:
        """Knight taunts the adversary."""
        return self.taunts[::-1][self.limbs]


class Shrubbery:
    """A shrubbery bought in town."""

    looks_nice: bool
    too_expensive: bool

    def __init__(self, looks_nice: bool, too_expensive: bool):
        self.looks_nice = looks_nice
        self.too_expensive = too_expensive
