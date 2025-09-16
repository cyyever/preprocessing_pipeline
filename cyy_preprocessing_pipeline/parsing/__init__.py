from collections.abc import Iterable, Sequence

import bs4

from .parse_score import parse_score
from .regex_parsing import parse_floats, parse_pattern


def approximately_match_token(a: str, b: str, threshold: float = 0.9) -> bool:
    a_set = set(a.lower())
    b_set = set(b.lower())
    return len(a_set.intersection(b_set)) / len(a_set.union(b_set)) > threshold


def approximately_match_tokens(
    tokens: list[str], pred_tokens: list[str | tuple[Sequence[str], Iterable[str]]]
) -> list[str | None]:
    # case sensitive
    if not tokens:
        return []
    token_len = len(tokens)
    tags: list[str | None] = []
    while tokens:
        token = tokens[0]
        if not pred_tokens:
            tokens = tokens[1:]
            tags.append(None)
            continue
        has_match = False
        for idx, element in enumerate(pred_tokens):
            if isinstance(element, str):
                if approximately_match_token(token, element):
                    has_match = True
                    tokens = tokens[1:]
                    tags.append(element)
                    pred_tokens = pred_tokens[idx + 1 :]
                    break
            else:
                phase = element[0]
                if len(tokens) >= len(phase) and all(
                    approximately_match_token(tokens[i], phase[i])
                    for i in range(len(phase))
                ):
                    has_match = True
                    tags += element[1]
                    tokens = tokens[len(phase) :]
                    pred_tokens = pred_tokens[1:]
                    break
        if not has_match:
            tags.append(None)
            tokens = tokens[1:]
    assert len(tags) == token_len
    return tags


def parsing_html_tag(html: str, preferred_tag: str) -> str:
    # Parse HTML using BeautifulSoup
    soup = bs4.BeautifulSoup(html, "html.parser")
    result = ""
    for child in soup:
        match child:
            case bs4.element.NavigableString():
                result += child.get_text()
            case bs4.element.Tag():
                last_tag_text = child.get_text()
                tag_name = child.name.lower()
                if tag_name == preferred_tag.lower():
                    return child.get_text()
                result += f"<{tag_name}>{last_tag_text}</{tag_name}>"
            case _:
                raise NotImplementedError(child)
    return result


def parse_html_tag(html: str, preferred_tag: str) -> str:
    return parsing_html_tag(html=html, preferred_tag=preferred_tag)


__all__ = [
    "approximately_match_token",
    "approximately_match_tokens",
    "parsing_html_tag",
    "parse_html_tag",
    "parse_floats",
    "parse_pattern",
    "parse_score",
]
