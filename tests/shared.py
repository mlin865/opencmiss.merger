import os.path

here = os.path.abspath(os.path.dirname(__file__))


def resource_path(resource_name):
    return os.path.join(here, "resources", resource_name)
