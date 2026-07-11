"""Shared domain contracts for the Game Assistant MVP."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
import math
from types import MappingProxyType
from typing import Any, TypeVar
from uuid import uuid4


__all__ = [
    "AnalysisResult",
    "CoachReport",
    "DomainValidationError",
    "EvidenceRef",
    "EvidenceSource",
    "GameId",
    "KeyMode",
    "MapMetadata",
    "PlayerProfile",
    "PracticeSession",
    "ReplayMetadata",
    "ReplaySupportStatus",
    "ScoreRecord",
    "SessionStatus",
    "TrainingPlan",
    "TrainingTask",
    "WeaknessCategory",
    "WeaknessSignal",
    "new_id",
]


class DomainValidationError(ValueError):
    """Raised when a domain model violates a field-specific invariant."""


class GameId(str, Enum):
    """Stable game identifiers supported by the shared MVP contract."""

    OSU_MANIA = "osu_mania"


class KeyMode(str, Enum):
    """osu!mania key modes supported by the MVP."""

    FOUR_K = "4k"
    SEVEN_K = "7k"


class SessionStatus(str, Enum):
    """Lifecycle state for a practice session record."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class EvidenceSource(str, Enum):
    """Kinds of records that may ground analysis, plans, and reports."""

    MANUAL_NOTE = "manual_note"
    MAP_METADATA = "map_metadata"
    PRACTICE_SESSION = "practice_session"
    REPLAY_METADATA = "replay_metadata"
    SCORE_RECORD = "score_record"
    ANALYSIS_RESULT = "analysis_result"
    TRAINING_PLAN = "training_plan"


class WeaknessCategory(str, Enum):
    """Stable weakness categories for early osu!mania coaching records."""

    ACCURACY_CONTROL = "accuracy_control"
    CONSISTENCY = "consistency"
    JACK_CONTROL = "jack_control"
    LONG_NOTE_CONTROL = "long_note_control"
    READING = "reading"
    SPEED = "speed"
    STAMINA = "stamina"
    TIMING = "timing"


class ReplaySupportStatus(str, Enum):
    """Current replay handling support for a registered replay file."""

    UNSUPPORTED = "unsupported"
    METADATA_ONLY = "metadata_only"
    SUPPORTED = "supported"


SourceMetadataValue = str | bool | None
_EnumT = TypeVar("_EnumT", bound=Enum)


def new_id(prefix: str | None = None) -> str:
    """Return a caller-visible unique string id.

    Constructors never generate identifiers implicitly. Callers that want a new
    id can opt in through this helper, then pass the returned string explicitly.
    """

    generated = str(uuid4())
    if prefix is None:
        return generated

    clean_prefix = _required_text("new_id", "prefix", prefix)
    if any(character.isspace() for character in clean_prefix):
        raise DomainValidationError("new_id.prefix must not contain whitespace")
    return f"{clean_prefix}_{generated}"


def _fail(model: str, field_name: str, message: str) -> None:
    raise DomainValidationError(f"{model}.{field_name} {message}")


def _required(data: Mapping[str, Any], model: str, field_name: str) -> Any:
    if field_name not in data:
        _fail(model, field_name, "is required")
    return data[field_name]


def _optional(data: Mapping[str, Any], field_name: str, default: Any = None) -> Any:
    return data[field_name] if field_name in data else default


def _required_text(model: str, field_name: str, value: Any) -> str:
    if not isinstance(value, str):
        _fail(model, field_name, "must be a string")
    normalized = value.strip()
    if normalized == "":
        _fail(model, field_name, "must not be blank")
    return normalized


def _optional_text(model: str, field_name: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        _fail(model, field_name, "must be a string or None")
    normalized = value.strip()
    return normalized or None


def _required_id(model: str, field_name: str, value: Any) -> str:
    return _required_text(model, field_name, value)


def _optional_id(model: str, field_name: str, value: Any) -> str | None:
    return _optional_text(model, field_name, value)


def _coerce_enum(
    enum_type: type[_EnumT],
    model: str,
    field_name: str,
    value: Any,
) -> _EnumT:
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            _fail(model, field_name, f"has unknown value {value!r}")
    _fail(model, field_name, f"must be a {enum_type.__name__} value")


def _enum_value(value: Enum) -> str:
    return str(value.value)


def _ensure_sequence(model: str, field_name: str, values: Any) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)):
        _fail(model, field_name, "must be a sequence, not a string")
    try:
        return tuple(values)
    except TypeError:
        _fail(model, field_name, "must be a sequence")


