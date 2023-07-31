# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import copy

import sgtk

from .item import FileItem
from .. import constants


class BreakdownManager(object):
    """This class is used for managing and executing file updates."""

    def __init__(self, bundle):
        """Initialize the manager."""

        self._bundle = bundle

    @sgtk.LogManager.log_timing
    def scan_scene(self, execute_in_main_thread=True):
        """
        Scan the current scene to return a list of scene references.

        The return dict value has the following key-values:

            node (str)
                The name of the node which holds the reference.
            type (str)
                The node type.
            path (str)
                The reference file path.
            extra_data (dict)
                Extra data for the reference (optional).

        :param execute_in_main_thread: True will ensure the hook method is executed in the
            main thread, else False will execute in the current thread. Default is True, since
            the scan_scene function will need to execute DCC functionality that likely needs
            to execute in the main thread (e.g. GUI events).
        :type execute_in_main_thread: bool

        :return: A list of scene references.
        :rtype: dict
        """

        if execute_in_main_thread:
            # Ensure that the scan scene operation is executed in the main UI thread. Many
            # apps are sensitive to these types of operations happening in other threads.
            return self._bundle.engine.execute_in_main_thread(
                self._bundle.execute_hook_method, "hook_scene_operations", "scan_scene"
            )

        # Execute in the current thread
        return self._bundle.execute_hook_method("hook_scene_operations", "scan_scene")

    @sgtk.LogManager.log_timing
    def get_published_files_for_items_data(
        self, items_data, extra_fields=None
    ):
        """
        Query the ShotGrid API to get the Published Files for the given items data.

        :param items_data: A list of dictionaries as retrieved by scan scene.
        :type items_data: List[dict]
        :param extra_fields: A list of ShotGrid fields to append to the ShotGrid query
                             when retreiving the published files.
        :type extra_fields: List[str]

        :return: The Published Files data.
        :rtype: dict
        """
        # Get the published file fields to pass to the query
        fields = self.get_published_file_fields()
        if extra_fields is not None:
            fields += extra_fields

        return self._bundle.execute_hook_method(
            "hook_get_published_files",
            "get_published_files_for_items_data",
            items_data=items_data,
            fields=fields,
        )

    def get_file_items(self, scene_objects):
        """
        Get the file item objects for the given scene objects.

        Scene objects that do not have a corresponding ShotGrid Published File will be omitted
        from the result (a FileItem will not be created for it).

        The `scene_objects` dict param expects the key-values:

            node (str)
                The name of the node which holds the reference.
            type (str)
                The node type.
            path (str)
                The reference file path.
            extra_data (dict)
                Extra data for the reference (optional).
            sg_data (dict)
                A dictionary for the Published File retrieved from ShotGrid.

        :param scene_objects: Objects from the DCC. This value can be the result returned by
            the `scan_scene` method.
        :type scene_objects: dict

        :return: A list of FileItem objects representing the scene objects.
        :rtype: List[FileItem]
        """

        file_items = []

        for obj in scene_objects:
            if obj.get("sg_data"):
                file_item = FileItem(obj["node_name"], obj["node_type"], obj["path"])
                file_item.extra_data = obj.get("extra_data")
                # Make a shallow copy in case it is shared between multiple items.
                file_item.sg_data = copy.copy(obj["sg_data"])
                file_items.append(file_item)

        return file_items

    def get_published_file_fields(self):
        """
        Get the fields to pass to the query to retrieve the published files when scanning the
        scene.

        :return: The published file fields.
        :rtype: list<str>
        """

        return constants.PUBLISHED_FILES_FIELDS + self._bundle.get_setting(
            "published_file_fields", []
        )

    def get_latest_published_file(self, item, data_retriever=None):
        """
        Get the latest available published file according to the current item context.

        :param item: :class`FileItem` object we want to get the latest published file
        :type item: FileItem
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: The latest published file as a ShotGrid entity dictionary if the request was
            synchronous, else the request background task id if the request was async.
        """

        if not item or not item.sg_data:
            return None if data_retriever else {}

        result = self._bundle.execute_hook_method(
            "hook_get_published_files",
            "get_latest_published_file",
            item=item,
            data_retriever=data_retriever,
        )

        # Only set the latest published file data if the result was immediately returned.
        if data_retriever is None:
            item.latest_published_file = result

        return result

    @sgtk.LogManager.log_timing
    def get_published_files_for_items(self, items, data_retriever=None):
        """
        Get all published files for the given items.

        The published files returned may then be parsed to determine the latest published
        file for each item.

        :param items: the list of :class`FileItem` we want to get published files for.
        :type items: List[FileItem]
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        if not items:
            return None if data_retriever else {}

        return self._bundle.execute_hook_method(
            "hook_get_published_files",
            "get_published_files_for_items",
            items=items,
            data_retriever=data_retriever,
        )

    def get_published_file_history(self, item, extra_fields=None):
        """
        Get the published history for the selected item. It will gather all the published files with the same context
        than the current item (project, name, task, ...)

        :param extra_fields: A list of ShotGrid fields to append to the ShotGrid query fields.
        :param item: :class`FileItem` object we want to get the published file history
        :param extra_fields: A list of ShotGrid fields to append to the ShotGrid query
                             for published files.

        :returns: A list of ShotGrid published file dictionary
        """

        if not item.sg_data:
            return []

        fields = constants.PUBLISHED_FILES_FIELDS + self._bundle.get_setting(
            "published_file_fields", []
        )
        if extra_fields is not None:
            fields += extra_fields

        filters = [
            ["project", "is", item.sg_data["project"]],
            ["name", "is", item.sg_data["name"]],
            ["task", "is", item.sg_data["task"]],
            ["entity", "is", item.sg_data["entity"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]

        pfs = self._bundle.shotgun.find(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=[{"direction": "desc", "field_name": "version_number"}],
        )

        if pfs:
            item.latest_published_file = pfs[0]
            return pfs

        # Return empty list indicating no publish file history was found.
        return []

    def update_to_latest_version(self, item):
        """
        Update the item to its latest version.

        :param item: Item to update
        :type item: FileItem

        :return: True if the item requires the data model to update, else False will not
            trigger a model update.
        :rtype: bool
        """

        if not item.latest_published_file:
            return False

        return self.update_to_specific_version(item, item.latest_published_file)

    def update_to_specific_version(self, item, sg_data):
        """
        Update the item to a specific version.

        :param item: Item to update
        :type item: FileItem
        :param sg_data: Dictionary of ShotGrid data representing the published file we want to update the item to
        :type sg_data: dict

        :return: True if the item requires the data model to update, else False will not
            trigger a model update.
        :rtype: bool
        """

        item_dict = item.to_dict()
        item_dict["sg_data"] = sg_data

        new_path = self._bundle.execute_hook_method(
            "hook_scene_operations",
            "update",
            item=item_dict,
        )

        if new_path:
            # Only update the file item if an update was done. Updating the item will affect the data
            # model directly
            item.sg_data = sg_data
            item.path = new_path
            item.extra_data = item_dict["extra_data"]

        return bool(new_path)
