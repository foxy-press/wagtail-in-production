"""Convert legacy blog HTML into BlogPage StreamField data."""

import re
import uuid

from bs4 import BeautifulSoup

INLINE_KEEP = {"b", "i", "a", "code", "br"}
INLINE_RENAME = {"strong": "b", "em": "i"}


def block(block_type, value):
    return {"type": block_type, "value": value, "id": str(uuid.uuid4())}


def clean_inline(node):
    """Reduce a fragment to the inline tags Wagtail rich text stores, keeping only href on links."""
    for tag in list(node.find_all(True)):
        if tag.name in INLINE_RENAME:
            tag.name = INLINE_RENAME[tag.name]
        if tag.name not in INLINE_KEEP:
            tag.unwrap()
            continue
        href = tag.get("href") if tag.name == "a" else None
        tag.attrs = {"href": href} if href else {}
    return node.decode_contents().strip()


def html_to_blocks(html):
    """Map the top-level elements of an <article> to ArticleBodyBlock children."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article") or soup
    blocks = []
    for node in article.find_all(recursive=False):
        name = node.name
        if name == "h1":
            continue  # the title becomes the page title, not a block
        if name in ("h2", "h3", "h4"):
            blocks.append(block("heading", {"text": node.get_text(" ", strip=True), "level": name, "anchor": node.get("id", "")}))
        elif name == "p":
            text = clean_inline(node)
            if text:
                blocks.append(block("paragraph", f"<p>{text}</p>"))
        elif name in ("ul", "ol"):
            items = "".join(f"<li>{clean_inline(li)}</li>" for li in node.find_all("li", recursive=False))
            blocks.append(block("paragraph", f"<{name}>{items}</{name}>"))
        elif name == "pre":
            code = node.find("code") or node
            language = next((c[9:] for c in code.get("class", []) if c.startswith("language-")), "text")
            blocks.append(block("code", {"filename": "", "language": language, "code": code.get_text()}))
        elif name == "aside":
            tone = "caution" if "warning" in node.get("class", []) else "tip"
            blocks.append(block("note", {"tone": tone, "text": f"<p>{clean_inline(node)}</p>"}))
        else:
            # Anything unexpected is kept, fenced in the one raw HTML block a page may have (chapter 2).
            if not any(b["type"] == "html" for b in blocks):
                blocks.append(block("html", str(node)))
    return blocks


def intro_from(html):
    soup = BeautifulSoup(html, "html.parser")
    first = soup.find("p")
    return re.sub(r"\s+", " ", first.get_text(" ", strip=True)) if first else ""
