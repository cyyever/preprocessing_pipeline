import json

from .types import BIOTokenList, CanonicalTags, make_bio_span


def json2bio(json_text: str, canonical_tags: CanonicalTags) -> BIOTokenList:
    entities = json.loads(json_text)

    assert isinstance(entities, list)

    tokens: BIOTokenList = []
    for ent in entities:
        if not isinstance(ent, dict):
            continue
        tag = canonical_tags.match(ent.get("entity", ""))
        text = ent.get("text", "")
        if not tag or not text:
            continue

        words = text.strip().split()
        if not words:
            continue
        tokens.append(make_bio_span(words, tag))

    return tokens
