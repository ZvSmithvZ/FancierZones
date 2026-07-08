from enum import Enum, auto


class HandleType(Enum):
    """
    Which part of a zone the user is interacting with.
    """

    NONE = auto()

    MOVE = auto()

    LEFT = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()

    TOP_LEFT = auto()
    TOP_RIGHT = auto()

    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()


class EditorMode(Enum):
    """
    Current editor action.
    """

    IDLE = auto()

    CREATING = auto()

    MOVING = auto()

    RESIZING = auto()
