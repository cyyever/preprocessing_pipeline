import bs4

from .types import BIOTokenList, CanonicalTags, make_bio_span


def tokenize(txt: str) -> list[str]:
    for mark in ":;,.":
        if mark in txt:
            txt = txt.replace(mark, f" {mark} ")
    lines = txt.strip().split(" ")
    return [line for line in lines if line]


def html2bio(
    html: str,
    canonical_tags: CanonicalTags,
) -> BIOTokenList:
    tokens: BIOTokenList = []
    if not html:
        return []

    soup = bs4.BeautifulSoup(html, "html.parser")
    last_tag_text = None
    for child in soup:
        match child:
            case bs4.element.NavigableString():
                if child.get_text() == last_tag_text:
                    last_tag_text = None
                    continue
                tokens += tokenize(child.get_text())
            case bs4.element.Tag():
                last_tag_text = child.get_text()
                words = tokenize(last_tag_text)
                if not words:
                    continue
                if child.name.lower() != "span":
                    tokens += words
                    continue
                classes: str | list[str] = child.attrs.get("class", [])
                classes = [classes] if isinstance(classes, str) else list(classes)
                if not classes:
                    tokens += words
                    continue
                tag: str | None = None
                for c in classes:
                    tag = canonical_tags.match(c)
                    if tag is not None:
                        break
                if tag is None:
                    tokens += words
                    continue
                tokens.append(make_bio_span(words, tag))
            case _:
                raise NotImplementedError(child)
    return tokens
