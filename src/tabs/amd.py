
from ui.common import load_module
from ui.dynamic_page import DynamicPage


class AmdPage(DynamicPage):
    def __init__(self, log_fn):
        super().__init__(load_module("amd"), log_fn)
        self._log = log_fn


