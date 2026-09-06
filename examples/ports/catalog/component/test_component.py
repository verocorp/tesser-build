from __future__ import annotations

import catalog.client as client
import catalog.component as component


def test_the_wired_client_serves_an_item_it_stored() -> None:
    catalog_client = component.Catalog().client
    catalog_client.add(client.AddItemRequest(id="a1", name="Anvil"))
    get_item_response = catalog_client.get(client.GetItemRequest(id="a1"))
    assert tuple((view.id, view.name) for view in get_item_response.items) == (("a1", "Anvil"),)


def test_the_wired_client_refuses_the_reserved_name() -> None:
    catalog_client = component.Catalog().client
    add_item_response = catalog_client.add(client.AddItemRequest(id="c3", name="admin"))
    assert add_item_response.items == ()
    assert add_item_response.reason == "name is reserved"


def test_the_wired_client_accepts_a_name_that_is_not_reserved() -> None:
    catalog_client = component.Catalog().client
    add_item_response = catalog_client.add(client.AddItemRequest(id="a1", name="Anvil"))
    assert tuple((v.id, v.name) for v in add_item_response.items) == (("a1", "Anvil"),)
    assert add_item_response.reason == ""


def test_the_wired_client_lists_everything_it_stored() -> None:
    catalog_client = component.Catalog().client
    catalog_client.add(client.AddItemRequest(id="a1", name="Anvil"))
    catalog_client.add(client.AddItemRequest(id="b2", name="Bellows"))
    list_items_response = catalog_client.list(client.ListItemsRequest())
    assert tuple(view.name for view in list_items_response.items) == ("Anvil", "Bellows")


def test_a_wiring_hands_out_one_service() -> None:
    catalog = component.Catalog()
    assert catalog.client is catalog.client


def test_two_wirings_do_not_share_what_they_stored() -> None:
    first = component.Catalog()
    second = component.Catalog()
    first.client.add(client.AddItemRequest(id="a1", name="Anvil"))
    get_item_response = second.client.get(client.GetItemRequest(id="a1"))
    assert get_item_response.items == ()
