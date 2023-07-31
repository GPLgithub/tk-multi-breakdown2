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

    def get_published_files_for_items_data(self, items_data, fields):
        """
        Return the Published Files for the given items data.

        Items data are dictionaries with the following expected keys:
        - "node_name": The name of the 'node' that is to be operated on. Most DCCs have
          a concept of a node, path or some other way to address a particular
          object in the scene.
        - "node_type": The object type that this is. This is later passed to the
          update method so that it knows how to handle the object.
        - "path": Path on disk to the referenced object.
        - "extra_data": Optional key to pass some extra data to the update method
          in case we'd like to access them when updating the nodes.

        Items data dictionaries for which a Published File is found are updated
        with a "sg_data" key with the found Published File dictionary, allowing
        custom implementations to have full control on how scene objects are mapped
        to Published Files.

        This implementation is based on items data paths matching Published File paths.

        :param items_data: A list of dictionaries as returned by the scene scanner.
        :param fields: A list of fields to query from SG.
        :returns: A list of items data for which a Published File was found.
        """
        if not items_data:
            return []
        file_paths = [o["path"] for o in items_data]
        publishes = sgtk.util.find_publish(
            self.sgtk, file_paths, fields=fields, only_current_project=False
        )
        published_items_data = []
        for item_data in items_data:
            if item_data["path"] in publishes:
                item_data["sg_data"] = publishes[item_data["path"]]
                published_items_data.append(item_data)
        return published_items_data

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
        self.logger.debug("Retrieving Published files for items %s" % items)
        if not items:
            return {}

        # Build the filters to get all published files at once for all the file items.
        entities = []
        names = []
        tasks = []
        pf_types = []
        for file_item in items:
            if file_item.sg_data["task"]:
                # If we have a Task, use it
                tasks.append(file_item.sg_data["task"])
            else:
                # Otherwise match with the Entity and no task
                entities.append(file_item.sg_data["entity"])
            names.append(file_item.sg_data["name"])
            pf_types.append(file_item.sg_data["published_file_type"])

        # Published files will be found by their name, entity or task and published file type.
        filters = [
            ["name", "in", names],
            ["published_file_type", "in", pf_types],
        ]
        if tasks:
            if entities:
                # Match Published files linked to the Tasks or linked to the Entities
                # but with an empty Task
                filters.append(
                    {
                        "filter_operator": "any",
                        "filters": [
                            ["task", "in", tasks],
                            {
                                "filter_operator": "all",
                                "filters": [
                                    ["entity", "in", entities],
                                    ["task", "is", None]
                                ]
                            }
                        ]
                    }
                )
            else:
                # Match against the list of Tasks
                filters.append(["task", "in", tasks])
        else:
            # If we don't have tasks then we have entities
            # Match against them with an empty Task
            filters.extend([
                ["entity", "in", entities],
                ["task", "is", None]
            ])
        self.logger.debug("Retrieving published files with %s" % filters)

        # Get the query fields. This assumes all file items in the list have the same fields.
        fields = list(items[0].sg_data.keys()) + ["version_number", "path"]
        # Highest version first or latest one
        order = [
            {"field_name": "version_number", "direction": "desc"},
            {"field_name": "created_at", "direction": "desc"}
        ]
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
            ["name", "is", item.sg_data["name"]],
            ["published_file_type", "is", item.sg_data["published_file_type"]],
        ]
        # If we have a Task, use it for the match, otherwise match the
        # Entity with an empty Task
        if item.sg_data["task"]:
            filters.append(["task", "is", item.sg_data["task"]])
        else:
            filters.extend([
                ["entity", "is", item.sg_data["entity"]],
                ["task", "is", None]
            ])
        fields = list(item.sg_data.keys()) + ["version_number", "path"]
        # Highest version first or latest one
        order = [
            {"field_name": "version_number", "direction": "desc"},
            {"field_name": "created_at", "direction": "desc"}
        ]
        self.logger.debug("Retrieving published files with %s, %s" % (filters, fields))

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
