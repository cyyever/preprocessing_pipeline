import re
from collections import Counter

from cyy_naive_lib import Expected
from cyy_naive_lib.log import log_error

from ..common import strip_lines
from .regex_parsing import (
    MatchWithContext,
    float_pattern,
    parse_floats,
    parse_pattern,
)


def refine_match(m: MatchWithContext) -> str:
    s = m.real_match
    context = m.context
    # return an invalid number
    invalid_score = "10000000"
    if "/" in s:
        idx = s.find("/")
        s = s[:idx]
    if f"({s})" in context:
        return invalid_score
    if s.endswith(".0"):
        s.removesuffix(".0")
    if "00" in s:
        return invalid_score
    return s


def is_valid_score(m: MatchWithContext) -> bool:
    try:
        score_number = float(refine_match(m))
        assert 0 <= score_number <= 1
        return True
    except BaseException:
        pass
    return False


def __parse_score_impl(s: str) -> MatchWithContext | list[MatchWithContext] | None:
    lines = strip_lines(s)
    for idx, line in enumerate(lines):
        lines[idx] = " ".join(line.split())
    s = " ".join(lines)
    s = (
        s.lower().strip().replace(" :", ":").replace(": ", ":").replace(" =", "=")
    ).strip()
    s = re.sub(r" +", " ", s)

    new_float_pattern = float_pattern + r"(?:/1(.0)?)?"
    matches = parse_pattern(
        s=s, pattern=new_float_pattern, verifier=is_valid_score, verbose=True
    )

    if not matches:
        return None
    for m in matches:
        m.real_match = refine_match(m)
    unique_scores = {m.real_match for m in matches}
    if len(unique_scores) == 1:
        # if matches[0].match.start() == 0:
        #     return matches[0]
        # if "0" in unique_scores or "0.0" in unique_scores:
        #     return matches[0]
        # if "1" in unique_scores or "1.0" in unique_scores:
        #     return matches[0]
        if "score" in matches[0].context:
            return matches[0]
        # if "*" in matches[0].context:
        #     return matches[0]
        if "answer is" in matches[0].context:
            return matches[0]
        # if len(matches) == 1:
        #     return matches[0]
        log_error("Unique scores for %s, matches are %s", s, matches)

    score_lines = [line for line in s.splitlines() if "**" in line]
    if len(score_lines) == 1:
        s = score_lines[0]

    score_pattern = r"(?:final )?score.*?" + float_pattern

    for match in parse_pattern(s=s, pattern=score_pattern, verbose=False):
        a = match.match.group(0).removesuffix(".")
        if "score:0/1" in a or "score:0/1.0" in a:
            matches.append(match)
            continue
        if "*score:0*" in a:
            matches.append(match)
            continue
        matches += parse_floats(s=a, verifier=is_valid_score, verbose=False)
    assert matches

    matches = [m for m in matches if "score is not" not in m.match.group(0)]
    possible_matches = [m for m in matches if f"score:{m.real_match}" in m.context]
    if len(possible_matches) == 1:
        return possible_matches[0]
    if len(possible_matches) > 1:
        real_match_set = {m.real_match for m in possible_matches}
        if len(real_match_set) == 1:
            return possible_matches[0]
        log_error("multiple scores %s: %s", s, possible_matches)

    possible_matches = [m for m in matches if "final score:" in m.match.group(0)]
    if len(possible_matches) == 1:
        return possible_matches[0]
    if len(possible_matches) > 1:
        log_error("multiple final scores %s: %s", s, possible_matches)

    counter = Counter([float(m.real_match) for m in matches])
    value, cnt = counter.most_common(1)[0]
    if cnt / counter.total() > 0.8:
        for m in matches:
            if float(m.real_match) == value:
                return m
        log_error("Most frequent score %s: %s", s, matches)
    return matches


def parse_score(sample_id: str, raw_score: str) -> Expected[float]:
    assert isinstance(raw_score, str)
    res = __parse_score_impl(raw_score)
    if not isinstance(res, MatchWithContext):
        if res is None:
            return Expected.ok(value=0)
        return Expected.not_ok()

    score_number = float(res.real_match)
    assert 0 <= score_number <= 1, res.real_match
    return Expected.ok(value=score_number)
