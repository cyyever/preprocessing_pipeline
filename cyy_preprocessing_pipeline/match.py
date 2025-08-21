from collections.abc import Sequence


def approximately_match_token(a: str, b: str, threshold: float = 0.9) -> bool:
    a_set = set(a.lower())
    b_set = set(b.lower())
    return len(a_set.intersection(b_set)) / len(a_set.union(b_set)) > threshold


def approximately_match_tokens(
    tokens: list[str], pred_tokens: list[str | tuple[Sequence[str], Sequence[str]]]
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
