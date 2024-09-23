"""Implement a button with value
"""

import ipywidgets as widgets


class ButtonWithValue(widgets.Button):
    """Implements a button with value by inheriting from
    Button class.
    """

    def __init__(self, *args, **kwargs):
        self.value = kwargs["value"]
        kwargs.pop("value", None)
        super().__init__(*args, **kwargs)
