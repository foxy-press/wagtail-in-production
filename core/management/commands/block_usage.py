import json
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import TextField
from django.db.models.functions import Cast
from wagtail.fields import StreamField
from wagtail.models import get_page_models


def block_types(raw):
    """Every block type name in a stream's raw JSON, at any depth."""
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict) and "type" in item:
                yield item["type"]
                yield from block_types(item.get("value"))
            else:
                yield from block_types(item)
    elif isinstance(raw, dict):
        for value in raw.values():
            yield from block_types(value)


def stored_streams(model, fields, drafts):
    """(url_path, {field: raw JSON}) for every page, read without Wagtail parsing the stream.

    Parsing drops block types the code no longer defines, which are exactly the ones you may be looking for.
    """
    if drafts:
        for page in model.objects.select_related("latest_revision"):
            content = page.latest_revision.content if page.latest_revision else {}
            yield page.url_path, {name: json.loads(content.get(name) or "[]") for name in fields}
        return
    casts = {f"raw_{name}": Cast(name, TextField()) for name in fields}
    for row in model.objects.annotate(**casts).values("url_path", *casts):
        yield row["url_path"], {name: json.loads(row[f"raw_{name}"] or "[]") for name in fields}


class Command(BaseCommand):
    help = "Count StreamField block types across all pages, or list the pages that use one block type."

    def add_arguments(self, parser):
        parser.add_argument("block_type", nargs="?", help="List the pages that use this block type")
        parser.add_argument("--drafts", action="store_true", help="Read each page's latest revision instead of the live version")

    def handle(self, block_type=None, drafts=False, **options):
        counts = Counter()
        for model in get_page_models():
            fields = [f.name for f in model._meta.get_fields() if isinstance(f, StreamField) and f.model is model]
            if model._meta.abstract or not fields:
                continue
            for url_path, streams in stored_streams(model, fields, drafts):
                found = Counter()
                for raw in streams.values():
                    found.update(block_types(raw))
                counts.update(found)
                if block_type and found[block_type]:
                    self.stdout.write(f"{found[block_type]:>4}  {url_path}  ({model.__name__})")
        if not block_type:
            for name, count in counts.most_common():
                self.stdout.write(f"{count:>6}  {name}")
