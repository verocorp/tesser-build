from __future__ import annotations

import tesser.testing as ts

import tessercheck.domain.checks as checks


@ts.helper
def _spec(
    sources: tuple[tuple[str, str, str | None, bool], ...] = (),
    declared: str = "app",
    exports: tuple[str, ...] = (),
    imports: tuple[str, ...] = (),
    stdlib: tuple[str, ...] = (),
    base: tuple[tuple[str, str, str | None, bool], ...] = (
        (
            "app/domain/thing.py",
            "app.domain.thing",
            "import tesser.domain as ts\n"
            "class ThingSpec(ts.Spec):\n"
            "    def __init__(self, text: str) -> None:\n"
            "        self.text = text\n"
            "class Thing(ts.AggregateRoot):\n"
            "    def __init__(self, spec: ThingSpec) -> None:\n"
            "        self.text = spec.text\n",
            False,
        ),
    ),
    kernel_init: tuple[tuple[str, str, str | None, bool], ...] = (
        ("kernel/__init__.py", "kernel", "", True),
    ),
    money: tuple[tuple[str, str, str | None, bool], ...] = (
        (
            "kernel/money.py",
            "kernel.money",
            "import tesser.domain as ts\n"
            "class Money(ts.ValueObject):\n"
            "    _amount: int\n"
            "    def __init__(self, amount: int) -> None:\n"
            "        if amount < 0:\n"
            '            raise ValueError(f"negative: {amount}")\n'
            '        object.__setattr__(self, "_amount", amount)\n',
            False,
        ),
    ),
) -> checks.CodebaseSpec:
    return checks.CodebaseSpec(
        sources=base + kernel_init + money + sources,
        declared=declared,
        nested=(),
        symlinked=(),
        exports=exports,
        imports=imports,
        stdlib=stdlib,
    )


def test_a_second_export_declaration_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(exports=("one", "two"))).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "a tree has one exported kernel, so a declaration carries at most one "
        "'export <dir>' line" in f
        for f in findings
    ), findings


def test_an_export_that_is_no_package_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(exports=("ghost",))).violations()
    )
    assert any(
        "this tree exports 'ghost' but no such package exists; "
        "an export names a package at the tree root" in f
        for f in findings
    ), findings


def test_an_export_never_takes_a_shell_or_kernel_name() -> None:
    for taken in ("srv", "kernel", "tests", "protocol", "bootstrap"):
        findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(exports=(taken,))).violations()
    )
        assert any(
            "an exported kernel never takes the name of the kernel package "
            "or the app shell" in f
            for f in findings
        ), (taken, findings)


def test_kernel_is_a_package_never_a_module() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(("kernel.py", "kernel", "X = 1\n", False),),
            kernel_init=(),
            money=(),
        )).violations()
    )
    assert any(
        "kernel.py:1: TB041 kernel is a kernel module at the tree root; "
        "kernel is a package, never a module" in f
        for f in findings
    ), findings


def test_a_kernel_init_only_reexports_from_its_own_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/__init__.py",
                    "kernel",
                    "import app.domain.thing as thing\nX = 1\n",
                    True,
                ),
            ),
            kernel_init=(),
        )).violations()
    )
    assert any(
        "kernel imports app.domain.thing; "
        "a kernel __init__ only re-exports from its own kernel" in f
        for f in findings
    ), findings
    assert any(
        "kernel __init__ declares code; "
        "a kernel __init__ only re-exports from its own kernel" in f
        for f in findings
    ), findings


def test_every_kernel_class_declares_its_block() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/loose.py",
                    "kernel.loose",
                    "import tesser.domain as ts\nclass Bare:\n    pass\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "kernel.loose.Bare declares no ts.* base; "
        "every kernel class declares its block" in f
        for f in findings
    ), findings


