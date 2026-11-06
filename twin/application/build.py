"""The Build: a LoadedSource to one file per league-season of MetricProfiles and twin lists (Q23, Q26).

Each entry holds both twin lists of every Candidate method. The Basketball method is only a Comparison method, so it stays
on the validation report and out of these files (Q20).

A public file is site or release output (D43). Only `write_public_files` writes one, and it fails the run unless the source
may publish (D34). A source that may not, such as the stand-in, writes the same format into `build/private/`.
Usage: python3 -m twin.application.build  (the stand-in run, into build/private/)
"""
import json
from pathlib import Path

from twin.domain.profiles import METRICS, peer_group_profiles
from twin.domain.twins import CANDIDATE_METHODS, twin_lists

BUILD = Path(__file__).resolve().parent.parent.parent / "build"


def twin_entries(matches):
    return [
        {"player_id": found.player_season.player_id, "name": found.player_season.name, "league": found.player_season.league, "season": found.player_season.season,
         "minutes": found.player_season.minutes, "distance": found.distance, "closeness": found.closeness}
        for found in matches
    ]


def profile_file(loaded, league, season, profiles, lists):
    """Derived values only (Q3): no shot row and no raw season total."""
    return {
        "source": loaded.source,
        "league": league,
        "season": season,
        "metrics": list(METRICS),
        "player_seasons": [
            {
                "player_id": found.player_season.player_id,
                "name": found.player_season.name,
                "clubs": list(found.player_season.clubs),
                "minutes": found.player_season.minutes,
                "display_position": found.player_season.display_position,
                "metric_profile": dict(zip(METRICS, found.values)),
                "display_stats": {"goals": found.display_stats.goals, "assists": found.display_stats.assists, "npg_minus_npxg": found.display_stats.npg_minus_npxg},
                "twins": {
                    method: {"all_leagues": twin_entries(lists[method][found.player_season.key].all_leagues), "same_league": twin_entries(lists[method][found.player_season.key].same_league)}
                    for method in CANDIDATE_METHODS
                },
            }
            for found in profiles
        ],
    }


def write_files(loaded, folder):
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    peer_groups = peer_group_profiles(loaded.player_seasons, loaded.shots)
    lists = twin_lists(peer_groups)
    for (league, season), profiles in peer_groups.items():
        path = folder / f"{league}_{season}.json"
        path.write_text(json.dumps(profile_file(loaded, league, season, profiles, lists), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        written.append(path)
    return written


def write_public_files(loaded, folder):
    if not loaded.may_publish:
        raise SystemExit(f"build: source {loaded.source!r} may not publish, so no public file is written")
    return write_files(loaded, folder)


def run(loaded, build_root=BUILD):
    if loaded.may_publish:
        return write_public_files(loaded, build_root / "site")
    return write_files(loaded, build_root / "private")


if __name__ == "__main__":
    from twin.infrastructure.standin.loader import StandinLoader

    for path in run(StandinLoader().load()):
        print(path.relative_to(BUILD.parent))
