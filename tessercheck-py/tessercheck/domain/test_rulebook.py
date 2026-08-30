from __future__ import annotations

import pytest

import tessercheck.domain.rulebook as rulebook


def test_a_violation_spec_carries_all_four_fields() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('only-message; a clause'))\n"
    )
    with pytest.raises(RuntimeError, match="exactly the four"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_violation_call_takes_one_violation_spec() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation('p', 1, 'TB040', 'a head; a clause')\n"
    )
    with pytest.raises(RuntimeError, match="exactly the four"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_violation_spec_may_name_its_fields() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, code='TB040', message='a head; a clause'))\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    assert "| TB040 | a clause |" in rendered


def test_a_violation_code_must_be_literal_or_bound() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec(p, 1, computed, 'head; a clause'))\n"
    )
    with pytest.raises(RuntimeError, match="neither a literal"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_one_clause_carries_one_code() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', 'a head; one shared clause'))\n"
        "        Violation(ViolationSpec('p', 1, 'TB041', 'b head; one shared clause'))\n"
    )
    with pytest.raises(RuntimeError, match="one clause has one code"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_clause_emitted_by_two_owners_renders_both() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Codebase:\n"
        "    def __init__(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', 'a head; one shared clause'))\n"
        "    def violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 2, 'TB040', 'b head; one shared clause'))\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    assert "| one shared clause | checked source file · debt marker |" in rendered


def test_a_message_without_a_normative_clause_is_rejected() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', 'a bare head with no tail'))\n"
    )
    with pytest.raises(RuntimeError, match="normative clause"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_clause_carrying_a_hole_is_rejected() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', f'head; a clause about {target}'))\n"
    )
    with pytest.raises(RuntimeError, match="not a literal"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_message_hole_with_no_reader_name_is_rejected() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', f'{mystery} head; a clause'))\n"
    )
    with pytest.raises(RuntimeError, match="extend HOLE_NAMES"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_subject_with_no_applies_to_entry_is_rejected() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Codebase:\n"
        "    def _unmapped_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', 'head; a clause'))\n"
    )
    with pytest.raises(RuntimeError, match="APPLIES_TO"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_checks_module_without_the_block_name_map_is_rejected() -> None:
    checks_text = (
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', 'head; a clause'))\n"
    )
    with pytest.raises(RuntimeError, match="TS_NAME_BY_BLOCK"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_a_row_carries_the_code_the_reach_and_every_source_line() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'first shape; the shared tail'))\n"
        "        Violation(ViolationSpec('p', 2, 'TB020', 'second shape; the shared tail'))\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    rows = [line for line in rendered.splitlines() if line.startswith("| TB")]
    assert rows == [
        "| TB020 | the shared tail | every module | first shape · second shape "
        "| domain/checks.py:5,6 | NONE |"
    ]


def test_a_hole_prefix_is_stripped_from_the_fires_when_shape() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', f'{where} says nothing; the tail'))\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    assert "| TB020 | the tail | every module | says nothing |" in rendered


def test_an_assert_literal_containing_the_clause_is_the_fixture() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the shared tail'))\n"
    )
    modules = (
        (
            "a/test_thing.py",
            "def test_the_tail_is_locked() -> None:\n"
            "    assert x == [], 'saw a finding about the shared tail here'\n"
            "def helper() -> None:\n"
            "    assert y, 'the shared tail'\n",
        ),
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text, modules)))
    assert "| domain/checks.py:5 | test_the_tail_is_locked |" in rendered


def test_contracts_pair_each_section_id_with_its_name() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    text = (
        "[importlinter]\n"
        "root_packages =\n"
        "    app\n"
        "\n"
        "[importlinter:contract:domain-is-pure]\n"
        "name = domain imports nothing\n"
        "type = forbidden\n"
        "\n"
        "[importlinter:contract:client-is-thin]\n"
        "name = the client DTOs stay thin\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text, contracts_text=text)))
    assert "| domain-is-pure | domain imports nothing |" in rendered
    assert "| client-is-thin | the client DTOs stay thin |" in rendered


def test_render_reports_an_uncovered_rule_as_none() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    assert (
        "| TB020 | the rendered tail | every module | a shape | domain/checks.py:5 | NONE |"
        in rendered
    )


def test_render_names_the_covering_test_and_the_contract_rows() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    modules = (
        (
            "a/test_thing.py",
            "def test_the_rendered_tail_holds() -> None:\n"
            "    assert findings == ['the rendered tail']\n",
        ),
    )
    rendered = str(
        rulebook.Rulebook(
            rulebook.RulebookSpec(
                checks_text,
                modules,
                "[importlinter:contract:domain-is-pure]\nname = domain imports nothing\n",
            )
        )
    )
    assert "| test_the_rendered_tail_holds |" in rendered
    assert "| domain-is-pure | domain imports nothing |" in rendered
    assert "modules under the top-level `protocol/` package" in rendered


def test_render_without_the_protocol_package_constant_is_rejected() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "class Module:\n"
        "    def comment_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB020', 'a shape; the rendered tail'))\n"
    )
    with pytest.raises(RuntimeError, match="PROTOCOL_PACKAGE"):
        rulebook.Rulebook(rulebook.RulebookSpec(checks_text))


def test_an_empty_string_binding_drops_the_row() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class ThingSpec:\n"
        "    def __init__(self, where: str = '') -> None:\n"
        "        self.where = where\n"
        "class Module:\n"
        "    def __init__(self, spec: ThingSpec) -> None:\n"
        "        pass\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', f'{where} is wrong; the dropped tail'))\n"
        "        Violation(ViolationSpec('p', 1, 'TB041', 'a head; the kept tail'))\n"
        "THING = ThingSpec()\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    assert "the dropped tail" not in rendered
    assert "the kept tail" in rendered


def test_a_spec_without_an_init_binds_nothing_and_does_not_crash() -> None:
    checks_text = (
        "TS_NAME_BY_BLOCK: dict = {}\n"
        "PROTOCOL_PACKAGE: str = 'protocol'\n"
        "class EmptySpec:\n"
        "    pass\n"
        "class Module:\n"
        "    def __init__(self, spec: EmptySpec) -> None:\n"
        "        pass\n"
        "    def stray_violations(self) -> None:\n"
        "        Violation(ViolationSpec('p', 1, 'TB040', 'a shape; the rendered tail'))\n"
    )
    rendered = str(rulebook.Rulebook(rulebook.RulebookSpec(checks_text)))
    assert "the rendered tail" in rendered
