from collections.abc import Iterable

type BIOSpan = tuple[list[str], list[str]]
type BIOTokenList = list[BIOSpan | str]


class CanonicalTags:
    def __init__(self, tags: Iterable[str]) -> None:
        self.tags: list[str] = list(tags)
        assert self.tags
        self._lower = [t.lower() for t in self.tags]

    def match(self, tag: str) -> str | None:
        tag_lower = tag.lower()
        if tag_lower in self._lower:
            return self.tags[self._lower.index(tag_lower)]
        return None


def make_bio_span(words: list[str], tag: str) -> BIOSpan:
    return (words, [f"B-{tag}"] + [f"I-{tag}"] * (len(words) - 1))
