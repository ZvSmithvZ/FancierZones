from enum import Enum


class HandleType(Enum):
    """
    Which part of a zone the user is interacting with.
    """

    NONE = 0

    MOVE = 1

    TOP_LEFT = 2
    TOP = 3
    TOP_RIGHT = 4
    LEFT = 5
    RIGHT = 6
    BOTTOM_LEFT = 7
    BOTTOM = 8
    BOTTOM_RIGHT = 9


class EditorMode(Enum):
    """
    Current editor action.
    """

    IDLE = 0

    CREATING = 1

    MOVING = 2

    RESIZING = 3
