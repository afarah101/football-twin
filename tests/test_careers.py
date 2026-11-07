"""CareerProfiles and career twin lists (#30), on tests/fixtures/standin/loader_sample/.

The sample is cut as whole matches, so its careers are short: the longest is Mohamed Salah's, 3,611 Pool minutes over
ENG 2017/18 (2,414) and ENG 2023/24 (1,197). No real sample career reaches the 6,000-minute bar (D30-1). So the bar is
tested at its edge on Salah, and the rest runs the same code with the bar at the Pool's own 900 minutes, which turns each
of the sample's 29 real Pool players into a career. Every value is checked against a plain-Python version written here.
The sample holds no career with seasons in two role groups, so the most-minutes rule is checked on single-group careers.
Run from the repo root: python3 -m unittest discover tests
"""
import sys
import unittest
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_twins import SALAH, peer_groups, plain_distance, plain_percentiles
from twin.domain import careers, profiles, twins

POOL_BAR = 900  # the Pool's own minimum: every sample Pool player becomes a career
SALAH_MINUTES = 3611  # real: 2,414 + 1,197


@lru_cache(maxsize=None)
def sample_careers():
    return careers.career_profiles(peer_groups(), career_minutes=POOL_BAR)


@lru_cache(maxsize=None)
def sample_lists():
    return careers.career_lists(sample_careers())


def plain_seasons():
    """{player_id: [MetricProfile]} of every sample Pool PlayerSeason."""
    found = defaultdict(list)
    for members in peer_groups().values():
        for member in members:
            found[member.player_season.player_id].append(member)
    return found


def plain_ranked(method, career, same_role):
    others = [other for other in sample_careers() if other.player_id != career.player_id and (not same_role or other.role_group == career.role_group)]
    return sorted(others, key=lambda other: (round(plain_distance(method, career.values, other.values), twins.DISTANCE_DECIMALS), other.player_id))


def plain_closeness(method, distance, role_group=None):
    kept = [career for career in sample_careers() if role_group is None or career.role_group == role_group]
    pairs = [round(plain_distance(method, a.values, b.values), twins.DISTANCE_DECIMALS) for i, a in enumerate(kept) for b in kept[i + 1:]]
    return 100 * sum(1 for found in pairs if found > distance) / max(len(pairs), 1)


class CareerBar(unittest.TestCase):
    def test_the_bar_is_6000_career_minutes_and_inclusive(self):
        self.assertEqual(careers.CAREER_MINUTES, 6000)  # D30-1
        self.assertEqual(careers.career_profiles(peer_groups()), [])  # real: no sample career reaches 6,000
        self.assertEqual([career.player_id for career in careers.career_profiles(peer_groups(), career_minutes=SALAH_MINUTES)], [SALAH])
        self.assertEqual(careers.career_profiles(peer_groups(), career_minutes=SALAH_MINUTES + 1), [])


class CareerProfiles(unittest.TestCase):
    def test_career_profile_is_the_minutes_weighted_mean_of_its_season_z_scores(self):
        seasons = plain_seasons()
        self.assertEqual({career.player_id for career in sample_careers()}, set(seasons))
        for career in sample_careers():
            own = seasons[career.player_id]
            total = sum(member.player_season.minutes for member in own)
            self.assertEqual(career.minutes, total)  # D30-7: each stint with its own minutes
            for index, metric in enumerate(profiles.METRICS):
                plain = sum(member.player_season.minutes * member.values[index] for member in own) / total
                self.assertAlmostEqual(career.values[index], plain, places=12, msg=(career.name, metric))
        salah = next(career for career in sample_careers() if career.player_id == SALAH)
        self.assertEqual((salah.minutes, len(salah.profiles)), (SALAH_MINUTES, 2))
        self.assertEqual((salah.first_season, salah.last_season, salah.season_count), (2017, 2023, 2))  # D30-7: distinct seasons

    def test_role_group_is_the_one_with_the_most_career_minutes(self):
        for career in sample_careers():
            minutes = defaultdict(int)
            for member in plain_seasons()[career.player_id]:
                minutes[careers.ROLE_GROUPS[member.player_season.display_position]] += member.player_season.minutes
            self.assertEqual(career.role_group, max(minutes, key=minutes.get), career.name)
        self.assertEqual(next(career.role_group for career in sample_careers() if career.player_id == SALAH), "Wide")  # real: RW both seasons
        self.assertEqual(careers.ROLE_GROUPS, {"FW": "Forward", "LW": "Wide", "RW": "Wide", "AM": "Central AM"})

    def test_career_percentiles_are_among_all_careers(self):
        found = careers.career_percentiles(sample_careers())
        columns = [plain_percentiles([career.values[index] for career in sample_careers()]) for index in range(len(profiles.METRICS))]
        for row, career in enumerate(sample_careers()):
            self.assertEqual(len(found[career.player_id]), len(profiles.METRICS))
            for index in range(len(profiles.METRICS)):
                self.assertAlmostEqual(found[career.player_id][index], columns[index][row], places=12, msg=career.name)
                self.assertTrue(0 <= found[career.player_id][index] <= 100)


class CareerLists(unittest.TestCase):
    def test_each_career_appears_once_per_list_and_never_in_its_own(self):
        self.assertEqual(set(sample_lists()), set(twins.CANDIDATE_METHODS))
        for method, lists in sample_lists().items():
            self.assertEqual(set(lists), {career.player_id for career in sample_careers()})
            for career in sample_careers():
                for same_role, listed in ((False, lists[career.player_id].all_roles), (True, lists[career.player_id].same_role)):
                    ids = [match.career.player_id for match in listed]
                    self.assertEqual(len(ids), len(set(ids)), (method, career.name))
                    self.assertNotIn(career.player_id, ids, (method, career.name))
                    self.assertEqual(len(ids), min(twins.TOP, len(plain_ranked(method, career, same_role))), (method, career.name, same_role))

    def test_lists_rank_by_distance_on_career_z_scores(self):
        for method, lists in sample_lists().items():
            for career in sample_careers():
                listed = lists[career.player_id].all_roles
                expected = plain_ranked(method, career, same_role=False)[:twins.TOP]
                self.assertEqual([match.career.player_id for match in listed], [other.player_id for other in expected], (method, career.name))
                for match, other in zip(listed, expected):
                    self.assertAlmostEqual(match.distance, plain_distance(method, career.values, other.values), places=9)

    def test_role_filter_keeps_only_the_careers_role_group(self):
        crossed = False
        for method, lists in sample_lists().items():
            for career in sample_careers():
                same = lists[career.player_id].same_role
                self.assertTrue(all(match.career.role_group == career.role_group for match in same), (method, career.name))
                self.assertEqual([match.career.player_id for match in same], [other.player_id for other in plain_ranked(method, career, same_role=True)[:twins.TOP]])
                crossed |= any(match.career.role_group != career.role_group for match in lists[career.player_id].all_roles)
        self.assertTrue(crossed)  # real: the all-roles lists do cross role groups

    def test_closeness_uses_career_pairs_only(self):
        for method, lists in sample_lists().items():
            for career in sample_careers():
                for match in lists[career.player_id].all_roles:
                    self.assertAlmostEqual(match.closeness, plain_closeness(method, match.distance), places=9)
                for match in lists[career.player_id].same_role:
                    self.assertAlmostEqual(match.closeness, plain_closeness(method, match.distance, career.role_group), places=9)


if __name__ == "__main__":
    unittest.main()
