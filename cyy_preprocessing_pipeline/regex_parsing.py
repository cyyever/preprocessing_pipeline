import re
from collections.abc import Callable
from dataclasses import dataclass

from cyy_naive_lib.log import log_info


@dataclass
class MatchWithContext:
    match: re.Match
    context: str


def get_match_with_context(s: str, match: re.Match) -> MatchWithContext:
    start = match.start(0)
    end = match.start(0)
    start = max(start - 10, 0)
    context = s[start : end + 10]
    return MatchWithContext(match=match, context=context)


def parse_pattern(
    s: str, pattern: str, verifier: None | Callable[[str], bool]
) -> MatchWithContext | list[MatchWithContext] | None:
    matches = list(
        get_match_with_context(s=s, match=m)
        for m in re.finditer(pattern=pattern, string=s)
    )
    if not matches:
        log_info("no match")
        return None
    if verifier is not None:
        matches = [m for m in matches if verifier(m.match.group(0))]
    if not matches:
        log_info("no filtered match")
        return None
    if len(matches) == 1:
        return matches[0]
    return matches


def parse_floats(
    s: str, verifier: None | Callable[[str], bool]
) -> MatchWithContext | list[MatchWithContext] | None:
    float_pattern = r"(?:[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"
    return parse_pattern(s=s, pattern=float_pattern, verifier=verifier)
