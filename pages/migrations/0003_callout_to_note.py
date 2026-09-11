from django.db import migrations
from wagtail.blocks.migrations.migrate_operation import MigrateStreamData
from wagtail.blocks.migrations.operations import RenameStreamChildrenOperation, RenameStructChildrenOperation

from core.migration_operations import MapValueOperation

# Renames "callout" blocks to "note", their "style" child to "tone", and the "warning" value to "caution".
# Applies to live pages, drafts and every revision, so compare and revert keep working.
CALLOUT_TO_NOTE = [
    (RenameStreamChildrenOperation(old_name="callout", new_name="note"), ""),
    (RenameStructChildrenOperation(old_name="style", new_name="tone"), "note"),
    (MapValueOperation({"warning": "caution"}), "note.tone"),
]


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0002_note_block_definition"),
        ("wagtailcore", "0069_log_entry_jsonfield"),
    ]

    operations = [
        MigrateStreamData(
            app_name="pages",
            model_name="ServicePage",
            field_name="body",
            operations_and_block_paths=CALLOUT_TO_NOTE,
        ),
    ]
