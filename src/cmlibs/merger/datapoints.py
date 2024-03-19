import os

from cmlibs.zinc.field import Field

from cmlibs.merger.errors import ZincMergeInvalidInputs

from cmlibs.zinc.status import OK as ZINC_OK

from cmlibs.utils.zinc.general import ChangeManager


def merge(dominant_file, recessive_file, context, output_directory=None):
    if not os.path.isfile(dominant_file):
        raise ZincMergeInvalidInputs("Invalid dominant file given.")

    if not os.path.isfile(recessive_file):
        raise ZincMergeInvalidInputs("Invalid recessive file given.")

    root_region = context.getDefaultRegion()
    dominant_region = root_region.createChild("dominant")
    recessive_region = root_region.createChild("recessive")

    dominant_region.readFile(dominant_file)
    recessive_region.readFile(recessive_file)

    fm_d = dominant_region.getFieldmodule()
    fm_r = recessive_region.getFieldmodule()

    fc_r = fm_r.createFieldcache()
    fc_d = fm_d.createFieldcache()

    datapoints_to_add_to_field = {}
    with ChangeManager(fm_d):
        datapoints_r = fm_r.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        datapoints_d = fm_d.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
        field_iterator = fm_r.createFielditerator()
        field = field_iterator.next()
        field_list = []
        while field.isValid():
            if field.castGroup().isValid():
                field_d = fm_d.findFieldByName(field.getName())
                if not field_d.isValid():
                    field_group = fm_d.createFieldGroup()
                    field_group.setName(field.getName())
                    field_list.append((field.castGroup(), field_group))
                elif field_d.castGroup().isValid():
                    field_list.append((field.castGroup(), field_d.castGroup()))
            field = field_iterator.next()

    with ChangeManager(fm_d):
        datapoint_template = datapoints_d.createNodetemplate()
        coordinates_r = fm_r.findFieldByName('coordinates')
        coordinates_d = fm_d.findFieldByName('coordinates')
        datapoint_template.defineField(coordinates_d)
        datapoints_iterator = datapoints_r.createNodeiterator()
        datapoint_r = datapoints_iterator.next()
        while datapoint_r.isValid():
            fc_r.setNode(datapoint_r)
            result, values = coordinates_r.evaluateReal(fc_r, 3)
            datapoint = datapoints_d.createNode(-1, datapoint_template)
            fc_d.setNode(datapoint)
            coordinates_d.assignReal(fc_d, values)
            for field_r, field_d in field_list:
                datapoint_group_r = field_r.getNodesetGroup(datapoints_r)
                datapoint_group_d = field_d.getOrCreateNodesetGroup(datapoints_d)
                if datapoint_group_r.containsNode(datapoint_r):
                    datapoint_group_d.addNode(datapoint)
            datapoint_r = datapoints_iterator.next()

    filename_parts = os.path.splitext(os.path.basename(dominant_file))
    if output_directory is None:
        output_directory = os.path.curdir
    output_exf = os.path.join(output_directory, f'{filename_parts[0]}_merged.exf')
    result = dominant_region.writeFile(output_exf)

    output = None
    if result == ZINC_OK:
        output = output_exf

    return output
