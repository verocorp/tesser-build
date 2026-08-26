from __future__ import annotations

import alpha.domain.widget as widget


class TestWidget:

    def test_a_widget_constructs_from_its_spec(self) -> None:
        spec = widget.WidgetSpec(name="a", part=widget.PartSpec(id="p"))
        built = widget.Widget(spec)
        assert str(built.identity) == spec.name
