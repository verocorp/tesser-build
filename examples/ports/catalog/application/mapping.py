from __future__ import annotations

import typing

import tesser.application as ts

import catalog.application.ports.item_repository as item_repository
import catalog.application.ports.name_policy as name_policy
import catalog.domain.item as item


class MapToItemView(ts.Mapper):

    def __init__(self, view: item_repository.ItemView) -> None:
        self._id = view.id
        self._name = view.name

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name


class MapToGetItemResponse(ts.Mapper):

    def __init__(self, found: item_repository.FindItemResponse) -> None:
        self._item_view_mappers: tuple[MapToItemView, ...] = ()
        match found.outcome:
            case item_repository.ItemLookup.FOUND:
                self._item_view_mappers = tuple(MapToItemView(view=view) for view in found.items)
            case item_repository.ItemLookup.ARCHIVED:
                pass
            case item_repository.ItemLookup.MISSING:
                pass
            case _ as unreachable:
                typing.assert_never(unreachable)

    @property
    def item_view_mappers(self) -> tuple[MapToItemView, ...]:
        return self._item_view_mappers


class MapToAddItemResponse(ts.Mapper):

    def __init__(self, entity: item.Item, checked: name_policy.CheckNameResponse) -> None:
        self._item_view_mappers: tuple[MapToAddedItemView, ...] = ()
        match checked.verdict:
            case name_policy.NameVerdict.ALLOWED:
                self._item_view_mappers = (MapToAddedItemView(entity=entity),)
            case name_policy.NameVerdict.RESERVED:
                pass
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._reason = checked.reason

    @property
    def item_view_mappers(self) -> tuple[MapToAddedItemView, ...]:
        return self._item_view_mappers

    @property
    def reason(self) -> str:
        return self._reason


class MapToAddedItemView(ts.Mapper):

    def __init__(self, entity: item.Item) -> None:
        self._id = entity.id()
        self._name = entity.name()

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name
