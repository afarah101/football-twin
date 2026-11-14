"""Claim Check's CLI for #43: Extraction JSON files in, a printed Verdict and a Verdict JSON under build/private/claim_check/ out.

Run from the repo root:
  python -m claim_check.interface.cli <extraction.json> [...]
Each file holds {"claim": "<the Claim>", "extraction": {<the Extraction shape>}}. The typed-Claim CLI comes in #47.
The stand-in may never publish: the JSON stays under build/private/ (Q11 publishing gate).
"""
import argparse
import dataclasses
import json
import re
from pathlib import Path

from claim_check.application.check_extractions import check_extractions
from twin.infrastructure.standin.player_join import StandinFiles

OUT = Path(__file__).resolve().parents[2] / "build" / "private" / "claim_check"


def ordinal(value):
    number = f"{value:.0f}"
    last = int(number) % 100
    return number + ("th" if 11 <= last <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(last % 10, "th"))


def render(verdict):
    lines = [f"Claim: {verdict.claim}"]
    if verdict.subject:
        lines.append(f"Subject: {verdict.subject}")
    if verdict.polarity == "negated":
        lines.append("Negated Claim: Supported and Not supported are swapped.")
    for found in verdict.readings:
        lines.append(f"{found.claim_type or 'Verdict'}: {found.verdict}" + (f" ({found.reason})" if found.reason else ""))
        if found.detail:
            lines.append(f"  {found.detail}")
        if found.threshold:
            lines.append(f"  {found.threshold}")
        if found.test:
            test, low, high = found.test, *found.test.interval
            lines.append(f"  {verdict.subject}: {ordinal(test.percentile)} percentile (range {ordinal(low)}-{ordinal(high)}): {test.outcome}")
            lines.append(f"  Value: {test.value_words}, on {test.shots} shots.")
        if found.reference_group:
            lines.append(f"  {found.reference_group}")
        if found.seasons:
            lines.append(f"  Seasons: {found.seasons} · {verdict.data_end}")
        if found.coverage:
            lines.append(f"  {found.coverage}" + (" Thin evidence." if found.thin else ""))
        if found.seasons_alone:
            lines.append("  Each season alone (context only): " + "; ".join(found.seasons_alone))
    if verdict.warning:
        lines.append(verdict.warning)
    lines.append(f"Versions: word map {verdict.word_map} ({verdict.draft}) · level scale {verdict.level_scale} · {verdict.method}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("extractions", nargs="+", type=Path)
    parser.add_argument("--standin", type=Path, default=StandinFiles().folder)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--no-season-checks", action="store_true", help="for a sample cut as whole matches, as the tests load it")
    args = parser.parse_args(argv)
    inputs = [json.loads(path.read_text(encoding="utf8")) for path in args.extractions]
    matches, verdicts = check_extractions(inputs, StandinFiles(args.standin), not args.no_season_checks)
    print(f"Stand-in: {matches.unlinked_matches} FBref matches left out, not linked to Understat (no shots, no TeamMatch).")
    args.out.mkdir(parents=True, exist_ok=True)
    for verdict in verdicts:
        path = args.out / (re.sub(r"[^a-z0-9]+", "-", verdict.claim.lower()).strip("-") + ".json")
        path.write_text(json.dumps(dataclasses.asdict(verdict), indent=2, ensure_ascii=False) + "\n", encoding="utf8")
        print(f"\n{render(verdict)}\nVerdict JSON: {path}")


if __name__ == "__main__":
    main()
