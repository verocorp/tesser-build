import tesser.application as ts
import tesser.errors as errors

import tesserinspect.application.ports as ports
import tesserinspect.client as client
import tesserinspect.domain as domain


class MapToReadCheckoutRequest(ts.Mapper, ports.ReadCheckoutRequest):
    def __init__(
        self,
        checkout_location: domain.CheckoutLocation,
        baseline_reference: domain.BaselineReference,
    ) -> None:
        super().__init__(repo=str(checkout_location), base=str(baseline_reference))


class MapToInventorySpec(ts.Mapper, domain.InventorySpec):
    def __init__(self, read_checkout_response: ports.ReadCheckoutResponse) -> None:
        super().__init__(
            sources=read_checkout_response.sources,
            changes=read_checkout_response.changes
            + tuple(
                (path, previous, staged + unstaged)
                for path, previous, staged, unstaged in read_checkout_response.working_tree_changes
            ),
            paths=read_checkout_response.paths,
        )


class MapToInspectTestsResponse(ts.Mapper, client.InspectTestsResponse):
    def __init__(
        self,
        read_checkout_response: ports.ReadCheckoutResponse,
        inventory: domain.Inventory,
    ) -> None:
        super().__init__(
            baseline=read_checkout_response.baseline,
            changes=read_checkout_response.changes,
            changed_tests=tuple(str(path) for path in inventory.changed_tests()),
            candidates=tuple(
                (
                    str(candidate.kind()),
                    str(candidate.path()),
                    int(candidate.line()),
                    str(candidate.symbol()),
                    str(candidate.reason()),
                )
                for candidate in inventory.candidates()
            ),
            working_tree_changes=read_checkout_response.working_tree_changes,
        )


class InspectionService(ts.ApplicationService):
    def __init__(self, checkout_reader: ports.CheckoutReader) -> None:
        self._checkout_reader = checkout_reader

    def inspect_tests(
        self, inspect_tests_request: client.InspectTestsRequest
    ) -> client.InspectTestsResponse:
        try:
            checkout_location = domain.CheckoutLocation(inspect_tests_request.repo)
            baseline_reference = domain.BaselineReference(inspect_tests_request.base)
            read_checkout_response = self._checkout_reader.read_checkout(
                MapToReadCheckoutRequest(checkout_location, baseline_reference)
            )
            inventory = domain.Inventory(MapToInventorySpec(read_checkout_response))
        except errors.DomainError as domain_error:
            raise client.InspectionFailed(
                domain_error.code, domain_error.message
            ) from domain_error
        return MapToInspectTestsResponse(read_checkout_response, inventory)
