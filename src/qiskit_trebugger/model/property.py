"""Module to implement a property of a circuit.
"""

from collections import defaultdict


class Property:
    """Implements the property of a transpiler pass as a data structure."""

    LARGE_VALUE_THRESHOLD = 2000

    def __init__(self, name, prop_type, value, state) -> None:
        self.name = name
        self.prop_type = prop_type
        self.state = state

        if prop_type in (list, defaultdict) and (len(value) > self.LARGE_VALUE_THRESHOLD):
            print(len(value))
            self.value = "LARGE_VALUE"
        else:
            self.value = value

    def __repr__(self) -> str:
        return f"{self.name} ({self.prop_type.__name__}) : {self.value}"

    def __eq__(self, other):
        if self.name != other.name:
            return False
        if self.prop_type != other.prop_type:
            return False
        if self.state != other.state:
            return False
        if self.value != other.value:
            return False
        return True
