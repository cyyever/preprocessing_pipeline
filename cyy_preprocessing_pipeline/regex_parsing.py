import re
from collections.abc import Callable

from cyy_naive_lib.log import log_info


def parse_pattern(
    s: str, pattern: str, verifier: None | Callable[[str], bool]
) -> re.Match | list[re.Match] | None:
    matches = list(re.finditer(pattern=pattern, string=s))
    if not matches:
        log_info("no match")
        return None
    if verifier is not None:
        matches = [m for m in matches if verifier(m.group(0))]
    if not matches:
        log_info("no filtered match")
        return None
    if len(matches) == 1:
        return matches[0]
    return matches
