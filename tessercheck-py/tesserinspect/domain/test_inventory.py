import pytest
import tesser.errors as errors

import tesserinspect.domain as domain


def test_unchanged_aliased_reader_constrains_new_helper_without_calling_it() -> None:
    inventory = domain.Inventory(
        domain.InventorySpec(
            sources=(
                (
                    "tests/test_new.py",
                    "def helper(value=1):\n    return value\ndef test_new():\n    assert helper() == 1\n",
                ),
                (
                    "meta/test_contract.py",
                    "from inspect import getsource as source\nclass TestContract:\n    def test_literal_arguments(self):\n        return source('tests/test_new.py')\n",
                ),
            ),
            changes=(("tests/test_new.py", "", "?"),),
            paths=(),
        )
    )

    assert any(
        str(row.kind()) == "helper" and str(row.symbol()) == "helper"
        for row in inventory.candidates()
    )
    assert any(
        str(row.kind()) == "source-reader"
        and str(row.path()) == "meta/test_contract.py"
        and str(row.symbol()) == "TestContract.test_literal_arguments"
        for row in inventory.candidates()
    )


def test_fixture_alias_parameters_imports_and_ancestor_configuration_are_candidates() -> (
    None
):
    inventory = domain.Inventory(
        domain.InventorySpec(
            sources=(
                (
                    "tests/unit/test_new.py",
                    "from helpers import build as make\ndef test_new(database):\n    assert make(database)\n",
                ),
                (
                    "tests/conftest.py",
                    "from pytest import fixture as provide\n@provide(name='database')\ndef connection():\n    return 1\n",
                ),
            ),
            changes=(("tests/unit/test_new.py", "", "A"),),
            paths=(
                "pyproject.toml",
                "conftest.py",
                "tests/conftest.py",
                "tests/unit/pytest.ini",
                "elsewhere/pytest.ini",
            ),
        )
    )

    assert {
        str(row.path())
        for row in inventory.candidates()
        if str(row.kind()) == "collection"
    } == {"pyproject.toml", "conftest.py", "tests/conftest.py", "tests/unit/pytest.ini"}
    assert any(
        str(row.kind()) == "fixture-definition" and str(row.symbol()) == "connection"
        for row in inventory.candidates()
    )
    assert any(
        str(row.kind()) == "fixture-reference" and str(row.symbol()) == "database"
        for row in inventory.candidates()
    )
    assert any(
        str(row.kind()) == "import-reference" and str(row.symbol()) == "make"
        for row in inventory.candidates()
    )


def test_deleted_and_renamed_tests_retain_old_locations() -> None:
    inventory = domain.Inventory(
        domain.InventorySpec(
            sources=(),
            changes=(
                ("test_deleted.py", "", "D"),
                ("utility.py", "test_old.py", "R100"),
            ),
            paths=(),
        )
    )

    assert tuple(str(path) for path in inventory.changed_tests()) == (
        "test_deleted.py",
        "test_old.py",
    )


def test_inventory_is_deterministic_and_equal_for_reordered_input() -> None:
    first = domain.Inventory(
        domain.InventorySpec(
            sources=(
                ("test_z.py", "def test_z():\n    pass\n"),
                ("test_a.py", "def test_a():\n    pass\n"),
            ),
            changes=(("test_z.py", "", "M"), ("test_a.py", "", "A")),
            paths=(),
        )
    )
    second = domain.Inventory(
        domain.InventorySpec(
            sources=(
                ("test_a.py", "def test_a():\n    pass\n"),
                ("test_z.py", "def test_z():\n    pass\n"),
            ),
            changes=(("test_a.py", "", "A"), ("test_z.py", "", "M")),
            paths=(),
        )
    )

    assert first == second
    assert first.candidates() == second.candidates()


def test_inventory_rejects_malformed_source_instead_of_returning_no_candidates() -> (
    None
):
    with pytest.raises(errors.DomainError, match="broken.py"):
        domain.Inventory(
            domain.InventorySpec(
                sources=(("broken.py", "def broken(:\n"),), changes=(), paths=()
            )
        )


def test_ordinary_data_reader_remains_a_conservative_candidate() -> None:
    inventory = domain.Inventory(
        domain.InventorySpec(
            sources=(
                (
                    "test_data.py",
                    "def test_data():\n    return open('data.csv').read()\n",
                ),
            ),
            changes=(("test_new.py", "", "?"),),
            paths=(),
        )
    )

    assert any(str(row.kind()) == "source-reader" for row in inventory.candidates())


def test_no_changed_test_does_not_infer_a_dependency_selection() -> None:
    inventory = domain.Inventory(
        domain.InventorySpec(
            sources=(("app.py", "value = 1\n"),),
            changes=(("app.py", "", "M"),),
            paths=(),
        )
    )

    assert inventory.changed_tests() == ()
    assert inventory.candidates() == ()


def test_deleted_collection_configuration_remains_visible() -> None:
    inventory = domain.Inventory(
        domain.InventorySpec(
            sources=(),
            changes=(("tests/test_new.py", "", "?"), ("pytest.ini", "", "D")),
            paths=(),
        )
    )

    assert any(
        str(row.kind()) == "collection" and str(row.path()) == "pytest.ini"
        for row in inventory.candidates()
    )


def test_checkout_coordinates_validate_and_round_trip_by_value() -> None:
    checkout_location = domain.CheckoutLocation("/repo")
    baseline_reference = domain.BaselineReference("HEAD~1")

    assert domain.CheckoutLocation(str(checkout_location)) == checkout_location
    assert domain.BaselineReference(str(baseline_reference)) == baseline_reference
    assert domain.CheckoutLocation("/different") != checkout_location
    assert domain.BaselineReference("HEAD") != baseline_reference
    with pytest.raises(errors.DomainError):
        domain.CheckoutLocation("")
    with pytest.raises(errors.DomainError):
        domain.BaselineReference("--help")
