from dataclasses import dataclass, field

from enums import AssignmentType


@dataclass
class AppSettings:
    auto_tile_on_launch: bool = False


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
class WindowBehavior:
    maximize: bool = False
    always_on_top: bool = False


@dataclass
class Zone:
    x: int
    y: int
    width: int
    height: int
    assignment: Assignment | None = None
    window_behavior: WindowBehavior = field(default_factory=WindowBehavior)
    occupied_hwnd: int | None = None


@dataclass
class Monitor:
    id: str
    x: int
    y: int
    width: int
    height: int
    work_x: int
    work_y: int
    work_width: int
    work_height: int
    zones: list[Zone] = field(default_factory=list)
