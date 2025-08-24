import re
from collections.abc import Callable
from dataclasses import dataclass

from cyy_naive_lib.log import log_info


@dataclass
class MatchWithContext:
    match: re.Match
    context: str


def get_match_with_context(match: re.Match) -> MatchWithContext:
    start = match.start(0)
    end = match.start(0)
    start = max(start - 10, 0)
    context = match.string[start : end + 10]
    return MatchWithContext(match=match, context=context)


def parse_pattern(
    s: str, pattern: str, verifier: None | Callable[[MatchWithContext], bool] = None
) -> list[MatchWithContext]:
    matches = [
        get_match_with_context(match=m) for m in re.finditer(pattern=pattern, string=s)
    ]
    if not matches:
        log_info("no match: %s",s)
        return matches
    if verifier is not None:
        matches = [m for m in matches if verifier(m)]
    if not matches:
        log_info("no filtered match")
        return matches
    return matches


float_pattern = r"(?:[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"


def parse_floats(
    s: str, verifier: None | Callable[[MatchWithContext], bool] = None
) -> list[MatchWithContext]:
    return parse_pattern(s=s, pattern=float_pattern, verifier=verifier)