def test_a_kernel_holds_only_domain_kinds() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/svc.py",
                    "kernel.svc",
                    "import tesser.domain as ts\n"
                    "import tesser.application as tsa\n"
                    "class Svc(tsa.ApplicationService):\n"
                    "    pass\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "a kernel holds only domain kinds — "
        "value objects, entities, aggregates, and specs" in f
        for f in findings
    ), findings


def test_kernel_statement_totality() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/loose.py",
                    "kernel.loose",
                    "import tesser.domain as ts\n"
                    "LIMIT = 3\n"
                    "def helper() -> int:\n"
                    "    return LIMIT\n"
                    "print(LIMIT)\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any("a kernel constant is Final" in f for f in findings), findings
    assert any(
        "a kernel function declares itself with @ts.function" in f for f in findings
    ), findings
    assert any(
        "a kernel module holds only imports, classes, declared functions, "
        "and Final constants" in f
        for f in findings
    ), findings


def test_kernel_tesser_import_rules() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/wrong.py",
                    "kernel.wrong",
                    "import tesser.adapters as ts\n"
                    "class Money(ts.ValueObject):\n"
                    "    pass\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "a kernel module imports only tesser.domain" in f for f in findings
    ), findings
    absent = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/bare.py",
                    "kernel.bare",
                    "from typing import Final\nLIMIT: Final[int] = 3\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "a kernel module imports tesser.domain exactly once, as ts" in f
        for f in absent
    ), absent


def test_kernel_import_allowlist() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/prices.py",
                    "kernel.prices",
                    "import tesser.domain as ts\n"
                    "from decimal import Decimal\n"
                    "import kernel.money\n"
                    "import app.domain.thing\n"
                    "import requests\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "kernel.prices imports app.domain.thing; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in findings
    ), findings
    assert any(
        "kernel.prices imports requests; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in findings
    ), findings
    assert not any("imports decimal" in f for f in findings), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_a_declared_kernel_import_is_legal_in_a_kernel() -> None:
    def grown(imports: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
                sources=(
                    (
                        "kernel/prices.py",
                        "kernel.prices",
                        "import tesser.domain as ts\n"
                        "import money_kernel\n"
                        "class PriceSpec(ts.Spec):\n"
                        "    def __init__(self, text: str) -> None:\n"
                        "        self.text = text\n",
                        False,
                    ),
                ),
                imports=imports,
            )).violations()
    )

    assert not any(
        "imports money_kernel" in f for f in grown(("money_kernel",))
    ), grown(("money_kernel",))
    assert any("imports money_kernel" in f for f in grown(())), grown(())


def test_pure_roles_may_import_kernels() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "app/domain/price.py",
                    "app.domain.price",
                    "import tesser.domain as ts\n"
                    "from kernel.money import Money\n"
                    "import money_kernel\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, money: Money) -> None:\n"
                    "        self.money = money\n",
                    False,
                ),
            ),
            imports=("money_kernel",),
        )).violations()
    )
    assert not any("app/domain/price.py" in f for f in findings), findings


def test_an_undeclared_package_in_a_pure_role_is_still_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "app/domain/price.py",
                    "app.domain.price",
                    "import tesser.domain as ts\n"
                    "import money_kernel\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "app.domain.price imports money_kernel; domain, client, and application "
        "import only their context, their kernels, their tesser package, "
        "and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_kernel_test_reaches_only_its_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/test_money.py",
                    "kernel.test_money",
                    "import tesser.testing as ts\n"
                    "from kernel.money import Money\n"
                    "import app.domain.thing\n"
                    "def test_money() -> None:\n"
                    "    assert Money(1) == Money(1)\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "kernel.test_money imports app.domain.thing, but a test placed in "
        "a kernel reaches no context; "
        "a test reaches only what its placement allows" in f
        for f in findings
    ), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_an_exported_kernel_is_governed_like_a_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                ("shells/__init__.py", "shells", "", True),
                (
                    "shells/svc.py",
                    "shells.svc",
                    "import tesser.domain as ts\n"
                    "import tesser.application as tsa\n"
                    "class Svc(tsa.ApplicationService):\n"
                    "    pass\n",
                    False,
                ),
                (
                    "app/domain/price.py",
                    "app.domain.price",
                    "import tesser.domain as ts\n"
                    "from shells.svc import Svc\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
            exports=("shells",),
        )).violations()
    )
    assert any(
        "a kernel holds only domain kinds" in f for f in findings
    ), findings
    assert not any("app/domain/price.py" in f for f in findings), findings


