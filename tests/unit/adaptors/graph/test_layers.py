from __future__ import annotations

import itertools

import pytest  # type: ignore

from grimp import PackageDependency, Route
from grimp.adaptors.graph import ImportGraph
from grimp.exceptions import NoSuchContainer


def _single_chain_route(*modules: str) -> Route:
    return Route(
        heads=frozenset({modules[0]}),
        middle=tuple(modules[1:-1]),
        tails=frozenset({modules[-1]}),
    )


class TestSingleOrNoContainer:
    @pytest.mark.parametrize("specify_container", (True, False))
    def test_no_illegal_imports(self, specify_container: bool):
        graph = self._build_legal_graph()

        result = self._analyze(graph, specify_container=specify_container)

        assert result == frozenset()

    @pytest.mark.parametrize("specify_container", (True, False))
    @pytest.mark.parametrize(
        "importer",
        ("mypackage.medium", "mypackage.medium.orange", "mypackage.medium.orange.beta"),
    )
    @pytest.mark.parametrize(
        "imported",
        ("mypackage.high", "mypackage.high.yellow", "mypackage.high.yellow.alpha"),
    )
    def test_direct_illegal_within_one_package(
        self, specify_container: bool, importer: str, imported: str
    ):
        graph = self._build_legal_graph()
        graph.add_import(importer=importer, imported=imported)

        result = self._analyze(graph, specify_container=specify_container)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            _single_chain_route(importer, imported),
                        }
                    ),
                ),
            }
        )

    @pytest.mark.parametrize("specify_container", (True, False))
    @pytest.mark.parametrize(
        "start",
        ("mypackage.medium", "mypackage.medium.orange", "mypackage.medium.orange.beta"),
    )
    @pytest.mark.parametrize(
        "end",
        ("mypackage.high", "mypackage.high.yellow", "mypackage.high.yellow.alpha"),
    )
    @pytest.mark.parametrize(
        "route_middle",
        [
            ["mypackage.nickel"],
            ["mypackage.bismuth", "mypackage.gold"],
            [
                "mypackage.iron",
                "mypackage.gold.alpha",
                "mypackage.plutonium.yellow.beta",
            ],
            [
                "mypackage.boron.purple",
                "mypackage.iron",
                "mypackage.boron.green",
                "mypackage.boron.green.gamma",
            ],
        ],
    )
    def test_indirect_illegal_within_one_package(
        self, specify_container: bool, start: str, end: str, route_middle: list[str]
    ):
        graph = self._build_legal_graph()
        import_pairs = _pairwise([start] + route_middle + [end])
        for importer, imported in import_pairs:
            graph.add_import(importer=importer, imported=imported)

        result = self._analyze(graph, specify_container=specify_container)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            Route(
                                heads=frozenset({start}),
                                middle=tuple(route_middle),
                                tails=frozenset({end}),
                            ),
                        }
                    ),
                )
            }
        )

    def test_two_package_dependencies(self):
        graph = self._build_legal_graph()
        graph.add_import(
            importer="mypackage.low.white", imported="mypackage.medium.orange.beta"
        )
        graph.add_import(
            importer="mypackage.medium.orange", imported="mypackage.high.green"
        )

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.low",
                    downstream="mypackage.medium",
                    routes=frozenset(
                        {
                            _single_chain_route(
                                "mypackage.low.white", "mypackage.medium.orange.beta"
                            ),
                        }
                    ),
                ),
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            _single_chain_route(
                                "mypackage.medium.orange", "mypackage.high.green"
                            ),
                        }
                    ),
                ),
            }
        )

    def test_multiple_illegal_routes_same_ends(self):
        graph = self._build_legal_graph()
        # Route 1.
        graph.add_import(
            importer="mypackage.medium.orange", imported="mypackage.tungsten"
        )
        graph.add_import(importer="mypackage.tungsten", imported="mypackage.copper")
        graph.add_import(importer="mypackage.copper", imported="mypackage.high.green")
        # Route 2.
        graph.add_import(
            importer="mypackage.medium.orange", imported="mypackage.gold.delta"
        )
        graph.add_import(
            importer="mypackage.gold.delta", imported="mypackage.high.green"
        )

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            _single_chain_route(
                                "mypackage.medium.orange",
                                "mypackage.tungsten",
                                "mypackage.copper",
                                "mypackage.high.green",
                            ),
                            _single_chain_route(
                                "mypackage.medium.orange",
                                "mypackage.gold.delta",
                                "mypackage.high.green",
                            ),
                        }
                    ),
                ),
            }
        )

    def test_multiple_illegal_routes_different_ends_in_same_layer(self):
        graph = self._build_legal_graph()
        # Route 1.
        graph.add_import(
            importer="mypackage.medium.orange", imported="mypackage.tungsten"
        )
        graph.add_import(importer="mypackage.tungsten", imported="mypackage.copper")
        graph.add_import(importer="mypackage.copper", imported="mypackage.high.green")
        # Route 2.
        graph.add_import(
            importer="mypackage.medium.orange.beta", imported="mypackage.gold.delta"
        )
        graph.add_import(
            importer="mypackage.gold.delta", imported="mypackage.high.yellow"
        )

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            _single_chain_route(
                                "mypackage.medium.orange",
                                "mypackage.tungsten",
                                "mypackage.copper",
                                "mypackage.high.green",
                            ),
                            _single_chain_route(
                                "mypackage.medium.orange.beta",
                                "mypackage.gold.delta",
                                "mypackage.high.yellow",
                            ),
                        }
                    ),
                ),
            }
        )

    def test_illegal_route_with_extra_ends(self):
        graph = self._build_legal_graph()
        # Route 1.
        graph.add_import(
            importer="mypackage.medium.orange", imported="mypackage.tungsten"
        )
        graph.add_import(importer="mypackage.tungsten", imported="mypackage.copper")
        graph.add_import(importer="mypackage.copper", imported="mypackage.high.green")
        # Extra firsts.
        graph.add_import(
            importer="mypackage.medium.orange.beta", imported="mypackage.tungsten"
        )
        graph.add_import(importer="mypackage.medium.red", imported="mypackage.tungsten")
        # Extra lasts.
        graph.add_import(importer="mypackage.copper", imported="mypackage.high")
        graph.add_import(
            importer="mypackage.copper", imported="mypackage.high.yellow.alpha"
        )

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            Route(
                                heads=frozenset(
                                    {
                                        "mypackage.medium.orange",
                                        "mypackage.medium.orange.beta",
                                        "mypackage.medium.red",
                                    }
                                ),
                                middle=(
                                    "mypackage.tungsten",
                                    "mypackage.copper",
                                ),
                                tails=frozenset(
                                    {
                                        "mypackage.high.green",
                                        "mypackage.high",
                                        "mypackage.high.yellow.alpha",
                                    }
                                ),
                            ),
                        }
                    ),
                ),
            }
        )

    def _build_legal_graph(self):
        graph = ImportGraph()
        for module in (
            "mypackage",
            "mypackage.high",
            "mypackage.high.green",
            "mypackage.high.blue",
            "mypackage.high.yellow",
            "mypackage.high.yellow.alpha",
            "mypackage.medium",
            "mypackage.medium.orange",
            "mypackage.medium.orange.beta",
            "mypackage.medium.red",
            "mypackage.low",
            "mypackage.low.black",
            "mypackage.low.white",
            "mypackage.low.white.gamma",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(
            importer="mypackage.high.green", imported="mypackage.medium.orange"
        )
        graph.add_import(
            importer="mypackage.high.green", imported="mypackage.low.white.gamma"
        )
        graph.add_import(
            importer="mypackage.medium.orange", imported="mypackage.low.white"
        )
        graph.add_import(importer="mypackage.high.blue", imported="mypackage.utils")
        graph.add_import(importer="mypackage.utils", imported="mypackage.medium.red")

        return graph

    def _analyze(
        self, graph: ImportGraph, specify_container: bool = False
    ) -> frozenset[PackageDependency]:
        if specify_container:
            return graph.find_illegal_dependencies_for_layers(
                layers=("high", "medium", "low"),
                containers={"mypackage"},
            )
        else:
            return graph.find_illegal_dependencies_for_layers(
                layers=("mypackage.high", "mypackage.medium", "mypackage.low"),
            )


class TestMultiplePackages:
    @pytest.mark.parametrize(
        "importer",
        ("medium", "medium.orange", "medium.orange.beta"),
    )
    @pytest.mark.parametrize(
        "imported",
        ("high", "high.yellow", "high.yellow.alpha"),
    )
    def test_direct_illegal_across_two_packages(self, importer: str, imported: str):
        graph = self._build_legal_graph()
        graph.add_import(importer=importer, imported=imported)

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="medium",
                    downstream="high",
                    routes=frozenset(
                        {
                            _single_chain_route(importer, imported),
                        }
                    ),
                ),
            }
        )

    @pytest.mark.parametrize(
        "start",
        ("medium", "medium.orange", "medium.orange.beta"),
    )
    @pytest.mark.parametrize(
        "end",
        ("high", "high.yellow", "high.yellow.alpha"),
    )
    @pytest.mark.parametrize(
        "route_middle",
        [
            ["nickel"],
            ["bismuth", "gold"],
            [
                "iron",
                "gold.alpha",
                "plutonium.yellow.beta",
            ],
            [
                "boron.purple",
                "iron",
                "boron.green",
                "boron.green.gamma",
            ],
        ],
    )
    def test_indirect_illegal_across_two_packages(
        self, start: str, end: str, route_middle: list[str]
    ):
        graph = self._build_legal_graph()
        import_pairs = _pairwise([start] + route_middle + [end])
        for importer, imported in import_pairs:
            graph.add_import(importer=importer, imported=imported)

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="medium",
                    downstream="high",
                    routes=frozenset(
                        {
                            Route(
                                heads=frozenset({start}),
                                middle=tuple(route_middle),
                                tails=frozenset({end}),
                            ),
                        }
                    ),
                )
            }
        )

    def _build_legal_graph(self):
        graph = ImportGraph()
        for module in (
            "high",
            "high.green",
            "high.blue",
            "high.yellow",
            "high.yellow.alpha",
            "medium",
            "medium.orange",
            "medium.orange.beta",
            "medium.red",
            "low",
            "low.black",
            "low.white",
            "low.white.gamma",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(importer="high.green", imported="medium.orange")
        graph.add_import(importer="high.green", imported="low.white.gamma")
        graph.add_import(importer="medium.orange", imported="low.white")
        graph.add_import(importer="high.blue", imported="utils")
        graph.add_import(importer="utils", imported="medium.red")

        return graph

    def _analyze(self, graph: ImportGraph) -> frozenset[PackageDependency]:
        return graph.find_illegal_dependencies_for_layers(
            layers=("high", "medium", "low"),
        )


class TestMultipleContainers:
    def test_no_illegal_imports(self):
        graph = self._build_legal_graph()

        result = self._analyze(graph)

        assert result == frozenset()

    def test_multiple_illegal_imports(self):
        graph = self._build_legal_graph()
        graph.add_import(importer="one.low.white", imported="one.high.green")
        graph.add_import(
            importer="one.low.white",
            imported="two.medium.pink",
        )
        graph.add_import(
            importer="two.medium.pink",
            imported="one.high.green",
        )
        graph.add_import(importer="one.low.white", imported="one.high.brown")
        graph.add_import(
            importer="two.medium.pink.delta", imported="two.high.yellow.gamma"
        )

        result = self._analyze(graph)

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="one.low",
                    downstream="one.high",
                    routes=frozenset(
                        {
                            _single_chain_route("one.low.white", "one.high.green"),
                            _single_chain_route("one.low.white", "one.high.brown"),
                            Route(
                                heads=frozenset({"one.low.white"}),
                                middle=("two.medium.pink",),
                                # N.B. two.medium.pink ->  one.high.blue is in the
                                # legal imports added in _build_legal_graph.
                                tails=frozenset({"one.high.green", "one.high.blue"}),
                            ),
                        }
                    ),
                ),
                PackageDependency(
                    upstream="two.medium",
                    downstream="two.high",
                    routes=frozenset(
                        {
                            _single_chain_route(
                                "two.medium.pink.delta", "two.high.yellow.gamma"
                            ),
                        }
                    ),
                ),
            }
        )

    def _build_legal_graph(self):
        graph = ImportGraph()
        for module in (
            "one",
            "one.high",
            "one.high.green",
            "one.high.blue",
            "one.high.yellow",
            "one.high.yellow.alpha",
            "one.medium",
            "one.medium.orange",
            "one.medium.orange.beta",
            "one.medium.red",
            "one.low",
            "one.low.black",
            "one.low.white",
            "one.low.white.gamma",
            "two",
            "two.high",
            "two.high.brown",
            "two.high.yellow",
            "two.high.yellow.gamma",
            "two.medium",
            "two.medium.pink",
            "two.medium.pink.delta",
            "two.medium.purple",
            "two.low",
            "two.low.black",
            "two.low.black.epsilon",
        ):
            graph.add_module(module)

        # Add some 'legal' imports.
        graph.add_import(importer="one.high.yellow", imported="one.low.white.gamma")
        graph.add_import(importer="one.high.brown", imported="one.utils")
        graph.add_import(importer="one.utils", imported="one.medium.pink")
        graph.add_import(importer="two.medium", imported="two.low")
        graph.add_import(importer="two.medium.purple", imported="two.low")
        graph.add_import(importer="two.medium", imported="two.low.black.epsilon")
        # Imports between low layers to high layers across containers aren't illegal.
        graph.add_import(importer="two.medium.pink", imported="one.high.blue")

        return graph

    def _analyze(self, graph: ImportGraph) -> frozenset[PackageDependency]:
        return graph.find_illegal_dependencies_for_layers(
            layers=("high", "medium", "low"),
            containers={"one", "two"},
        )


