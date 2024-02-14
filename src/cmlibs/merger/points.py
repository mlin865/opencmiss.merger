import json
import os.path

from cmlibs.zinc.context import Context
from cmlibs.zinc.field import Field
from cmlibs.zinc.status import OK as ZINC_OK
from cmlibs.merger.errors import ZincMergeInvalidInputs, ZincMergeFileReadFailed


def display_field_info(field_info):
    text = f"{field_info['name']}:\n"
    text += f" - {field_info['field_type']}\n"
    text += f" - # of components: {field_info['component_count']}\n"
    if field_info['is_type_coordinate']:
        text += " - coordinate field\n"

    return text


def _determine_field_details(field, field_descriptions):
    matching_fields = [f for f in field_descriptions["Fields"] if f["Name"] == field.getName()]
    if len(matching_fields) > 0:
        return matching_fields[0]

    print(f"oh dear!!! We do not have a field description for: '{field.getName()}'.")
    return None


def _evaluate_string_field_value(node, field):
    field_module = field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    return field.evaluateString(field_cache)


def _assign_string_field_value(node, field, value):
    field_module = field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    return field.assignString(field_cache, value)


def _evaluate_mesh_location_field_value(node, field):
    field_module = field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    # Fix dimension of node to dimension 3.
    element, xi = field.evaluateMeshLocation(field_cache, 3)
    return {"element": element, "xi": xi}


def _assign_mesh_location_field_value(node, field, value):
    field_module = field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    return field.assignMeshLocation(field_cache, value["element"], value["xi"])


def _get_real_field_values(node, field_name):
    node_set = node.getNodeset()
    field_module = node_set.getFieldmodule()
    field = field_module.findFieldByName(field_name)
    time_sequence = _get_field_time_sequence(node, field_name)

    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    values = []
    for index in range(time_sequence.getNumberOfTimes()):
        time = time_sequence.getTime(index + 1)
        field_cache.setTime(time)
        result, value = field.evaluateReal(field_cache, field.getNumberOfComponents())
        if result == ZINC_OK:
            values.append({
                "time": time,
                "value": value
            })
        else:
            print("Did not evaluate field successfully.")

    return values


def _assign_real_field_values(node, field, values):
    field_module = field.getFieldmodule()
    field_cache = field_module.createFieldcache()
    field_cache.setNode(node)
    for value in values:
        if value["time"] is not None:
            field_cache.setTime(value["time"])

        field.assignReal(field_cache, value["value"])


def _get_marker_name(node):
    node_set = node.getNodeset()
    field_module = node_set.getFieldmodule()
    field = field_module.findFieldByName("marker_name")
    if field.isValid():
        return _evaluate_string_field_value(node, field)

    return "<not-found>"


def _fetch_marker_information(region):
    marker_info = []
    field_module = region.getFieldmodule()
    field_description = json.loads(field_module.writeDescription())
    field = field_module.findFieldByName("marker")

    marker_group = None
    if field.isValid():
        group = field.castGroup()
        if group:
            marker_group = group

    if not marker_group.isValid():
        return marker_info

    DOMAIN_TYPES = [Field.DOMAIN_TYPE_DATAPOINTS, Field.DOMAIN_TYPE_NODES, Field.DOMAIN_TYPE_POINT]
    for domain in DOMAIN_TYPES:
        domain_nodes = field_module.findNodesetByFieldDomainType(domain)
        node_group = marker_group.getNodesetGroup(domain_nodes)
        node_iterator = node_group.createNodeiterator()

        node_template = node_group.createNodetemplate()
        node = node_iterator.next()

        while node.isValid():
            field_iterator = field_module.createFielditerator()
            field = field_iterator.next()
            field_information_list = []
            while field.isValid():
                result = node_template.defineFieldFromNode(field, node)
                if result == ZINC_OK:
                    field_details = _determine_field_details(field, field_description)
                    field_information_list.append(field_details)
                field = field_iterator.next()

            marker_info.append({
                "id": node.getIdentifier(),
                "name": _get_marker_name(node),
                "domain": domain,
                "fields": field_information_list,
            })
            node = node_iterator.next()

    return marker_info


