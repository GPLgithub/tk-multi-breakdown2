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

try:
    import builtins
except ImportError:
    try:
        import __builtins__ as builtins
    except ImportError:
        import __builtin__ as builtins

builtins.vrNodeService = vrNodeService  # noqa F821
builtins.vrReferenceService = vrReferenceService  # noqa F821
builtins.vrFileIOService = vrFileIOService  # noqa F821


HookBaseClass = sgtk.get_hook_baseclass()


class BreakdownSceneOperations(HookBaseClass):
    """A hook to perform scene operations in VRED necessary for Breakdown 2 App."""

    def __init__(self, *args, **kwargs):
        """Class constructor."""

        super(BreakdownSceneOperations, self).__init__(*args, **kwargs)

        # Keep track of the scene change callbacks that are registered, so that they can be
        # disconnected at a later time.
        self._on_references_changed_cb = None

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

        refs = []

        for r in vrReferenceService.getSceneReferences():  # noqa F821

            # we only want to keep the top references
            has_parent = vrReferenceService.getParentReferences(r)  # noqa F821
            if has_parent:
                continue

            if r.hasSmartReference():
                node_type = "smart_reference"
                path = r.getSmartPath()
            elif r.hasSourceReference():
                node_type = "source_reference"
                path = r.getSourcePath()
            else:
                node_type = "reference"
                path = None

            if path:
                refs.append(
                    {
                        "node_name": r.getName(),
                        "node_type": node_type,
                        "path": path,
                        "extra_data": {"node_id": r.getObjectId()},
                    }
                )

        return refs

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
        if not sg_data or not sg_data.get("path", {}).get("local_path", None):
            return False
        path = sg_data["path"]["local_path"]
        extra_data = item["extra_data"]

        ref_node = get_reference_by_id(extra_data["node_id"])
        if not ref_node:
            self.logger.error("Couldn't get reference node named {}".format(node_name))
            return

        new_node_name = os.path.splitext(os.path.basename(path))[0]

        if node_type == "source_reference":
            ref_node.setSourcePath(path)
            ref_node.loadSourceReference()
            ref_node.setName(new_node_name)
            return path
        elif node_type == "smart_reference":
            ref_node.setSmartPath(path)
            vrReferenceService.reimportSmartReferences([ref_node])  # noqa F821
            return path
        # No update done
        return False

    def register_scene_change_callback(self, scene_change_callback):
        """
        Register the callback such that it is executed on a scene change event.

        This hook method is useful to reload the breakdown data when the data in the scene has
        changed.

        For Alias, the callback is registered with the AliasEngine event watcher to be
        triggered on a PostRetrieve event (e.g. when a file is opened).

        :param scene_change_callback: The callback to register and execute on scene chagnes.
        :type scene_change_callback: function
        """

        # Keep track of the callback so that it can be disconnected later
        self._on_references_changed_cb = lambda nodes, cb=scene_change_callback: cb()

        # Set up the signal/slot connection to potentially call the scene change callback
        # based on how the references have cahnged.
        # NOTE ideally the VRED API would have signals for specific reference change events,
        # until then, any reference change will trigger a full reload of the app.
        vrReferenceService.referencesChanged.connect(self._on_references_changed_cb)  # noqa F821

    def unregister_scene_change_callback(self):
        """Unregister the scene change callbacks by disconnecting any signals."""

        if self._on_references_changed_cb:
            vrReferenceService.referencesChanged.disconnect(  # noqa F821
                self._on_references_changed_cb
            )
            self._on_references_changed_cb = None


def get_reference_by_id(ref_id):
    """
    Get a reference node from its name.

    :param ref_name: Name of the reference we want to get the associated node from
    :returns: The reference node associated to the reference name
    """
    ref_list = vrReferenceService.getSceneReferences()  # noqa F821
    for r in ref_list:
        if r.getObjectId() == ref_id:
            return r
    return None
