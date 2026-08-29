from __future__ import annotations

import alpha.application.alpha_service as alpha_service
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import alpha.domain.widget as widget


class TestAlphaServiceMappers:

    def test_an_add_request_maps_to_a_widget_spec_holding_its_own_name_as_the_part(self) -> None:
        spec = alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p"))
        assert spec.name == "a"
        assert spec.part.id == "a"

    def test_an_add_request_maps_to_the_part_it_names(self) -> None:
        assert alpha_service.MapToPartSpec(client.AddRequest(name="a", part="p")).id == "p"

    def test_a_take_request_maps_to_the_part_it_names(self) -> None:
        assert alpha_service.MapToTakenPartSpec(client.TakeRequest(name="a", part="q")).id == "q"

    def test_a_loaded_widget_maps_to_a_spec_carrying_its_stored_part(self) -> None:
        spec = alpha_service.MapToLoadedWidgetSpec(widget_repository.LoadWidgetResponse(name="a", part="p"))
        assert spec.name == "a"
        assert spec.part.id == "p"

    def test_a_widget_maps_to_a_save_request_carrying_its_name_and_part(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        request = alpha_service.MapToSaveWidgetRequest(built)
        assert request.name == "a"
        assert request.part == "a"

    def test_a_name_maps_to_a_load_request(self) -> None:
        assert alpha_service.MapToLoadWidgetRequest(widget.Name("a")).name == "a"

    def test_a_name_maps_to_a_find_request(self) -> None:
        assert alpha_service.MapToFindWidgetRequest(widget.Name("a")).name == "a"

    def test_a_widget_maps_to_a_check_request(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        assert alpha_service.MapToCheckRequest(built).name == "a"

    def test_a_widget_maps_to_an_add_response(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        assert alpha_service.MapToAddResponse(built).name == "a"

    def test_a_widget_maps_to_a_take_response_carrying_the_part_it_now_holds(self) -> None:
        built = widget.Widget(alpha_service.MapToWidgetSpec(client.AddRequest(name="a", part="p")))
        built.take(alpha_service.MapToTakenPartSpec(client.TakeRequest(name="a", part="q")))
        response = alpha_service.MapToTakeResponse(built)
        assert response.name == "a"
        assert response.part == "q"
