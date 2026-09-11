import html
import re

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound
from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock
from wagtail.images.blocks import ImageChooserBlock

# Rich text features, chosen per block rather than left at the site-wide default.
INLINE_FEATURES = ["bold", "italic", "link", "code"]
PROSE_FEATURES = INLINE_FEATURES + ["ol", "ul", "h3", "h4", "blockquote"]

LANGUAGES = [
    ("python", "Python"),
    ("bash", "Bash"),
    ("javascript", "JavaScript"),
    ("html+django", "Django template"),
    ("json", "JSON"),
    ("yaml", "YAML"),
    ("ini", "INI"),
    ("sql", "SQL"),
    ("text", "Plain text"),
]


class FAQBlock(blocks.StructBlock):
    question = blocks.CharBlock()
    answer = blocks.TextBlock()

    class Meta:
        icon = "help"
        label = "Question"


class HeadingBlock(blocks.StructBlock):
    text = blocks.CharBlock()
    level = blocks.ChoiceBlock(choices=[("h2", "H2"), ("h3", "H3"), ("h4", "H4")], default="h2")
    anchor = blocks.CharBlock(required=False, help_text="Optional id for links. Generated from the text when empty.")

    class Meta:
        icon = "title"
        template = "blocks/heading.html"

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["anchor"] = heading_anchor(value)
        return context


class CodeBlock(blocks.StructBlock):
    filename = blocks.CharBlock(required=False, help_text="Shown in the panel header, e.g. settings.py")
    language = blocks.ChoiceBlock(choices=LANGUAGES, default="python")
    code = blocks.TextBlock()

    class Meta:
        icon = "code"
        template = "blocks/code.html"

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context)
        context["highlighted"] = highlight_code(value["code"], value["language"])
        return context

    def get_api_representation(self, value, context=None):
        # Headless clients get the raw code plus the highlighted HTML, so they can choose.
        data = super().get_api_representation(value, context)
        data["highlighted"] = str(highlight_code(value["code"], value["language"]))
        return data


class NoteBlock(blocks.StructBlock):
    """Called CalloutBlock until chapter 3, with a "style" of tip or warning."""

    tone = blocks.ChoiceBlock(choices=[("tip", "Tip"), ("caution", "Caution")], default="tip")
    text = blocks.RichTextBlock(features=INLINE_FEATURES + ["ol", "ul"])

    class Meta:
        icon = "warning"
        template = "blocks/note.html"


class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock()
    alt = blocks.CharBlock(required=False, help_text="What the image shows, for people who can't see it")
    decorative = blocks.BooleanBlock(required=False, help_text="Tick if the image adds nothing to the text. Screen readers will skip it.")
    caption = blocks.CharBlock(required=False)

    def clean(self, value):
        value = super().clean(value)
        if not value["alt"] and not value["decorative"]:
            raise blocks.StructBlockValidationError(
                {"alt": ValidationError("Describe the image, or tick “decorative” if it adds nothing to the text.")}
            )
        return value

    class Meta:
        icon = "image"
        template = "blocks/image.html"

    def get_api_representation(self, value, context=None):
        # A front end needs a URL and dimensions, not an image ID it would have to look up.
        image = value["image"]
        rendition = image.get_rendition("width-1200|format-webp")
        return {
            "src": rendition.full_url,
            "width": rendition.width,
            "height": rendition.height,
            "alt": "" if value.get("decorative") else value["alt"],
            "caption": value["caption"],
        }


class ArticleBodyBlock(blocks.StreamBlock):
    """The one body stream shared by every article-like page type."""

    heading = HeadingBlock()
    paragraph = blocks.RichTextBlock(features=PROSE_FEATURES)
    code = CodeBlock()
    note = NoteBlock()
    table = TableBlock()
    image = ImageBlock()
    html = blocks.RawHTMLBlock(help_text="Use sparingly, for layouts no other block covers.")

    class Meta:
        # Editors may only use raw HTML a little: one per page is plenty.
        block_counts = {"html": {"max_num": 1}}


def highlight_code(code, language):
    try:
        lexer = get_lexer_by_name(language)
    except ClassNotFound:
        lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=True, classprefix="tok-")
    return mark_safe(highlight(code.rstrip("\n"), lexer, formatter))


def heading_anchor(value):
    return value.get("anchor") or slugify(value["text"])


def body_headings(body, level="h2"):
    """(anchor, text) pairs for the headings of one level in an ArticleBodyBlock stream."""
    return [
        (heading_anchor(child.value), child.value["text"])
        for child in body
        if child.block_type == "heading" and child.value["level"] == level
    ]


FAQ_HEADING = re.compile(r"\b(questions|faqs?)\b", re.IGNORECASE)


def body_faqs(body):
    """Question and answer pairs from a "Common questions" section: an h2, then h3 questions with paragraphs."""
    faqs, in_section, current = [], False, None
    for child in body:
        if child.block_type == "heading":
            if child.value["level"] == "h2":
                if in_section:
                    break
                in_section = bool(FAQ_HEADING.search(child.value["text"]))
                current = None
            elif in_section and child.value["level"] == "h3":
                current = {"question": child.value["text"], "answer": ""}
                faqs.append(current)
        elif in_section and current is not None and child.block_type == "paragraph":
            text = html.unescape(strip_tags(child.value.source))
            current["answer"] = f"{current['answer']} {' '.join(text.split())}".strip()
    return [faq for faq in faqs if faq["answer"]]


def body_word_count(body):
    words = 0
    for child in body:
        if child.block_type == "paragraph":
            words += len(strip_tags(child.value.source).split())
        elif child.block_type == "heading":
            words += len(child.value["text"].split())
        elif child.block_type == "code":
            words += len(child.value["code"].split()) // 2
        elif child.block_type == "note":
            words += len(strip_tags(child.value["text"].source).split())
    return words
