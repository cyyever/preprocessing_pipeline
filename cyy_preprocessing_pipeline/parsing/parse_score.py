import re
from collections import Counter

from cyy_naive_lib import Expected
from cyy_naive_lib.log import log_error

from ..common import strip_lines
from ..incremental_computing import incremental_computing
from .regex_parsing import (
    MatchWithContext,
    float_pattern,
    parse_floats,
    parse_pattern,
)


def refine_match(s: str) -> str:
    if "/" in s:
        idx = s.find("/")
        s = s[:idx]
    if s.endswith(".0"):
        s.removesuffix(".0")
    if "00" in s:
        # return an invalid number
        return "10000000"
    return s


def is_valid_score(m: MatchWithContext) -> bool:
    try:
        score_number = float(refine_match(m.real_match))
        assert 0 <= score_number <= 1
        return True
    except BaseException:
        pass
    return False


def __parse_score_impl(s: str) -> MatchWithContext | list[MatchWithContext] | None:
    lines = strip_lines(s)
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
        m.real_match = refine_match(m.real_match)
    unique_scores = {m.real_match for m in matches}
    if len(unique_scores) == 1:
        if matches[0].match.start() == 0:
            return matches[0]

        if "0" in unique_scores or "0.0" in unique_scores:
            return matches[0]
        if "1" in unique_scores or "1.0" in unique_scores:
            return matches[0]
        if "score" in matches[0].context:
            return matches[0]
        if "*" in matches[0].context:
            return matches[0]
        if "answer is" in matches[0].context:
            return matches[0]
        if len(matches) == 1:
            return matches[0]
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
    possible_matches = [
        m for m in matches if "**" in m.context or "score:" in m.context
    ]
    if len(possible_matches) == 1:
        return possible_matches[0]

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
        print("Invalid processed answer:\n", raw_score, "multiple matches", res, "\n")
        return Expected.ok(value=0)

    score_number = float(res.real_match)
    assert 0 <= score_number <= 1, res.real_match
    return Expected.ok(value=score_number)


if __name__ == "__main__":
    input_json = "/home/cyy/visual_sft/evaluate_qwen_2.5_3B_sft_nohint_and_evaluate_nohint_scores.json"
    output_json = input_json.removesuffix(".json") + "_accurate.json"
    incremental_computing(
        input_json,
        output_json,
        parse_score,
        save_second_interval=5,
    )