def test_a_context_shaped_export_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                ("beta/__init__.py", "beta", "", True),
                (
                    "beta/domain/policy.py",
                    "beta.domain.policy",
                    "import tesser.domain as ts\n"
                    "class PolicySpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
            exports=("beta",),
        )).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "a bounded context's domain is never exported — a kernel is not a context" in f
        for f in findings
    ), findings


def test_an_import_declaration_never_names_this_tree() -> None:
    for declared in ("srv", "kernel", "tests", "app"):
        findings = tuple(
            f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
            for v in checks.Codebase(_spec(imports=(declared,))).violations()
        )
        assert any(
            "an import declaration names an installed external kernel, "
            "never something the walk governs" in f
            for f in findings
        ), (declared, findings)


def test_an_import_declaration_never_names_the_stdlib() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            imports=("subprocess", "os.path"),
            stdlib=("os", "subprocess"),
        )).violations()
    )
    assert (
        sum(
            "the pure stdlib is already legal and the rest of it is never a kernel" in f
            for f in findings
        )
        == 2
    ), findings


def test_an_unused_import_declaration_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(imports=("money_kernel",))).violations()
    )
    assert any(
        "an import declaration that legalizes nothing is itself a finding" in f
        for f in findings
    ), findings


def test_kernel_siblings_import_each_other_in_both_kernel_shapes() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                ("shells/__init__.py", "shells", "", True),
                (
                    "shells/base.py",
                    "shells.base",
                    "import tesser.domain as ts\n"
                    "class BaseSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
                (
                    "shells/rich.py",
                    "shells.rich",
                    "import tesser.domain as ts\n"
                    "from shells.base import BaseSpec\n"
                    "class RichSpec(ts.Spec):\n"
                    "    def __init__(self, base: BaseSpec) -> None:\n"
                    "        self.base = base\n",
                    False,
                ),
                (
                    "kernel/rates.py",
                    "kernel.rates",
                    "import tesser.domain as ts\n"
                    "from kernel.money import Money\n"
                    "class RateSpec(ts.Spec):\n"
                    "    def __init__(self, money: Money) -> None:\n"
                    "        self.money = money\n",
                    False,
                ),
            ),
            exports=("shells",),
        )).violations()
    )
    assert not any("shells/rich.py" in f for f in findings), findings
    assert not any("kernel/rates.py" in f for f in findings), findings


def test_the_exported_kernel_never_imports_the_private_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                ("shells/__init__.py", "shells", "", True),
                (
                    "shells/base.py",
                    "shells.base",
                    "import tesser.domain as ts\n"
                    "from kernel.money import Money\n"
                    "class BaseSpec(ts.Spec):\n"
                    "    def __init__(self, money: Money) -> None:\n"
                    "        self.money = money\n",
                    False,
                ),
            ),
            exports=("shells",),
        )).violations()
    )
    assert any(
        "shells.base imports kernel.money; a kernel imports only its "
        "kernel, tesser.domain, declared kernels, and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_declared_import_matches_on_the_package_boundary() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/prices.py",
                    "kernel.prices",
                    "import tesser.domain as ts\n"
                    "import money_kernel.sub\n"
                    "import money_kernel_evil\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
            ),
            imports=("money_kernel",),
        )).violations()
    )
    assert any("imports money_kernel_evil" in f for f in findings), findings
    assert not any("imports money_kernel.sub" in f for f in findings), findings


