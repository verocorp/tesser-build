from shortlink import ShortLink, ShortLinkSpec


def _valid_spec() -> ShortLinkSpec:
    return ShortLinkSpec(
        slug="spring-sale", target_url="https://example.com/spring", active=True
    )


def test_constructs_from_spec() -> None:
    spec = _valid_spec()
    link = ShortLink(spec)
    assert link.active is spec.active
