import tesserinspect.client as client
import tesserinspect.component as component


def test_component_publishes_the_inspection_contract() -> None:
    inspection = component.Inspection(component.Config(component.Spec()))

    inspection_client: client.InspectionClient = inspection.client
    assert inspection_client is not None
    inspection.close()
    inspection.close()
