# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class GetPublishedFiles(HookBaseClass):
    """"""

    def get_published_files_from_scene_objects(self, scene_objects, fields):
        """
        Return the Published Files for the given scene objects.

        Scene objects are dictionaries with the following expected keys:
        - "node_name": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "node_type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.
        - "extra_data": Optional key to pass some extra data to the update method
          in case we'd like to access them when updating the nodes.

        :param scene_object: A list of dictionaries as returned by the scene scanner.
        :param fields: A list of fields to query from SG.
        :returns: A dictionary where keys are file paths and values SG Published Files
                  dictionaries.
        """
        if not scene_objects:
            return {}
        file_paths = [o["path"] for o in scene_objects]
        return sgtk.util.find_publish(
            self.sgtk, file_paths, fields=fields, only_current_project=False
        )


    def get_published_files_for_items(self, items, data_retriever=None):
        """
        Make an API request to get all published files for the given file items.

        :param items: a list of :class`FileItem` we want to get published files for.
        :type items: List[FileItem]
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        if not items:
            return {}

        # Build the filters to get all published files for at once for all the file items.
        entities = []
        names = []
        tasks = []
        pf_types = []
        for file_item in items:
            entities.append(file_item.sg_data["entity"])
            names.append(file_item.sg_data["name"])
            tasks.append(file_item.sg_data["task"])
            pf_types.append(file_item.sg_data["published_file_type"])

        # Published files will be found by their entity, name, task and published file type.
        filters = [
            ["entity", "in", entities],
            ["name", "in", names],
            ["task", "in", tasks],
            ["published_file_type", "in", pf_types],
        ]

        # Get the query fields. This assumes all file items in the list have the same fields.
        fields = list(items[0].sg_data.keys()) + ["version_number", "path"]
        order = [{"field_name": "version_number", "direction": "desc"}]

        if data_retriever:
            # Execute async and return the background task id.
            return data_retriever.execute_find(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )

        # No data retriever, execute synchronously and return the published file data result.
        return self.sgtk.shotgun.find(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=order,
        )

    def get_latest_published_file(self, item, data_retriever=None, **kwargs):
        """
        Query ShotGrid to get the latest published file for the given item.

        :param item: :class`FileItem` object we want to get the latest published file for
        :type item: :class`FileItem`
        :param data_retreiver: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :type data_retriever: ShotgunDataRetriever

        :return: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        :rtype: str | dict
        """

        filters = [
            ["entity", "is", item.sg_data["entity"]],
            ["name", "is", item.sg_data["name"]],
            ["task", "is", item.sg_data["task"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]
        fields = list(item.sg_data.keys()) + ["version_number", "path"]
        order = [{"field_name": "version_number", "direction": "desc"}]

        # todo: check if this work with url published files
        # todo: need to check for path comparison?
        if data_retriever:
            result = data_retriever.execute_find_one(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )
        else:
            result = self.sgtk.shotgun.find_one(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )

        return result