class TestInvalidContainers:
    @pytest.mark.parametrize("missing_container", ("one", "two"))
    def test_single_missing_container(self, missing_container: str):
        graph = ImportGraph()
        containers = {"one", "two"}

        for container in containers - {missing_container}:
            graph.add_module(container)

        with pytest.raises(
            NoSuchContainer, match=f"Container {missing_container} does not exist."
        ):
            graph.find_illegal_dependencies_for_layers(
                layers=("high", "medium", "low"),
                containers=containers,
            )


class TestMissingLayers:
    @pytest.mark.parametrize("specify_container", (True, False))
    def test_missing_layer_is_ignored_with_single_or_no_container(
        self, specify_container: bool
    ):
        graph = ImportGraph()

        # Add an import, but the rest of the layers don't exist.
        graph.add_module("mypackage")
        graph.add_module("mypackage.medium")
        graph.add_module("mypackage.high")
        graph.add_import(
            importer="mypackage.medium.blue", imported="mypackage.high.green"
        )

        if specify_container:
            result = graph.find_illegal_dependencies_for_layers(
                layers=("high", "medium", "low"),
                containers={"mypackage"},
            )
        else:
            result = graph.find_illegal_dependencies_for_layers(
                layers=("mypackage.high", "mypackage.medium", "mypackage.low"),
            )

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="mypackage.medium",
                    downstream="mypackage.high",
                    routes=frozenset(
                        {
                            _single_chain_route(
                                "mypackage.medium.blue", "mypackage.high.green"
                            )
                        }
                    ),
                )
            }
        )

    def test_missing_layer_is_ignored_with_multiple_containers(self):
        graph = ImportGraph()
        containers = {"one", "two"}
        for container in containers:
            graph.add_module(container)

        # Add an import, but the rest of the layers don't exist.
        graph.add_module("two.medium")
        graph.add_module("two.high")
        graph.add_import(importer="two.medium.blue", imported="two.high.green")

        result = graph.find_illegal_dependencies_for_layers(
            layers=("high", "medium", "low"),
            containers=containers,
        )

        assert result == frozenset(
            {
                PackageDependency(
                    upstream="two.medium",
                    downstream="two.high",
                    routes=frozenset(
                        {_single_chain_route("two.medium.blue", "two.high.green")}
                    ),
                )
            }
        )


def _pairwise(iterable):
    """
    Return successive overlapping pairs taken from the input iterable.
    pairwise('ABCDEFG') --> AB BC CD DE EF FG

    TODO: Replace with itertools.pairwise once on Python 3.10.
    """
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)
