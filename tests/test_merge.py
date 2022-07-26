import unittest

from opencmiss.merger.points import merge_markers
from opencmiss.zinc.context import Context
from opencmiss.zinc.status import OK as ZINC_OK

from tests.shared import resource_path


class PointsMerge(unittest.TestCase):

    def test_value_merge(self):
        mesh_file = resource_path("cube_with_markers.exf")
        phys_file = resource_path("colon_manometry_small.exf")

        merge_markers(mesh_file, phys_file)

        c = Context("data")
        root_region = c.getDefaultRegion()
        r1 = root_region.createChild("region1")
        r2 = root_region.createChild("region2")

        self.assertTrue(r1.isValid())
        self.assertEqual("region1", r1.getName())
        self.assertTrue(r2.isValid())
        self.assertEqual("region2", r2.getName())

        result = r1.readFile(mesh_file)
        self.assertEqual(ZINC_OK, result)

        result = r2.readFile(phys_file)
        self.assertEqual(ZINC_OK, result)

        dominant_marker_info = _fetch_marker_information(r1)
        dominant_regions_marker_info = {
            "region": r1,
            "marker_info": dominant_marker_info
        }

        recessive_marker_info = _fetch_marker_information(r2)
        recessive_regions_marker_info = {
            "region": r2,
            "marker_info": recessive_marker_info
        }

        # Find merge pairs.
        merge_pairs = _find_markers_to_merge(dominant_regions_marker_info, recessive_regions_marker_info)
        for pair in merge_pairs:
            _merge_node_pair(pair)

        r1.writeFile("output.exf")
