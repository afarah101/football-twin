"""TwinMatches (#9) at the Build seam: the stand-in loader's result on tests/fixtures/standin/loader_sample/ in, twin lists out.

The sample's Pool is 30 real PlayerSeasons in 9 PeerGroups. Mohamed Salah holds two of them (ENG 2017/18 and 2022/23),
which is the real own-seasons case. ENG 2020/21 and FRA 2018/19 hold one player each, so every z-score there is 0: the
real zero-vector case for cosine and Pearson, and Salah is also the real case of one player near another twice. Distances,
the one slot per player and both closeness reference sets are checked against a plain-Python version written here.
Run from the repo root: python3 -m unittest discover tests
"""
import math
import sys
import unittest
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_build import built_files, loaded
from twin.domain import profiles, twins

SALAH = "e342ad68"
TWIN_KEYS = {"player_id", "name", "league", "season", "minutes", "distance", "closeness"}


@lru_cache(maxsize=None)
def entries():
    """Every Pool entry of the build files, as {(league, season, player_id): entry}."""
    return {(content["league"], content["season"], entry["player_id"]): entry for content in built_files().values() for entry in content["player_seasons"]}


@lru_cache(maxsize=None)
def peer_groups():
    found = loaded()
    return profiles.peer_group_profiles(found.player_seasons, found.shots)


def plain_distance(method, a, b):
    if method in ("euclidean", "basketball"):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
    if method == "pearson":
        a, b = [x - sum(a) / len(a) for x in a], [y - sum(b) / len(b) for y in b]
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return 1 - (sum(x * y for x, y in zip(a, b)) / norm if norm else 0.0)


def plain_percentiles(column):
    return [100 * (sum(1 for other in column if other < value) + 0.5 * sum(1 for other in column if other == value)) / len(column) for value in column]


def plain_vectors(method):
    """{key: vector}: z-scores from the build files, or for the Basketball method percentiles of the shrunk metrics."""
    if method != "basketball":
        return {key: [entry["metric_profile"][metric] for metric in profiles.METRICS] for key, entry in entries().items()}
    vectors = {}
    for (league, season), members in peer_groups().items():
        columns = [plain_percentiles([member.shrunk[index] for member in members]) for index in range(len(profiles.METRICS))]
        for row, member in enumerate(members):
            vectors[(league, season, member.player_season.player_id)] = [column[row] for column in columns]
    return vectors


def plain_ranked(method, key, same_league):
    """Every other player's season, closest first, before the one-slot rule."""
    vectors = plain_vectors(method)
    others = [other for other in vectors if other[2] != key[2] and (not same_league or other[0] == key[0])]
    return sorted(others, key=lambda other: (round(plain_distance(method, vectors[key], vectors[other]), twins.DISTANCE_DECIMALS), other))


def plain_list(method, key, same_league):
    """Owner decision 1: each player once, with his closest season, up to TOP players."""
    vectors, kept, seen = plain_vectors(method), [], set()
    for other in plain_ranked(method, key, same_league):
        if other[2] not in seen:
            seen.add(other[2])
            kept.append((other, plain_distance(method, vectors[key], vectors[other])))
    return kept[:twins.TOP]


def plain_closeness(method, distance, league=None):
    """All pairs of two different players, or with `league` only pairs of two players in that league (owner decision 2)."""
    vectors = plain_vectors(method)
    keys = sorted(key for key in vectors if league is None or key[0] == league)
    pairs = [round(plain_distance(method, vectors[a], vectors[b]), twins.DISTANCE_DECIMALS) for i, a in enumerate(keys) for b in keys[i + 1:] if a[2] != b[2]]
    return 100 * sum(1 for found in pairs if found > distance) / len(pairs)


def domain_lists():
    return twins.twin_lists(peer_groups())