def _find_matching_node(marker_name, info):
    region = info["region"]
    field_module = region.getFieldmodule()
    field_cache = field_module.createFieldcache()
    for marker_info in info["marker_info"]:
        domain_nodes = field_module.findNodesetByFieldDomainType(marker_info["domain"])
        node = domain_nodes.findNodeByIdentifier(marker_info["id"])
        field_cache.setNode(node)
        marker_name_field = field_module.findFieldByName("marker_name")
        result = marker_name_field.evaluateString(field_cache)
        if marker_name == result:
            return {"node": node, "info": marker_info}

    return None


def _find_markers_to_merge(dominant, recessive):
    pairs = []
    dominant_region = dominant["region"]
    dominant_field_module = dominant_region.getFieldmodule()
    dominant_field_cache = dominant_field_module.createFieldcache()

    for marker_info in dominant["marker_info"]:
        domain_nodes = dominant_field_module.findNodesetByFieldDomainType(marker_info["domain"])
        node = domain_nodes.findNodeByIdentifier(marker_info["id"])
        dominant_field_cache.setNode(node)
        marker_name_field = dominant_field_module.findFieldByName("marker_name")
        result = marker_name_field.evaluateString(dominant_field_cache)
        recessive_info = _find_matching_node(result, recessive)
        if recessive_info is not None:
            pairs.append(({"node": node, "info": marker_info}, recessive_info))

    return pairs


def _get_field_time_sequence(node, field_name):
    node_set = node.getNodeset()
    field_module = node_set.getFieldmodule()
    node_template = node_set.createNodetemplate()
    field = field_module.findFieldByName(field_name)

    node_template.defineFieldFromNode(field, node)
    return node_template.getTimesequence(field)


def _merge_node_pair(pair):
    dominant_node = pair[0]["node"]
    dominant_info = pair[0]["info"]
    recessive_node = pair[1]["node"]
    recessive_info = pair[1]["info"]
    existing_fields = [f["Name"] for f in dominant_info["fields"]]
    new_fields = [f for f in recessive_info["fields"] if f["Name"] not in existing_fields]

    node_set = dominant_node.getNodeset()
    field_module = node_set.getFieldmodule()
    node_template = node_set.createNodetemplate()

    for new_field in new_fields:
        field_description = {"Fields": [new_field]}
        field_module.readDescription(json.dumps(field_description))
        field = field_module.findFieldByName(new_field["Name"])
        if not field.isValid():
            print(f"Problem: field '{new_field['Name']}' not created.")
            return

        node_template.defineField(field)
        time_sequence = _get_field_time_sequence(recessive_node, new_field["Name"])
        if time_sequence.isValid():
            node_template.setTimesequence(field, time_sequence)
        dominant_node.merge(node_template)
        field_values = _get_real_field_values(recessive_node, new_field["Name"])
        _assign_real_field_values(dominant_node, field, field_values)


def _clone_node_in_output_region(node_info, region):
    print("Warning: This function is incomplete.")
    print(node_info)
    node = node_info["node"]
    node_set = node.getNodeset()
    field_module = node_set.getFieldmodule()
    available_field_info = field_module.writeDescription()
    print(available_field_info)
    # node_template = node_set.createNodetemplate()
    field_iterator = field_module.createFielditerator()
    field = field_iterator.next()
    field_information_list = []
    while field.isValid():
        print("field:", field.getName())
        time_sequence = _get_field_time_sequence(node, field.getName())
        print("has time sequence:", time_sequence, time_sequence and time_sequence.isValid())
        cast_field = field.castFiniteElement()
        if cast_field.isValid():
            print('finite element field')
        cast_field = field.castStoredMeshLocation()
        if cast_field.isValid():
            print('stored mesh location field')
        cast_field = field.castStoredString()
        if cast_field.isValid():
            print('stored string field')
        # result = node_template.defineField(field)
        # if result == ZINC_OK:
        #     field_details = _determine_field_details(field)
        #     field_information_list.append(field_details)
        field = field_iterator.next()