def test_a_kernel_import_is_only_trusted_when_its_module_was_walked() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "app/domain/price.py",
                    "app.domain.price",
                    "import tesser.domain as ts\n"
                    "from kernel.money import Money\n"
                    "from kernel.vendored.impure import Client\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, money: Money) -> None:\n"
                    "        self.money = money\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any("imports kernel.vendored.impure" in f for f in findings), findings
    assert not any("imports kernel.money" in f for f in findings), findings


def test_a_pure_role_kernel_import_needs_the_kernel_to_exist() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "app/domain/price.py",
                    "app.domain.price",
                    "import tesser.domain as ts\n"
                    "from kernel.money import Money\n"
                    "class PriceSpec(ts.Spec):\n"
                    "    def __init__(self, money: Money) -> None:\n"
                    "        self.money = money\n",
                    False,
                ),
            ),
            kernel_init=(),
            money=(),
        )).violations()
    )
    assert any(
        "app.domain.price imports kernel.money; domain, client, and application "
        "import only their context, their kernels, their tesser package, "
        "and the pure stdlib" in f
        for f in findings
    ), findings


def test_a_role_named_subpackage_of_the_fixed_kernel_stays_kernel_governed() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                ("kernel/domain/__init__.py", "kernel.domain", "", True),
                (
                    "kernel/domain/svc.py",
                    "kernel.domain.svc",
                    "import tesser.domain as ts\n"
                    "import tesser.application as tsa\n"
                    "class Svc(tsa.ApplicationService):\n"
                    "    pass\n",
                    False,
                ),
            ),
        )).violations()
    )
    assert any(
        "a kernel holds only domain kinds" in f for f in findings
    ), findings
    assert not any("is not a context module" in f for f in findings), findings


def test_a_kernel_init_rejects_a_near_miss_package() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/__init__.py",
                    "kernel",
                    "import kernelish.money as money\n",
                    True,
                ),
                ("kernelish/__init__.py", "kernelish", "", True),
                (
                    "kernelish/money.py",
                    "kernelish.money",
                    "import app.domain.thing\n",
                    False,
                ),
            ),
            kernel_init=(),
        )).violations()
    )
    assert any(
        "kernel imports kernelish.money; "
        "a kernel __init__ only re-exports from its own kernel" in f
        for f in findings
    ), findings


def test_a_member_form_reexport_in_a_kernel_init_is_legal() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                (
                    "kernel/__init__.py",
                    "kernel",
                    "from kernel.money import Money as Money\n",
                    True,
                ),
            ),
            kernel_init=(),
        )).violations()
    )
    assert not any("kernel/__init__.py" in f for f in findings), findings


def test_an_export_naming_a_bare_module_is_a_finding() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(("shells.py", "shells", "X = 1\n", False),),
            exports=("shells",),
        )).violations()
    )
    assert len(findings) == 1, findings
    assert any(
        "an export names a package at the tree root" in f for f in findings
    ), findings


def test_a_kernel_test_may_reach_the_trees_other_kernel() -> None:
    findings = tuple(
        f"{v.path()}:{int(v.line())}: {v.code()} {v.text()}"
        for v in checks.Codebase(_spec(
            sources=(
                ("shells/__init__.py", "shells", "", True),
                (
                    "shells/base.py",
                    "shells.base",
                    "import tesser.domain as ts\n"
                    "class BaseSpec(ts.Spec):\n"
                    "    def __init__(self, text: str) -> None:\n"
                    "        self.text = text\n",
                    False,
                ),
                (
                    "kernel/test_money.py",
                    "kernel.test_money",
                    "from kernel.money import Money\n"
                    "from shells.base import BaseSpec\n"
                    "def test_money() -> None:\n"
                    "    assert Money(1) == Money(1)\n",
                    False,
                ),
            ),
            exports=("shells",),
        )).violations()
    )
    assert not any("kernel/test_money.py" in f for f in findings), findings
