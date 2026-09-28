import tesser.testing as ts

import tesserinspect.application as application
import tesserinspect.application.ports as ports
import tesserinspect.client as client


@ts.fake
class CheckoutReader(ports.CheckoutReader):
    def read_checkout(
        self, read_checkout_request: ports.ReadCheckoutRequest
    ) -> ports.ReadCheckoutResponse:
        assert read_checkout_request.repo == "/repo"
        assert read_checkout_request.base == "HEAD"
        return ports.ReadCheckoutResponse(
            baseline="abc",
            sources=(("test_new.py", "def test_new():\n    pass\n"),),
            changes=(("test_new.py", "", "?"),),
            paths=("test_new.py",),
            working_tree_changes=(("test_new.py", "", "?", "?"),),
        )


def test_service_maps_git_facts_through_inventory_to_public_response() -> None:
    inspection_service = application.InspectionService(CheckoutReader())

    inspect_tests_response = inspection_service.inspect_tests(
        client.InspectTestsRequest(repo="/repo", base="HEAD")
    )

    assert inspect_tests_response.baseline == "abc"
    assert inspect_tests_response.changes == (("test_new.py", "", "?"),)
    assert inspect_tests_response.changed_tests == ("test_new.py",)
    assert inspect_tests_response.candidates[0][:4] == (
        "changed-test",
        "test_new.py",
        0,
        "",
    )
