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
    """
    def __init__(self, name: str) -> None:
        """
        Args:
            name: The fully qualified name of a Python module, e.g. 'package.foo.bar'.
        """
        self.name = name

    def __str__(self) -> str:
        return self.name

    @property
    def package_name(self) -> str:
        return self.name.split('.')[0]

    def is_child_of(self, module: 'Module') -> bool:
        return self.name.split('.')[:-1] == module.name.split('.')

    def is_descendant_of(self, module: 'Module') -> bool:
        return self.name.startswith(f'{module.name}.')


class DirectImport(ValueObject):
    """
    An import between one module and another.
    """
    def __init__(
        self, *,
        importer: Module, imported: Module,
        line_number: int, line_contents: str,
    ) -> None:
        self.importer = importer
        self.imported = imported
        self.line_number = line_number
        self.line_contents = line_contents

    def __str__(self) -> str:
        return "{} -> {} (l. {})".format(self.importer, self.imported, self.line_number)

    def __hash__(self) -> int:
        return hash((str(self), self.line_contents))