def merge_matching_markers(dominant_file, recessive_file, output_directory=None):
    if not os.path.isfile(dominant_file):
        raise ZincMergeInvalidInputs("Invalid dominant file given.")

    if not os.path.isfile(recessive_file):
        raise ZincMergeInvalidInputs("Invalid dominant file given.")

    c = Context("data")
    root_region = c.getDefaultRegion()
    dominant_region = root_region.createChild("dominant")
    recessive_region = root_region.createChild("recessive")
    output_region = root_region.createChild("output")

    result = dominant_region.readFile(dominant_file)
    if result != ZINC_OK:
        raise ZincMergeFileReadFailed(f"Failed to read file '{dominant_file}'")

    result = recessive_region.readFile(recessive_file)
    if result != ZINC_OK:
        raise ZincMergeFileReadFailed(f"Failed to read file '{recessive_file}'")

    dominant_marker_info = _fetch_marker_information(dominant_region)
    dominant_regions_marker_info = {
        "region": dominant_region,
        "marker_info": dominant_marker_info
    }

    recessive_marker_info = _fetch_marker_information(recessive_region)
    recessive_regions_marker_info = {
        "region": recessive_region,
        "marker_info": recessive_marker_info
    }

    # Find merge pairs.
    merge_pairs = _find_markers_to_merge(dominant_regions_marker_info, recessive_regions_marker_info)
    for pair in merge_pairs:
        _merge_node_pair(pair)
        _clone_node_in_output_region(pair[0], output_region)

    filename_parts = os.path.splitext(os.path.basename(dominant_file))
    if output_directory is None:
        output_directory = os.path.curdir
    output_exf = os.path.join(output_directory, filename_parts[0] + ".exf")
    result = dominant_region.writeFile(output_exf)

    output = None
    if result == ZINC_OK:
        output = output_exf

    return output


class Merger(object):
    """
    Merger object for managing the merge regions.
    """

    def __init__(self):
        self._context = Context("merger")
        self._dominant = None
        self._recessive = None
        self._output = self._context.getDefaultRegion().createChild("output")

    def _load_file(self, region_name, filename):
        root_region = self._context.getDefaultRegion()
        region = root_region.createChild(region_name)
        result = region.readFile(filename)
        if result != ZINC_OK:
            raise ZincMergeFileReadFailed(f"Failed to read file '{filename}'")

        return region

    def get_dominant_region(self):
        """
        Get the region for the dominant data.
        """
        return self._dominant

    def get_recessive_region(self):
        """
        Get the region for the recessive data.
        """
        return self._recessive

    def get_output_region(self):
        return self._output

    def load_dominant_data(self, filename):
        """
        Load the data from the filename into the dominant region.
        """
        self._dominant = self._load_file("dominant", filename)

    def load_recessive_data(self, filename):
        """
        Load the data from the filename into the recessive region.
        """
        self._recessive = self._load_file("recessive", filename)

    def fetch_marker_information(self, from_region):
        """
        From the region given by *from_region*
        """
        marker_information = {}
        if from_region == "dominant":
            marker_information = _fetch_marker_information(self._dominant)
        elif from_region == "recessive":
            marker_information = _fetch_marker_information(self._recessive)

        return marker_information

    @staticmethod
    def merge(dominant_node_information, recessive_node_information):
        """
        Merge data defined in the *recessive_node_information* parameter into
        the data defined in the *dominant_node_information* region.

        The \\*_node_information parameter is a dict with fields *node*, and *info*.
        The *node* field is a node identifier.
        """
        _merge_node_pair((dominant_node_information, recessive_node_information))

    def clone(self, node_information):
        if len(node_information) > 0:
            print(node_information)
            node = node_information[0]["node"]
            node_set = node.getNodeset()
            field_module = node_set.getFieldmodule()
            available_field_info = field_module.writeDescription()
            self._output.readDescription(available_field_info)
            for info in node_information:
                _clone_node_in_output_region(info, self._output)
