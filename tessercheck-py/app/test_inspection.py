import app


def test_inspection_app_builds_once_and_closes_idempotently() -> None:
    inspection_app = app.InspectionApp()

    assert inspection_app.inspection.client is inspection_app.inspection.client
    inspection_app.close()
    inspection_app.close()