def _key_modes(model: str, field_name: str, values: Any) -> tuple[KeyMode, ...]:
    modes = tuple(
        _coerce_enum(KeyMode, model, field_name, value)
        for value in _ensure_sequence(model, field_name, values)
    )
    _reject_duplicates(model, field_name, tuple(_enum_value(mode) for mode in modes))
    return modes


def _weakness_categories(
    model: str,
    field_name: str,
    values: Any,
) -> tuple[WeaknessCategory, ...]:
    categories = tuple(
        _coerce_enum(WeaknessCategory, model, field_name, value)
        for value in _ensure_sequence(model, field_name, values)
    )
    _reject_duplicates(
        model,
        field_name,
        tuple(_enum_value(category) for category in categories),
    )
    return categories


def _text_items(model: str, field_name: str, values: Any) -> tuple[str, ...]:
    return tuple(
        _required_text(model, field_name, value)
        for value in _ensure_sequence(model, field_name, values)
    )


def _id_items(model: str, field_name: str, values: Any) -> tuple[str, ...]:
    ids = tuple(
        _required_id(model, field_name, value)
        for value in _ensure_sequence(model, field_name, values)
    )
    _reject_duplicates(model, field_name, ids)
    return ids


def _reject_duplicates(model: str, field_name: str, values: Sequence[str]) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            _fail(model, field_name, f"must not contain duplicate value {value!r}")
        seen.add(value)


def _utc_datetime(model: str, field_name: str, value: Any) -> datetime:
    if not isinstance(value, datetime):
        _fail(model, field_name, "must be a datetime")
    offset = value.utcoffset()
    if offset is None:
        _fail(model, field_name, "must be timezone-aware UTC")
    if offset.total_seconds() != 0:
        _fail(model, field_name, "must use UTC offset")
    return value.astimezone(timezone.utc)


def _optional_utc_datetime(
    model: str,
    field_name: str,
    value: Any,
) -> datetime | None:
    if value is None:
        return None
    return _utc_datetime(model, field_name, value)


