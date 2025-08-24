import re
from collections.abc import Callable
from dataclasses import dataclass

from cyy_naive_lib.log import log_info


@dataclass
class MatchWithContext:
    match: re.Match
    context: str


compiled_rex = {}


def get_match_with_context(match: re.Match) -> MatchWithContext:
    start = match.start(0)
    end = match.start(0)
    start = max(start - 10, 0)
    context = match.string[start : end + 10]
    return MatchWithContext(match=match, context=context)


def parse_pattern(
    s: str,
    pattern: str,
    verifier: None | Callable[[MatchWithContext], bool] = None,
    verbose: bool = False,
) -> list[MatchWithContext]:
    if pattern not in compiled_rex:
        compiled_rex[pattern] = re.compile(pattern)
    pattern = compiled_rex[pattern]
    matches = [
        get_match_with_context(match=m) for m in re.finditer(pattern=pattern, string=s)
    ]
    if not matches:
        if verbose:
            log_info("no match for pattern %s: %s", pattern, s)
        return matches
    if verifier is not None:
        matches = [m for m in matches if verifier(m)]
    if not matches:
        if verbose:
            log_info("no match for filter %s: %s", pattern, s)
        return matches
    return matches


float_pattern = r"(?:[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)"


def parse_floats(
    s: str,
    verifier: None | Callable[[MatchWithContext], bool] = None,
    verbose: bool = False,
) -> list[MatchWithContext]:
    return parse_pattern(s=s, pattern=float_pattern, verifier=verifier, verbose=verbose)
