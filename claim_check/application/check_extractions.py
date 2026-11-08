"""The #43 use case: Extractions given as JSON, checked against the stand-in. The LangGraph graph replaces it in #47."""
from claim_check.domain.verdicts import check
from claim_check.infrastructure.standin_adapter import load_matches
from twin.infrastructure.standin.player_join import StandinFiles


def check_extractions(inputs, files=StandinFiles(), season_checks=True):
    """(the stand-in's matches, one ClaimVerdict per {"claim", "extraction"} input). The stand-in is loaded once."""
    matches = load_matches(files, season_checks)
    return matches, [check(found["claim"], found["extraction"], matches.loaded.player_seasons, matches.player_matches) for found in inputs]
