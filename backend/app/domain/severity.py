from enum import IntEnum


class Level(IntEnum):
    CLEAR = 0
    CAUTION = 1
    WARNING = 2
    SEVERE = 3
    NO_GO = 4

    @property
    def code(self) -> str:
        return self.name.lower()

    @property
    def label(self) -> str:
        return {
            Level.CLEAR: "Clear",
            Level.CAUTION: "Caution",
            Level.WARNING: "Warning",
            Level.SEVERE: "Severe",
            Level.NO_GO: "No-Go",
        }[self]
