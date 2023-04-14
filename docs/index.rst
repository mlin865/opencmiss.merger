CMLibs Merger
=============

**CMLibs Merger** is a Python package for merging real valued fields from a set of nodes in a markers group onto another set of nodes in a markers group.

Usage
-----

::

 from cmlibs.merger.points import Merger

 merger = Merger()

 # Load node data into merger.
 merger.load_dominant_data(dominant_node_file)
 merger.load_recessive_data(recessive_node_file)

 # Retrieve information on nodes in marker group.
 target_info = merger.fetch_marker_information("dominant")
 source_info = merger.fetch_marker_information("recessive")

 # Setup merge information.
 dominant_item = {
     "node": 1 # Node identifier
     "info": marker_information # Entry from target_info information.
 }
 recessive_item = {
     "node": 1 # Node identifier
     "info": marker_information # Entry from source_info information.
 }

 # Merge the recessive item real value fields into the dominant item.
 merger.merge(dominant_item, recessive_item)


Package API
-----------

Points Module
*************

.. automodule:: cmlibs.merger.points

.. autoclass:: cmlibs.merger.points.Merger
   :members:
