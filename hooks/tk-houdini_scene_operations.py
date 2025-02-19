# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import os
import sgtk
import hou

HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for Houdini.

    This implementation handles detection of alembic node paths.
    """

    def scan_scene(self):
        """
        The scan scene method is executed once at startup and its purpose is
        to analyze the current scene and return a list of references that are
        to be potentially operated on.

        The return data structure is a list of dictionaries. Each scene reference
        that is returned should be represented by a dictionary with three keys:

        - "node_name": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "node_type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.
        - "extra_data": Optional key to pass some extra data to the update method
          in case we'd like to access them when updating the nodes.

        Toolkit will scan the list of items, see if any of the objects matches
        a published file and try to determine if there is a more recent version
        available. Any such versions are then displayed in the UI as out of date.
        """

        items = []

        # get a list of all regular lembic nodes in the file
        alembic_nodes = hou.nodeType(hou.sopNodeTypeCategory(), "alembic").instances()

        # return an item for each alembic node found. the breakdown app will check
        # the paths of each looking for a template match and a newer version.
        for alembic_node in alembic_nodes:

            file_parm = alembic_node.parm("fileName")
            file_path = os.path.normpath(file_parm.eval())

            items.append(
                {
                    "node_name": alembic_node.path(),
                    "node_type": "alembic",
                    "path": file_path,
                }
            )

        return items

    def update(self, item):
        """
        Perform replacements given a number of scene items passed from the app.

        Once a selection has been performed in the main UI and the user clicks
        the update button, this method is called.

        :param item: Dictionary on the same form as was generated by the scan_scene hook above.
                     The sg_data key holds the Published File that the node should be
                     updated *to* rather than the current Published File.
        :returns: The path which was set on the item or ``False`` if no update was done.
        """

        node_name = item["node_name"]
        node_type = item["node_type"]
        sg_data = item["sg_data"]
        if not sg_data or not sg_data.get("path", {}).get("local_path", None):
            return False
        path = sg_data["path"]["local_path"]

        path = path.replace("\\", "/")

        if node_type == "alembic":
            alembic_node = hou.node(node_name)
            self.logger.debug(
                "Updating alembic node '{}' to: {}".format(node_name, path)
            )
            alembic_node.parm("fileName").set(path)
            return path

        # No update done
        return False
