import tesserinspect.client as client


def test_request_preserves_repository_and_baseline() -> None:
    inspect_tests_request = client.InspectTestsRequest(repo="/repo", base="HEAD~1")

    assert inspect_tests_request.repo == "/repo"
    assert inspect_tests_request.base == "HEAD~1"
