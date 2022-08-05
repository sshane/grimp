from typing import Any


class ValueObject:
    def __repr__(self) -> str:
        return "<{}: {}>".format(self.__class__.__name__, self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return hash(self) == hash(other)
        else:
            return False

    def __hash__(self) -> int:
        return hash(str(self))


class Module(ValueObject):
    """
    A Python module.

    Attributes:

        package_name:
            The name of the module's top level package.

            This is usually just the first module before the dot in the name. But in the case of namespaced packages,
            the root package could be a module higher up.
    """

    def __init__(self, name: str, top_level_package: str = "") -> None:
        """
        Args:
            name: The fully qualified name of a Python module, e.g. 'package.foo.bar'.
            top_level_package: optional, the root package of the module. Only needs to be passed for modules in a
                               namespace package.
        """
        self.name = name
        self.package_name = top_level_package or name.split(".")[0]

    def __str__(self) -> str:
        return self.name

    @property
    def root(self) -> "Module":
        """
        The root package.

        Note that for modules in namespaced packages, this may be a package with a dot in it. See self.package_name.
        """
        return Module(self.package_name, top_level_package=self.package_name)

    @property
    def parent(self) -> "Module":
        components = self.name.split(".")
        if self == self.root or len(components) == 1:
            raise ValueError("Module has no parent.")
        return Module(".".join(components[:-1]))

    def is_child_of(self, module: "Module") -> bool:
        try:
            return module == self.parent
        except ValueError:
            # If this module has no parent, then it cannot be a child of the supplied module.
            return False

    def is_descendant_of(self, module: "Module") -> bool:
        return self.name.startswith(f"{module.name}.")


class DirectImport(ValueObject):
    """
    An import between one module and another.
    """

    def __init__(
        self,
        *,
        importer: Module,
        imported: Module,
        line_number: int,
        line_contents: str,
    ) -> None:
        self.importer = importer
        self.imported = imported
        self.line_number = line_number
        self.line_contents = line_contents

    def __str__(self) -> str:
        return "{} -> {} (l. {})".format(self.importer, self.imported, self.line_number)

    def __hash__(self) -> int:
        return hash((str(self), self.line_contents))
