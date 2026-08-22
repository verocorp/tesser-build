from __future__ import annotations

import catalog.client.client as client
import catalog.component.component as wire


def test_the_wired_client_serves_an_item_it_stored() -> None:
    svc = wire.Catalog().client
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    got = svc.get(client.GetItemRequest(id="a1"))
    assert tuple((view.id, view.name) for view in got.items) == (("a1", "Anvil"),)


def test_the_wired_client_refuses_the_reserved_name() -> None:
    svc = wire.Catalog().client
    added = svc.add(client.AddItemRequest(id="c3", name="admin"))
    assert added.items == ()
    assert added.reason == "name is reserved"


def test_the_wired_client_accepts_a_name_that_is_not_reserved() -> None:
    svc = wire.Catalog().client
    added = svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    assert tuple((v.id, v.name) for v in added.items) == (("a1", "Anvil"),)
    assert added.reason == ""


def test_the_wired_client_lists_everything_it_stored() -> None:
    svc = wire.Catalog().client
    svc.add(client.AddItemRequest(id="a1", name="Anvil"))
    svc.add(client.AddItemRequest(id="b2", name="Bellows"))
    listed = svc.list(client.ListItemsRequest())
    assert tuple(view.name for view in listed.items) == ("Anvil", "Bellows")


def test_a_wiring_hands_out_one_service() -> None:
    component = wire.Catalog()
    assert component.client is component.client


def test_two_wirings_do_not_share_what_they_stored() -> None:
    first = wire.Catalog()
    second = wire.Catalog()
    first.client.add(client.AddItemRequest(id="a1", name="Anvil"))
    got = second.client.get(client.GetItemRequest(id="a1"))
    assert got.items == ()