class TwinLists(unittest.TestCase):
    def test_every_candidate_method_gives_its_top_10(self):
        self.assertEqual(twins.CANDIDATE_METHODS, ("euclidean", "cosine", "pearson"))
        for key, entry in entries().items():
            self.assertEqual(set(entry["twins"]), set(twins.CANDIDATE_METHODS), key)
            for method in twins.CANDIDATE_METHODS:
                written = [((found["league"], found["season"], found["player_id"]), found["distance"]) for found in entry["twins"][method]["all_leagues"]]
                expected = plain_list(method, key, same_league=False)
                self.assertEqual(len(written), twins.TOP, (key, method))
                self.assertEqual([other for other, _ in written], [other for other, _ in expected], (key, method))
                for (_, distance), (_, plain) in zip(written, expected):
                    self.assertAlmostEqual(distance, plain, places=9)

    def test_basketball_method_uses_percentiles_of_the_shrunk_metrics_and_is_only_a_comparison_method(self):
        self.assertEqual(twins.COMPARISON_METHODS, ("basketball",))
        self.assertNotIn("basketball", twins.CANDIDATE_METHODS)
        # The shrunk values are the ones the z-scores came from, so the Basketball method reads the same 10 metrics.
        for members in peer_groups().values():
            for index in range(len(profiles.METRICS)):
                self.assertEqual(profiles.z_scores([member.shrunk[index] for member in members]), [member.values[index] for member in members])
        lists = domain_lists()["basketball"]
        for key in entries():
            self.assertEqual([(match.player_season.key, round(match.distance, 9)) for match in lists[key].all_leagues],
                             [(other, round(distance, 9)) for other, distance in plain_list("basketball", key, same_league=False)], key)
        # Only on the validation report (Q20): no build file holds it.
        self.assertFalse(any("basketball" in entry["twins"] for entry in entries().values()))

    def test_a_players_own_seasons_never_appear(self):
        salah = [key for key in entries() if key[2] == SALAH]
        self.assertEqual(len(salah), 2)  # real: ENG 2017/18 and 2022/23, both in the sample's Pool
        for key, entry in entries().items():
            for method, lists in entry["twins"].items():
                for listed in lists.values():
                    self.assertNotIn(key[2], {found["player_id"] for found in listed}, (key, method))
        for method, lists in domain_lists().items():
            for key, found in lists.items():
                self.assertNotIn(key[2], {match.player_season.player_id for match in found.all_leagues + found.same_league}, (key, method))

    def test_each_twin_match_has_league_minutes_and_closeness_percentile(self):
        records = {found.key: found for found in loaded().player_seasons}
        for key, entry in entries().items():
            for method in twins.CANDIDATE_METHODS:
                for found in entry["twins"][method]["all_leagues"] + entry["twins"][method]["same_league"]:
                    self.assertEqual(set(found), TWIN_KEYS)
                    record = records[(found["league"], found["season"], found["player_id"])]
                    self.assertEqual((found["minutes"], found["name"]), (record.minutes, record.name))
                    self.assertTrue(0 <= found["closeness"] <= 100)
        for method in twins.CANDIDATE_METHODS:
            first = entries()[("ENG", 2017, SALAH)]["twins"][method]["all_leagues"][0]
            self.assertAlmostEqual(first["closeness"], plain_closeness(method, first["distance"]), places=9)

    def test_both_lists_exist_all_leagues_and_same_league(self):
        crossed = False
        for key, entry in entries().items():
            for method in twins.CANDIDATE_METHODS:
                same = entry["twins"][method]["same_league"]
                self.assertEqual([(found["league"], found["season"], found["player_id"]) for found in same], [other for other, _ in plain_list(method, key, same_league=True)], (key, method))
                self.assertTrue(all(found["league"] == key[0] for found in same))
                crossed |= any(found["league"] != key[0] for found in entry["twins"][method]["all_leagues"])
        self.assertTrue(crossed)
        self.assertEqual(entries()[("FRA", 2018, next(key[2] for key in entries() if key[:2] == ("FRA", 2018)))]["twins"]["euclidean"]["same_league"], [])  # real: the only French Pool player

    def test_each_list_holds_a_player_once_with_his_closest_season(self):
        vectors = {method: plain_vectors(method) for method in twins.CANDIDATE_METHODS + twins.COMPARISON_METHODS}
        # Real: before the one-slot rule, Salah's two Pool seasons both reach some top 10.
        self.assertTrue(any(sum(1 for other in plain_ranked(method, key, same_league)[:twins.TOP] if other[2] == SALAH) == 2
                            for method in twins.CANDIDATE_METHODS for key in entries() for same_league in (False, True)))
        written = {(method, key, same_league): [(found["league"], found["season"], found["player_id"]) for found in entry["twins"][method]["same_league" if same_league else "all_leagues"]]
                   for key, entry in entries().items() for method in twins.CANDIDATE_METHODS for same_league in (False, True)}
        domain = {(method, key, same_league): [match.player_season.key for match in (found.same_league if same_league else found.all_leagues)]
                  for method, lists in domain_lists().items() for key, found in lists.items() for same_league in (False, True)}
        self.assertTrue(set(domain) > set(written))
        for (method, key, same_league), listed in [*written.items(), *domain.items()]:
            players = [other[2] for other in listed]
            self.assertEqual(len(players), len(set(players)), (method, key, same_league))
            eligible = {other[2] for other in plain_ranked(method, key, same_league)}
            self.assertEqual(len(players), min(twins.TOP, len(eligible)), (method, key, same_league))
            for other in listed:
                seasons = [found for found in vectors[method] if found[2] == other[2] and (not same_league or found[0] == key[0])]
                closest = min(seasons, key=lambda found: (round(plain_distance(method, vectors[method][key], vectors[method][found]), twins.DISTANCE_DECIMALS), found))
                self.assertEqual(other, closest, (method, key, same_league))

    def test_same_league_closeness_uses_same_league_pairs_only(self):
        checked = 0
        for key, entry in entries().items():
            for method in twins.CANDIDATE_METHODS:
                for found in entry["twins"][method]["same_league"]:
                    self.assertAlmostEqual(found["closeness"], plain_closeness(method, found["distance"], league=key[0]), places=9, msg=(key, method))
                    checked += 1
        self.assertTrue(checked)
        # The all-leagues list keeps all pairs as its reference, so the two differ for a real same-league twin.
        first = entries()[("ENG", 2017, SALAH)]["twins"]["euclidean"]
        same = first["same_league"][0]
        self.assertNotAlmostEqual(plain_closeness("euclidean", same["distance"], league="ENG"), plain_closeness("euclidean", same["distance"]), places=6)

    def test_a_peer_group_of_one_has_all_zero_z_scores_and_finite_distances(self):
        alone = [key for key in entries() if key[:2] in (("ENG", 2020), ("FRA", 2018))]
        self.assertEqual(len(alone), 2)  # real: one Pool player in each
        for key in alone:
            self.assertEqual(set(entries()[key]["metric_profile"].values()), {0.0})
            for method in twins.CANDIDATE_METHODS:
                self.assertTrue(all(math.isfinite(found["distance"]) for found in entries()[key]["twins"][method]["all_leagues"]))


if __name__ == "__main__":
    unittest.main()
