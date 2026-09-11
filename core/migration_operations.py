from django.utils.deconstruct import deconstructible
from wagtail.blocks.migrations.operations import BaseBlockOperation


@deconstructible
class MapValueOperation(BaseBlockOperation):
    """Replace old values of a simple block (a ChoiceBlock, CharBlock...) using a mapping.

    Values not in the mapping are left alone, so the operation is safe to run twice.
    """

    def __init__(self, mapping):
        super().__init__()
        self.mapping = mapping

    def apply(self, block_value):
        return self.mapping.get(block_value, block_value)

    @property
    def operation_name_fragment(self):
        return "map_values"
