from __future__ import annotations

import pytest

import tesser.testing as ts

import specification.domain as domain
import tesser.errors as errors


@ts.helper
def jtbd_spec(id: str = "j-root", level: int = 1, story_count: int = 0) -> domain.JtbdSpec:
    return domain.JtbdSpec(id=id, level=level, story_count=story_count)


@ts.helper
def story_spec(given: str = "a jtbd exists", when: str = "I click add story", then: str = "I see it nested") -> domain.StorySpec:
    return domain.StorySpec(given=given, when=when, then=then)


class TestIdentity:

    def test_an_identity_reads_back_as_written(self) -> None:
        assert str(domain.Identity("j-root")) == "j-root"

    def test_an_empty_identity_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            domain.Identity("")
        assert caught.value.code == "empty_identity"

    def test_identity_equality(self) -> None:
        assert domain.Identity("j-root") == domain.Identity("j-root")
        assert domain.Identity("j-root") != domain.Identity("j-page-c")


class TestLevel:

    def test_a_level_is_one_of_the_three(self) -> None:
        assert int(domain.Level(2)) == 2

    def test_a_fourth_level_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            domain.Level(4)
        assert caught.value.code == "invalid_level"

    def test_level_equality(self) -> None:
        assert domain.Level(1) == domain.Level(1)
        assert domain.Level(1) != domain.Level(2)


class TestPosition:

    def test_a_position_before_the_first_is_refused(self) -> None:
        with pytest.raises(errors.DomainError) as caught:
            domain.Position(-1)
        assert caught.value.code == "invalid_position"

    def test_position_equality(self) -> None:
        assert domain.Position(0) == domain.Position(0)
        assert domain.Position(0) != domain.Position(1)


class TestStory:

    def test_a_story_carries_its_three_lines(self) -> None:
        story = domain.Story(story_spec(given="g", when="w", then="t"))
        assert str(story.given) == "g"
        assert str(story.when) == "w"
        assert str(story.then) == "t"

    def test_story_equality(self) -> None:
        assert domain.Story(story_spec()) == domain.Story(story_spec())
        assert domain.Story(story_spec()) != domain.Story(story_spec(then="something else"))


class TestPlacement:

    def test_a_placement_decomposes_into_its_parts(self) -> None:
        placement = domain.Placement(domain.PlacementSpec(id="j-root-s0", level=1, position=0))
        assert str(placement.identity) == "j-root-s0"
        assert int(placement.level) == 1
        assert int(placement.position) == 0

    def test_placement_equality(self) -> None:
        assert domain.Placement(domain.PlacementSpec(id="j-root-s0", level=1, position=0)) == domain.Placement(
            domain.PlacementSpec(id="j-root-s0", level=1, position=0)
        )
        assert domain.Placement(domain.PlacementSpec(id="j-root-s0", level=1, position=0)) != domain.Placement(
            domain.PlacementSpec(id="j-root-s1", level=1, position=1)
        )


class TestJtbd:

    def test_a_jtbd_is_identified_and_leveled_by_its_spec(self) -> None:
        jtbd = domain.Jtbd(jtbd_spec(id="j-page-c", level=2))
        assert jtbd.identity == domain.Identity("j-page-c")
        assert jtbd.level == domain.Level(2)

    def test_the_first_story_is_placed_after_the_ones_already_there(self) -> None:
        jtbd = domain.Jtbd(jtbd_spec(id="j-root", level=1, story_count=3))
        placement = jtbd.add_story(domain.Story(story_spec()))
        assert str(placement.identity) == "j-root-s3"
        assert int(placement.position) == 3

    def test_a_story_takes_the_level_of_the_jtbd_it_hangs_on(self) -> None:
        jtbd = domain.Jtbd(jtbd_spec(level=2))
        placement = jtbd.add_story(domain.Story(story_spec()))
        assert int(placement.level) == 2

    def test_a_second_story_is_placed_after_the_first(self) -> None:
        jtbd = domain.Jtbd(jtbd_spec(story_count=0))
        jtbd.add_story(domain.Story(story_spec()))
        placement = jtbd.add_story(domain.Story(story_spec(given="another")))
        assert int(placement.position) == 1
        assert str(placement.identity) == "j-root-s1"