def _parse_utc_datetime(model: str, field_name: str, value: Any) -> datetime:
    if not isinstance(value, str):
        _fail(model, field_name, "must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(model, field_name, "must be an ISO 8601 UTC datetime string")
    return _utc_datetime(model, field_name, parsed)


def _parse_optional_utc_datetime(
    model: str,
    field_name: str,
    value: Any,
) -> datetime | None:
    if value is None:
        return None
    return _parse_utc_datetime(model, field_name, value)


def _datetime_to_json(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _required_date(model: str, field_name: str, value: Any) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        _fail(model, field_name, "must be a date")
    return value


def _parse_date(model: str, field_name: str, value: Any) -> date:
    if not isinstance(value, str):
        _fail(model, field_name, "must be an ISO 8601 date string")
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail(model, field_name, "must be an ISO 8601 date string")


def _finite_float(model: str, field_name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(model, field_name, "must be a finite number")
    as_float = float(value)
    if not math.isfinite(as_float):
        _fail(model, field_name, "must be finite")
    return as_float


def _optional_finite_float(
    model: str,
    field_name: str,
    value: Any,
) -> float | None:
    if value is None:
        return None
    return _finite_float(model, field_name, value)


def _non_negative_float(model: str, field_name: str, value: Any) -> float:
    as_float = _finite_float(model, field_name, value)
    if as_float < 0:
        _fail(model, field_name, "must be non-negative")
    return as_float


def _optional_non_negative_float(
    model: str,
    field_name: str,
    value: Any,
) -> float | None:
    if value is None:
        return None
    return _non_negative_float(model, field_name, value)


def _normalized_float(model: str, field_name: str, value: Any) -> float:
    as_float = _finite_float(model, field_name, value)
    if as_float < 0 or as_float > 1:
        _fail(model, field_name, "must be between 0 and 1 inclusive")
    return as_float


def _accuracy(model: str, field_name: str, value: Any) -> float:
    as_float = _finite_float(model, field_name, value)
    if as_float < 0 or as_float > 100:
        _fail(model, field_name, "must be between 0 and 100 inclusive")
    return as_float


def _int(model: str, field_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(model, field_name, "must be an integer")
    return value


def _non_negative_int(model: str, field_name: str, value: Any) -> int:
    as_int = _int(model, field_name, value)
    if as_int < 0:
        _fail(model, field_name, "must be non-negative")
    return as_int


def _optional_non_negative_int(
    model: str,
    field_name: str,
    value: Any,
) -> int | None:
    if value is None:
        return None
    return _non_negative_int(model, field_name, value)


def _positive_int(model: str, field_name: str, value: Any) -> int:
    as_int = _int(model, field_name, value)
    if as_int <= 0:
        _fail(model, field_name, "must be positive")
    return as_int


def _bool(model: str, field_name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        _fail(model, field_name, "must be a boolean")
    return value


def _source_metadata(
    model: str,
    field_name: str,
    value: Any,
) -> Mapping[str, SourceMetadataValue] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        _fail(model, field_name, "must be a mapping or None")

    normalized: dict[str, SourceMetadataValue] = {}
    for raw_key, raw_value in value.items():
        key = _required_text(model, field_name, raw_key)
        if isinstance(raw_value, bool) or raw_value is None:
            normalized[key] = raw_value
        elif isinstance(raw_value, str):
            normalized[key] = _optional_text(model, field_name, raw_value)
        elif isinstance(raw_value, (int, float)):
            _fail(
                model,
                field_name,
                "does not accept numeric metadata; use bounded model fields",
            )
        else:
            _fail(model, field_name, "must contain JSON-compatible string values")

    if not normalized:
        return None
    return MappingProxyType(dict(sorted(normalized.items())))


def _metadata_to_dict(
    value: Mapping[str, SourceMetadataValue] | None,
) -> dict[str, SourceMetadataValue] | None:
    if value is None:
        return None
    return {key: value[key] for key in sorted(value)}


def _evidence_refs(
    model: str,
    field_name: str,
    values: Any,
    *,
    required_non_empty: bool,
) -> tuple[EvidenceRef, ...]:
    refs = tuple(
        value
        if isinstance(value, EvidenceRef)
        else EvidenceRef.from_dict(value)
        for value in _ensure_sequence(model, field_name, values)
    )
    if required_non_empty and not refs:
        _fail(model, field_name, "must contain at least one evidence reference")
    _reject_duplicates(model, field_name, tuple(ref.record_id for ref in refs))
    return refs


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    """Reference to evidence without embedding another domain object."""

    source: EvidenceSource
    record_id: str
    message: str | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(
            self,
            "source",
            _coerce_enum(EvidenceSource, model, "source", self.source),
        )
        object.__setattr__(
            self,
            "record_id",
            _required_id(model, "record_id", self.record_id),
        )
        object.__setattr__(
            self,
            "message",
            _optional_text(model, "message", self.message),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": _enum_value(self.source),
            "record_id": self.record_id,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EvidenceRef:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            source=_required(data, model, "source"),
            record_id=_required(data, model, "record_id"),
            message=_optional(data, "message"),
        )


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    """Player identity and declared osu!mania practice focus."""

    id: str
    display_name: str
    primary_game: GameId
    created_at: datetime
    focus_modes: Sequence[KeyMode] = ()
    current_pp: float | None = None
    goals: Sequence[str] = ()

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "display_name",
            _required_text(model, "display_name", self.display_name),
        )
        object.__setattr__(
            self,
            "primary_game",
            _coerce_enum(GameId, model, "primary_game", self.primary_game),
        )
        object.__setattr__(
            self,
            "created_at",
            _utc_datetime(model, "created_at", self.created_at),
        )
        object.__setattr__(
            self,
            "focus_modes",
            _key_modes(model, "focus_modes", self.focus_modes),
        )
        object.__setattr__(
            self,
            "current_pp",
            _optional_non_negative_float(model, "current_pp", self.current_pp),
        )
        object.__setattr__(self, "goals", _text_items(model, "goals", self.goals))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "primary_game": _enum_value(self.primary_game),
            "created_at": _datetime_to_json(self.created_at),
            "focus_modes": [_enum_value(mode) for mode in self.focus_modes],
            "current_pp": self.current_pp,
            "goals": list(self.goals),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PlayerProfile:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            display_name=_required(data, model, "display_name"),
            primary_game=_required(data, model, "primary_game"),
            created_at=_parse_utc_datetime(
                model,
                "created_at",
                _required(data, model, "created_at"),
            ),
            focus_modes=_optional(data, "focus_modes", ()),
            current_pp=_optional(data, "current_pp"),
            goals=_optional(data, "goals", ()),
        )


@dataclass(frozen=True, slots=True)
class PracticeSession:
    """A practice session boundary that later records can reference by id."""

    id: str
    profile_id: str
    started_at: datetime
    status: SessionStatus
    ended_at: datetime | None = None
    notes: str | None = None
    focus_modes: Sequence[KeyMode] = ()

    def __post_init__(self) -> None:
        model = type(self).__name__
        started_at = _utc_datetime(model, "started_at", self.started_at)
        ended_at = _optional_utc_datetime(model, "ended_at", self.ended_at)
        if ended_at is not None and ended_at < started_at:
            _fail(model, "ended_at", "must not be earlier than started_at")

        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "profile_id",
            _required_id(model, "profile_id", self.profile_id),
        )
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(
            self,
            "status",
            _coerce_enum(SessionStatus, model, "status", self.status),
        )
        object.__setattr__(self, "ended_at", ended_at)
        object.__setattr__(self, "notes", _optional_text(model, "notes", self.notes))
        object.__setattr__(
            self,
            "focus_modes",
            _key_modes(model, "focus_modes", self.focus_modes),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "started_at": _datetime_to_json(self.started_at),
            "status": _enum_value(self.status),
            "ended_at": (
                _datetime_to_json(self.ended_at) if self.ended_at is not None else None
            ),
            "notes": self.notes,
            "focus_modes": [_enum_value(mode) for mode in self.focus_modes],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PracticeSession:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            profile_id=_required(data, model, "profile_id"),
            started_at=_parse_utc_datetime(
                model,
                "started_at",
                _required(data, model, "started_at"),
            ),
            status=_required(data, model, "status"),
            ended_at=_parse_optional_utc_datetime(
                model,
                "ended_at",
                _optional(data, "ended_at"),
            ),
            notes=_optional(data, "notes"),
            focus_modes=_optional(data, "focus_modes", ()),
        )


@dataclass(frozen=True, slots=True)
class ScoreRecord:
    """One played score with normalized osu!mania MVP fields."""

    id: str
    session_id: str
    map_id: str
    played_at: datetime
    key_mode: KeyMode
    score: int
    accuracy: float
    combo: int | None = None
    misses: int | None = None
    grade: str | None = None
    mods: Sequence[str] = ()
    source: EvidenceSource | None = None
    source_identifier: str | None = None
    source_metadata: Mapping[str, SourceMetadataValue] | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "session_id",
            _required_id(model, "session_id", self.session_id),
        )
        object.__setattr__(self, "map_id", _required_id(model, "map_id", self.map_id))
        object.__setattr__(
            self,
            "played_at",
            _utc_datetime(model, "played_at", self.played_at),
        )
        object.__setattr__(
            self,
            "key_mode",
            _coerce_enum(KeyMode, model, "key_mode", self.key_mode),
        )
        object.__setattr__(self, "score", _non_negative_int(model, "score", self.score))
        object.__setattr__(
            self,
            "accuracy",
            _accuracy(model, "accuracy", self.accuracy),
        )
        object.__setattr__(
            self,
            "combo",
            _optional_non_negative_int(model, "combo", self.combo),
        )
        object.__setattr__(
            self,
            "misses",
            _optional_non_negative_int(model, "misses", self.misses),
        )
        object.__setattr__(self, "grade", _optional_text(model, "grade", self.grade))
        mods = _text_items(model, "mods", self.mods)
        _reject_duplicates(model, "mods", mods)
        object.__setattr__(self, "mods", mods)
        source = None
        if self.source is not None:
            source = _coerce_enum(EvidenceSource, model, "source", self.source)
        object.__setattr__(self, "source", source)
        object.__setattr__(
            self,
            "source_identifier",
            _optional_id(model, "source_identifier", self.source_identifier),
        )
        object.__setattr__(
            self,
            "source_metadata",
            _source_metadata(model, "source_metadata", self.source_metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "map_id": self.map_id,
            "played_at": _datetime_to_json(self.played_at),
            "key_mode": _enum_value(self.key_mode),
            "score": self.score,
            "accuracy": self.accuracy,
            "combo": self.combo,
            "misses": self.misses,
            "grade": self.grade,
            "mods": list(self.mods),
            "source": _enum_value(self.source) if self.source is not None else None,
            "source_identifier": self.source_identifier,
            "source_metadata": _metadata_to_dict(self.source_metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ScoreRecord:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            session_id=_required(data, model, "session_id"),
            map_id=_required(data, model, "map_id"),
            played_at=_parse_utc_datetime(
                model,
                "played_at",
                _required(data, model, "played_at"),
            ),
            key_mode=_required(data, model, "key_mode"),
            score=_required(data, model, "score"),
            accuracy=_required(data, model, "accuracy"),
            combo=_optional(data, "combo"),
            misses=_optional(data, "misses"),
            grade=_optional(data, "grade"),
            mods=_optional(data, "mods", ()),
            source=_optional(data, "source"),
            source_identifier=_optional(data, "source_identifier"),
            source_metadata=_optional(data, "source_metadata"),
        )


@dataclass(frozen=True, slots=True)
class MapMetadata:
    """Metadata for a playable map without fetching or parsing files."""

    id: str
    game: GameId
    title: str
    artist: str
    creator: str
    version: str
    key_mode: KeyMode
    difficulty: float | None = None
    source_identifier: str | None = None
    source_uri: str | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "game",
            _coerce_enum(GameId, model, "game", self.game),
        )
        object.__setattr__(self, "title", _required_text(model, "title", self.title))
        object.__setattr__(self, "artist", _required_text(model, "artist", self.artist))
        object.__setattr__(
            self,
            "creator",
            _required_text(model, "creator", self.creator),
        )
        object.__setattr__(
            self,
            "version",
            _required_text(model, "version", self.version),
        )
        object.__setattr__(
            self,
            "key_mode",
            _coerce_enum(KeyMode, model, "key_mode", self.key_mode),
        )
        object.__setattr__(
            self,
            "difficulty",
            _optional_non_negative_float(model, "difficulty", self.difficulty),
        )
        object.__setattr__(
            self,
            "source_identifier",
            _optional_id(model, "source_identifier", self.source_identifier),
        )
        object.__setattr__(
            self,
            "source_uri",
            _optional_text(model, "source_uri", self.source_uri),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "game": _enum_value(self.game),
            "title": self.title,
            "artist": self.artist,
            "creator": self.creator,
            "version": self.version,
            "key_mode": _enum_value(self.key_mode),
            "difficulty": self.difficulty,
            "source_identifier": self.source_identifier,
            "source_uri": self.source_uri,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> MapMetadata:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            game=_required(data, model, "game"),
            title=_required(data, model, "title"),
            artist=_required(data, model, "artist"),
            creator=_required(data, model, "creator"),
            version=_required(data, model, "version"),
            key_mode=_required(data, model, "key_mode"),
            difficulty=_optional(data, "difficulty"),
            source_identifier=_optional(data, "source_identifier"),
            source_uri=_optional(data, "source_uri"),
        )


@dataclass(frozen=True, slots=True)
class ReplayMetadata:
    """Registered replay metadata; this model never reads the replay file."""

    id: str
    game: GameId
    file_name: str
    registered_at: datetime
    support_status: ReplaySupportStatus
    session_id: str | None = None
    score_id: str | None = None
    map_id: str | None = None
    checksum: str | None = None
    file_size_bytes: int | None = None
    played_at: datetime | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "game",
            _coerce_enum(GameId, model, "game", self.game),
        )
        object.__setattr__(
            self,
            "file_name",
            _required_text(model, "file_name", self.file_name),
        )
        object.__setattr__(
            self,
            "registered_at",
            _utc_datetime(model, "registered_at", self.registered_at),
        )
        object.__setattr__(
            self,
            "support_status",
            _coerce_enum(
                ReplaySupportStatus,
                model,
                "support_status",
                self.support_status,
            ),
        )
        object.__setattr__(
            self,
            "session_id",
            _optional_id(model, "session_id", self.session_id),
        )
        object.__setattr__(
            self,
            "score_id",
            _optional_id(model, "score_id", self.score_id),
        )
        object.__setattr__(self, "map_id", _optional_id(model, "map_id", self.map_id))
        object.__setattr__(
            self,
            "checksum",
            _optional_text(model, "checksum", self.checksum),
        )
        object.__setattr__(
            self,
            "file_size_bytes",
            _optional_non_negative_int(
                model,
                "file_size_bytes",
                self.file_size_bytes,
            ),
        )
        object.__setattr__(
            self,
            "played_at",
            _optional_utc_datetime(model, "played_at", self.played_at),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "game": _enum_value(self.game),
            "file_name": self.file_name,
            "registered_at": _datetime_to_json(self.registered_at),
            "support_status": _enum_value(self.support_status),
            "session_id": self.session_id,
            "score_id": self.score_id,
            "map_id": self.map_id,
            "checksum": self.checksum,
            "file_size_bytes": self.file_size_bytes,
            "played_at": (
                _datetime_to_json(self.played_at) if self.played_at is not None else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReplayMetadata:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            game=_required(data, model, "game"),
            file_name=_required(data, model, "file_name"),
            registered_at=_parse_utc_datetime(
                model,
                "registered_at",
                _required(data, model, "registered_at"),
            ),
            support_status=_required(data, model, "support_status"),
            session_id=_optional(data, "session_id"),
            score_id=_optional(data, "score_id"),
            map_id=_optional(data, "map_id"),
            checksum=_optional(data, "checksum"),
            file_size_bytes=_optional(data, "file_size_bytes"),
            played_at=_parse_optional_utc_datetime(
                model,
                "played_at",
                _optional(data, "played_at"),
            ),
        )


@dataclass(frozen=True, slots=True)
class WeaknessSignal:
    """A bounded weakness observation grounded in one or more evidence refs."""

    category: WeaknessCategory
    severity: float
    confidence: float
    summary: str
    evidence_refs: Sequence[EvidenceRef]

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(
            self,
            "category",
            _coerce_enum(WeaknessCategory, model, "category", self.category),
        )
        object.__setattr__(
            self,
            "severity",
            _normalized_float(model, "severity", self.severity),
        )
        object.__setattr__(
            self,
            "confidence",
            _normalized_float(model, "confidence", self.confidence),
        )
        object.__setattr__(
            self,
            "summary",
            _required_text(model, "summary", self.summary),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _evidence_refs(
                model,
                "evidence_refs",
                self.evidence_refs,
                required_non_empty=True,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": _enum_value(self.category),
            "severity": self.severity,
            "confidence": self.confidence,
            "summary": self.summary,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> WeaknessSignal:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            category=_required(data, model, "category"),
            severity=_required(data, model, "severity"),
            confidence=_required(data, model, "confidence"),
            summary=_required(data, model, "summary"),
            evidence_refs=_required(data, model, "evidence_refs"),
        )


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Analysis output over referenced sessions and scores."""

    id: str
    profile_id: str
    generated_at: datetime
    covered_session_ids: Sequence[str]
    covered_score_ids: Sequence[str]
    weakness_signals: Sequence[WeaknessSignal]
    insufficient_evidence: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        covered_session_ids = _id_items(
            model,
            "covered_session_ids",
            self.covered_session_ids,
        )
        covered_score_ids = _id_items(
            model,
            "covered_score_ids",
            self.covered_score_ids,
        )
        if not covered_session_ids and not covered_score_ids:
            _fail(
                model,
                "covered_session_ids",
                "or covered_score_ids must contain at least one id",
            )
        weakness_signals = tuple(
            value
            if isinstance(value, WeaknessSignal)
            else WeaknessSignal.from_dict(value)
            for value in _ensure_sequence(
                model,
                "weakness_signals",
                self.weakness_signals,
            )
        )

        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "profile_id",
            _required_id(model, "profile_id", self.profile_id),
        )
        object.__setattr__(
            self,
            "generated_at",
            _utc_datetime(model, "generated_at", self.generated_at),
        )
        object.__setattr__(self, "covered_session_ids", covered_session_ids)
        object.__setattr__(self, "covered_score_ids", covered_score_ids)
        object.__setattr__(self, "weakness_signals", weakness_signals)
        object.__setattr__(
            self,
            "insufficient_evidence",
            _bool(model, "insufficient_evidence", self.insufficient_evidence),
        )
        object.__setattr__(self, "notes", _optional_text(model, "notes", self.notes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "generated_at": _datetime_to_json(self.generated_at),
            "covered_session_ids": list(self.covered_session_ids),
            "covered_score_ids": list(self.covered_score_ids),
            "weakness_signals": [
                signal.to_dict() for signal in self.weakness_signals
            ],
            "insufficient_evidence": self.insufficient_evidence,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AnalysisResult:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            profile_id=_required(data, model, "profile_id"),
            generated_at=_parse_utc_datetime(
                model,
                "generated_at",
                _required(data, model, "generated_at"),
            ),
            covered_session_ids=_required(data, model, "covered_session_ids"),
            covered_score_ids=_required(data, model, "covered_score_ids"),
            weakness_signals=_required(data, model, "weakness_signals"),
            insufficient_evidence=_optional(data, "insufficient_evidence", False),
            notes=_optional(data, "notes"),
        )


@dataclass(frozen=True, slots=True)
class TrainingTask:
    """One ordered practice task inside a training plan."""

    id: str
    goal: str
    duration_minutes: int
    evidence_refs: Sequence[EvidenceRef] = ()
    weakness_categories: Sequence[WeaknessCategory] = ()

    def __post_init__(self) -> None:
        model = type(self).__name__
        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(self, "goal", _required_text(model, "goal", self.goal))
        object.__setattr__(
            self,
            "duration_minutes",
            _positive_int(model, "duration_minutes", self.duration_minutes),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _evidence_refs(
                model,
                "evidence_refs",
                self.evidence_refs,
                required_non_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "weakness_categories",
            _weakness_categories(
                model,
                "weakness_categories",
                self.weakness_categories,
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "duration_minutes": self.duration_minutes,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "weakness_categories": [
                _enum_value(category) for category in self.weakness_categories
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrainingTask:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            goal=_required(data, model, "goal"),
            duration_minutes=_required(data, model, "duration_minutes"),
            evidence_refs=_optional(data, "evidence_refs", ()),
            weakness_categories=_optional(data, "weakness_categories", ()),
        )


@dataclass(frozen=True, slots=True)
class TrainingPlan:
    """Ordered training tasks for a profile on a specific practice date."""

    id: str
    profile_id: str
    created_at: datetime
    plan_date: date
    tasks: Sequence[TrainingTask]
    notes: str | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        tasks = tuple(
            value
            if isinstance(value, TrainingTask)
            else TrainingTask.from_dict(value)
            for value in _ensure_sequence(model, "tasks", self.tasks)
        )
        if not tasks:
            _fail(model, "tasks", "must contain at least one task")
        _reject_duplicates(model, "tasks", tuple(task.id for task in tasks))

        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "profile_id",
            _required_id(model, "profile_id", self.profile_id),
        )
        object.__setattr__(
            self,
            "created_at",
            _utc_datetime(model, "created_at", self.created_at),
        )
        object.__setattr__(
            self,
            "plan_date",
            _required_date(model, "plan_date", self.plan_date),
        )
        object.__setattr__(self, "tasks", tasks)
        object.__setattr__(self, "notes", _optional_text(model, "notes", self.notes))

    @property
    def total_duration_minutes(self) -> int:
        """Derived total duration across ordered tasks."""

        return sum(task.duration_minutes for task in self.tasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "created_at": _datetime_to_json(self.created_at),
            "plan_date": self.plan_date.isoformat(),
            "tasks": [task.to_dict() for task in self.tasks],
            "total_duration_minutes": self.total_duration_minutes,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrainingPlan:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        instance = cls(
            id=_required(data, model, "id"),
            profile_id=_required(data, model, "profile_id"),
            created_at=_parse_utc_datetime(
                model,
                "created_at",
                _required(data, model, "created_at"),
            ),
            plan_date=_parse_date(model, "plan_date", _required(data, model, "plan_date")),
            tasks=_required(data, model, "tasks"),
            notes=_optional(data, "notes"),
        )
        serialized_total = _optional(data, "total_duration_minutes")
        if serialized_total is not None:
            expected = _non_negative_int(
                model,
                "total_duration_minutes",
                serialized_total,
            )
            if expected != instance.total_duration_minutes:
                _fail(
                    model,
                    "total_duration_minutes",
                    "must equal the sum of task durations",
                )
        return instance


@dataclass(frozen=True, slots=True)
class CoachReport:
    """Human-readable coaching report linked to evidence and outputs."""

    id: str
    profile_id: str
    generated_at: datetime
    summary: str
    evidence_refs: Sequence[EvidenceRef]
    grounded_in_evidence: bool = True
    analysis_id: str | None = None
    plan_id: str | None = None

    def __post_init__(self) -> None:
        model = type(self).__name__
        evidence_refs = _evidence_refs(
            model,
            "evidence_refs",
            self.evidence_refs,
            required_non_empty=False,
        )
        grounded_in_evidence = _bool(
            model,
            "grounded_in_evidence",
            self.grounded_in_evidence,
        )
        if grounded_in_evidence and not evidence_refs:
            _fail(
                model,
                "grounded_in_evidence",
                "cannot be true when evidence_refs is empty",
            )

        object.__setattr__(self, "id", _required_id(model, "id", self.id))
        object.__setattr__(
            self,
            "profile_id",
            _required_id(model, "profile_id", self.profile_id),
        )
        object.__setattr__(
            self,
            "generated_at",
            _utc_datetime(model, "generated_at", self.generated_at),
        )
        object.__setattr__(
            self,
            "summary",
            _required_text(model, "summary", self.summary),
        )
        object.__setattr__(self, "evidence_refs", evidence_refs)
        object.__setattr__(self, "grounded_in_evidence", grounded_in_evidence)
        object.__setattr__(
            self,
            "analysis_id",
            _optional_id(model, "analysis_id", self.analysis_id),
        )
        object.__setattr__(
            self,
            "plan_id",
            _optional_id(model, "plan_id", self.plan_id),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "generated_at": _datetime_to_json(self.generated_at),
            "summary": self.summary,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "grounded_in_evidence": self.grounded_in_evidence,
            "analysis_id": self.analysis_id,
            "plan_id": self.plan_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CoachReport:
        model = cls.__name__
        if not isinstance(data, Mapping):
            _fail(model, "data", "must be a mapping")
        return cls(
            id=_required(data, model, "id"),
            profile_id=_required(data, model, "profile_id"),
            generated_at=_parse_utc_datetime(
                model,
                "generated_at",
                _required(data, model, "generated_at"),
            ),
            summary=_required(data, model, "summary"),
            evidence_refs=_required(data, model, "evidence_refs"),
            grounded_in_evidence=_optional(data, "grounded_in_evidence", True),
            analysis_id=_optional(data, "analysis_id"),
            plan_id=_optional(data, "plan_id"),
        )
