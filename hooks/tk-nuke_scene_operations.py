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
import nuke
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """
    Breakdown operations for Nuke.

    This implementation handles detection of Nuke read nodes,
    geometry nodes and camera nodes.
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

        nodes = []

        # If we're in Nuke Studio or Hiero, we need to see if there are any
        # clips we need to be aware of that we might want to point to newer
        # publishes.
        if self.parent.engine.studio_enabled or self.parent.engine.hiero_enabled:

            import hiero

            for project in hiero.core.projects():
                for clip in project.clipsBin().clips():
                    files = clip.activeItem().mediaSource().fileinfos()
                    for file in files:
                        path = file.filename().replace("/", os.path.sep)
                        nodes.append(
                            dict(
                                node_name=clip.activeItem().name(),
                                node_type="Clip",
                                path=path,
                                extra_data={"clip": clip.activeItem()},
                            )
                        )

        # Hiero doesn't have nodes to check, so just return the clips.
        if self.parent.engine.hiero_enabled:
            return nodes

        # first let's look at the read nodes
        for node in nuke.allNodes("Read"):

            node_name = node.name()

            # note! We are getting the "abstract path", so contains
            # %04d and %V rather than actual values.
            path = node.knob("file").value().replace("/", os.path.sep)
            nodes.append({"node_name": node_name, "node_type": "Read", "path": path})

        # then the read geometry nodes
        for node in nuke.allNodes("ReadGeo2"):

            node_name = node.name()

            path = node.knob("file").value().replace("/", os.path.sep)
            nodes.append(
                {"node_name": node_name, "node_type": "ReadGeo2", "path": path}
            )

        # then the read camera nodes
        for node in nuke.allNodes("Camera2"):

            node_name = node.name()

            path = node.knob("file").value().replace("/", os.path.sep)
            nodes.append({"node_name": node_name, "node_type": "Camera2", "path": path})

        return nodes

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

        node_type_list = ["Read", "ReadGeo2", "Camera2"]

        node_name = item["node_name"]
        node_type = item["node_type"]
        extra_data = item["extra_data"]
        if not sg_data or not sg_data.get("path", {}).get("local_path", None):
            return False
        path = sg_data["path"]["local_path"].replace(os.path.sep, "/")

        if node_type in node_type_list:
            self.logger.debug("Node %s: Updating to version %s" % (node_name, path))
            node = nuke.toNode(node_name)
            node.knob("file").setValue(path)
            return path

        if node_type == "Clip":
            self.logger.debug("Clip %s: Updating to version %s" % (node_name, path))
            clip = extra_data["clip"]
            clip.reconnectMedia(path)
            return path
        # No update done
        return False
