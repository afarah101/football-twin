"""The Build: a LoadedSource to one file per league-season of MetricProfiles and twin lists (Q23, Q26), and one career file (#30).

Each entry holds both twin lists of every Candidate method, and whether its player has a CareerProfile. A player without one
keeps season twins only (D30-8). The career file holds every CareerProfile with its percentiles and both career lists. The Basketball method is only a Comparison method, so it stays
on the validation report and out of these files (Q20).

A public file is site or release output (D43). Only `write_public_files` writes one, and it fails the run unless the source
may publish (D34). A source that may not, such as the stand-in, writes the same format into `build/private/`.
Usage: python3 -m twin.application.build  (the stand-in run, into build/private/, and its site into build/private/site/)
"""
import json
from pathlib import Path

from twin.domain.pool_map import pca_points
from twin.domain.careers import CAREER_MINUTES, career_lists, career_percentiles, career_profiles
from twin.domain.profiles import METRICS, peer_group_profiles
from twin.domain.twins import CANDIDATE_METHODS, twin_lists

BUILD = Path(__file__).resolve().parent.parent.parent / "build"
MAP_FILE = "map.json"  # #12: the Pool map, its own file
CAREER_FILE = "careers.json"  # beside the league-season files; write_files returns only those, which the site reads


def twin_entries(matches):
    return [
        {"player_id": found.player_season.player_id, "name": found.player_season.name, "league": found.player_season.league, "season": found.player_season.season,
         "minutes": found.player_season.minutes, "distance": found.distance, "closeness": found.closeness}
        for found in matches
    ]


def career_summary(career):
    return {"player_id": career.player_id, "name": career.name, "role_group": career.role_group, "first_season": career.first_season,
            "last_season": career.last_season, "season_count": career.season_count, "minutes": career.minutes}


def career_twin_entries(matches):
    return [{**career_summary(found.career), "distance": found.distance, "closeness": found.closeness} for found in matches]


def career_file(loaded, careers, career_minutes):
    """Derived values only (Q3), like the league-season files."""
    percentiles, lists = career_percentiles(careers), career_lists(careers)
    return {
        "source": loaded.source,
        "metrics": list(METRICS),
        "career_minutes": career_minutes,
        "careers": [
            {
                **career_summary(career),
                "player_seasons": [{"league": found.player_season.league, "season": found.player_season.season, "minutes": found.player_season.minutes} for found in career.profiles],
                "metric_profile": dict(zip(METRICS, career.values)),
                "percentiles": dict(zip(METRICS, percentiles[career.player_id])),
                "twins": {method: {"all_roles": career_twin_entries(lists[method][career.player_id].all_roles), "same_role": career_twin_entries(lists[method][career.player_id].same_role)}
                          for method in lists},
            }
            for career in careers
        ],
    }


def profile_file(loaded, league, season, profiles, lists, career_ids):
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
                "career": found.player_season.player_id in career_ids,
            }
            for found in profiles
        ],
    }


def write_files(loaded, folder):
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    peer_groups = peer_group_profiles(loaded.player_seasons, loaded.shots)
    lists = twin_lists(peer_groups)
    careers = career_profiles(peer_groups)
    career_ids = {career.player_id for career in careers}
    for (league, season), profiles in peer_groups.items():
        path = folder / f"{league}_{season}.json"
        path.write_text(json.dumps(profile_file(loaded, league, season, profiles, lists, career_ids), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        written.append(path)
    (folder / CAREER_FILE).write_text(json.dumps(career_file(loaded, careers, CAREER_MINUTES), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
    map_points = {"source": loaded.source, "columns": ["league", "season", "player_id", "x", "y"], "points": [list(point) for point in pca_points(peer_groups)]}
    (folder / MAP_FILE).write_text(json.dumps(map_points, ensure_ascii=False) + "\n", encoding="utf8")
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
    from twin.application.site_data import write_site
    from twin.infrastructure.standin.loader import StandinLoader

    paths = run(StandinLoader().load())
    for path in paths:
        print(path.relative_to(BUILD.parent))
    print(write_site(paths).relative_to(BUILD.parent))
