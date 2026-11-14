"""#12: the Pool map. PCA on the Pool's z-scores, published as its own file, with no axis named.

The PCA rule uses small hand-made inputs: they say so in their names and never go in tests/fixtures/.
Run from the repo root: python3 -m unittest tests.test_pool_map
"""
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_site_data import data_files, sample_site
from twin.domain.pool_map import pca_points, pca_summary


def member(player_id, values, league="ENG", season=2023):
    return SimpleNamespace(values=values, player_season=SimpleNamespace(player_id=player_id, league=league, season=season))


class PcaPoints(unittest.TestCase):
    def test_hand_made_points_spread_along_the_first_component(self):
        # hand-made (the sample cannot show an exact line): 5 players on a line in 3 metrics; the first component holds all the spread.
        groups = {("ENG", 2023): [member(f"p{k}", (k, 2 * k, 0.0)) for k in range(5)]}
        points = pca_points(groups)
        self.assertEqual([point[2] for point in points], ["p0", "p1", "p2", "p3", "p4"])
        xs, ys = [point[3] for point in points], [point[4] for point in points]
        self.assertEqual(xs, sorted(xs))  # the sign rule makes the largest loading positive, so p4 sits right
        self.assertTrue(all(abs(y) < 1e-9 for y in ys))

    def test_hand_made_the_same_input_gives_the_same_map(self):
        groups = {("ENG", 2023): [member(f"p{k}", (k % 3, k * 0.5, -k)) for k in range(6)]}
        self.assertEqual(pca_points(groups), pca_points(groups))

    def test_hand_made_too_few_members_gives_no_map(self):
        self.assertEqual(pca_points({("ENG", 2023): [member("p0", (1.0, 2.0))]}), [])


class PcaSummary(unittest.TestCase):
    def test_the_build_prints_loadings_and_explained_variance(self):
        from test_build import loaded
        from twin.domain.profiles import METRICS, peer_group_profiles
        found = loaded()
        shares, loadings = pca_summary(peer_group_profiles(found.player_seasons, found.shots))
        self.assertEqual((len(shares), [len(row) for row in loadings]), (2, [len(METRICS)] * 2))
        self.assertGreaterEqual(shares[0], shares[1])
        self.assertTrue(all(max(row, key=abs) > 0 for row in loadings))  # the same sign rule as the map points


class MapFile(unittest.TestCase):
    def test_the_map_is_its_own_file_with_one_point_per_pool_season(self):
        found = json.loads(sample_site()["data/map.json"])
        self.assertEqual(found["columns"], ["league", "season", "player_id", "x", "y"])
        seasons = {(content["league"], content["season"], entry["player_id"]) for content in data_files().values() for entry in content["player_seasons"]}
        self.assertEqual({tuple(point[:3]) for point in found["points"]}, seasons)

    def test_no_axis_is_named(self):
        found = json.loads(sample_site()["data/map.json"])
        self.assertFalse({"axes", "axis", "x_label", "y_label", "loadings"} & set(found))
        page = sample_site()["index.html"]
        self.assertIn('id="map-box"', page)
        self.assertIn("The map has no axes.", page)


if __name__ == "__main__":
    unittest.main()
