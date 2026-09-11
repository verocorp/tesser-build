from __future__ import annotations

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class Identity(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise errors.invalid("empty_identity", "an identity is never empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Level(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value not in (1, 2, 3):
            raise errors.invalid("invalid_level", f"level {value!r} is not a level")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class Position(ts.ValueObject):

    _value: int

    def __init__(self, value: int) -> None:
        if value < 0:
            raise errors.invalid("invalid_position", f"position {value!r} is before the first")
        object.__setattr__(self, "_value", value)

    def __int__(self) -> int:
        return serialization.canonical_int(self._value)


class Line(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class StorySpec(ts.Spec):

    def __init__(self, given: str, when: str, then: str) -> None:
        self.given = given
        self.when = when
        self.then = then


class Story(ts.ValueObject):

    _given: Line
    _when: Line
    _then: Line

    def __init__(self, spec: StorySpec) -> None:
        object.__setattr__(self, "_given", Line(spec.given))
        object.__setattr__(self, "_when", Line(spec.when))
        object.__setattr__(self, "_then", Line(spec.then))

    @property
    def given(self) -> Line:
        return self._given

    @property
    def when(self) -> Line:
        return self._when

    @property
    def then(self) -> Line:
        return self._then


class PlacementSpec(ts.Spec):

    def __init__(self, id: str, level: int, position: int) -> None:
        self.id = id
        self.level = level
        self.position = position


class Placement(ts.ValueObject):

    _identity: Identity
    _level: Level
    _position: Position

    def __init__(self, spec: PlacementSpec) -> None:
        object.__setattr__(self, "_identity", Identity(spec.id))
        object.__setattr__(self, "_level", Level(spec.level))
        object.__setattr__(self, "_position", Position(spec.position))

    @property
    def identity(self) -> Identity:
        return self._identity

    @property
    def level(self) -> Level:
        return self._level

    @property
    def position(self) -> Position:
        return self._position


class JtbdSpec(ts.Spec):

    def __init__(self, id: str, level: int, story_count: int) -> None:
        self.id = id
        self.level = level
        self.story_count = story_count


class Jtbd(ts.AggregateRoot):

    def __init__(self, spec: JtbdSpec) -> None:
        self._identity = Identity(spec.id)
        self._level = Level(spec.level)
        self._story_count = Position(spec.story_count)
        self._added: list[Story] = []

    @property
    def identity(self) -> Identity:
        return self._identity

    @property
    def level(self) -> Level:
        return self._level

    def add_story(self, story: Story) -> Placement:
        position = int(self._story_count) + len(self._added)
        self._added.append(story)
        return Placement(PlacementSpec(id=f"{self._identity}-s{position}", level=int(self._level), position=position))
