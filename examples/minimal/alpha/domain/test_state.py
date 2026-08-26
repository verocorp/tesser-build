import alpha.domain.state as state


def test_a_state_is_a_closed_set() -> None:
    assert tuple(state.State) == (state.State.ON, state.State.OFF)
