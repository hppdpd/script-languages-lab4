from dataclasses import dataclass, field


@dataclass
class Country:
    name: str
    code: str
    id: int | None = None


@dataclass
class Prize:
    category: str
    year: int
    id: int | None = None


@dataclass
class Laureate:
    full_name: str
    email: str
    birth_year: int
    country_id: int
    id: int | None = None
    prize_ids: list[int] = field(default_factory=list)
