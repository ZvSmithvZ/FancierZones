from dataclasses import dataclass, field

from enums import AssignmentType


@dataclass
class Assignment:
    """
    Describes what window should occupy a zone.
    """

    type: AssignmentType | None = None
    name: str = ""


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    exe: str | None = None
    class_name: str = ""


@dataclass
class Zone:
    x: int
    y: int
    width: int
    height: int
    assignment: Assignment | None = None
    occupied_hwnd: int | None = None


@dataclass
class Monitor:
    id: str
    x: int
    y: int
    width: int
    height: int
    zones: list[Zone] = field(default_factory=list)
