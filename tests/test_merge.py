import os.path
import unittest

from cmlibs.zinc.field import Field

# from cmlibs.merger.points import merge_markers
from cmlibs.merger.datapoints import merge
from cmlibs.zinc.context import Context
from cmlibs.zinc.status import OK as ZINC_OK

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

    def test_datapoint_merge(self):
        if os.path.isfile(resource_path("datapoints_I_merged.exf")):
            os.remove(resource_path("datapoints_I_merged.exf"))

        datapoint_I_file = resource_path("datapoints_I.exf")
        datapoint_II_file = resource_path("datapoints_II.exf")

        c = Context("data")
        output_exf = merge(datapoint_I_file, datapoint_II_file, c, output_directory=resource_path(""))

        c_output = Context("output")
        region = c_output.getDefaultRegion()
        region.readFile(output_exf)

        fm = region.getFieldmodule()
        nodes = fm.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        self.assertEqual(22, nodes.getSize())
        inner_surface_field = fm.findFieldByName('inner_surface')
        outer_surface_field = fm.findFieldByName('outer_surface')
        self.assertEqual(10, inner_surface_field.castGroup().getNodesetGroup(nodes).getSize())
        self.assertEqual(12, outer_surface_field.castGroup().getNodesetGroup(nodes).getSize())
