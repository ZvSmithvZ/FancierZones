from dataclasses import dataclass, field


@dataclass
class Zone:
    x: int
    y: int
    width: int
    height: int
    assignment: str | None = None
    occupied_hwnd: int | None = None


@dataclass
class Monitor:
    id: str
    x: int
    y: int
    width: int
    height: int
    zones: list[Zone] = field(default_factory=list)
