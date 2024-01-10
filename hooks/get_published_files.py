# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from collections import defaultdict
import copy
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class GetPublishedFiles(HookBaseClass):
    """
    Hook called to retrieve the Published Files for the items in the scene.
    """

    def get_published_files_for_items_data(self, items_data, fields, filters=None):
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
        :param filters: An optional list of filters to use when querying SG.
        :returns: A list of items data for which a Published File was found.
        """
        if not items_data:
            return []
        file_paths = [o["path"] for o in items_data]
        publishes = sgtk.util.find_publish(
            self.sgtk, file_paths, fields=fields, filters=filters, only_current_project=False
        )
        published_items_data = []
        for item_data in items_data:
            if item_data["path"] in publishes:
                item_data["sg_data"] = publishes[item_data["path"]]
                published_items_data.append(item_data)
        return published_items_data

    def get_published_files_for_items(self, items, data_retriever=None, filters=None):
        """
        Make an API request to get all published files for the given file items.

        Use the publish_history_group_by_fields setting to build the filters to get all
        published files at once for all the file items.

        For example, if the publish_history_group_by_fields setting is set to
        ["project", "entity", "task", "name", "published_file_type"]
        then it will look for all file items which have matching values for all these fields.

        :param items: a list of :class`FileItem` we want to get published files for.
        :param data_retriever: If provided, the api request will be async. The default value
            will execute the api request synchronously.
        :param filters: A list of filters to use when querying SG.

        :returns: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        """
        self.logger.debug("Retrieving Published files for items %s" % items)
        if not items:
            return {}

        # Build the filters to get all published files at once for all the file items.
        group_by_fields = self.parent.get_setting("publish_history_group_by_fields")
        sg_data_by_field = defaultdict(list)
        for file_item in items:
            for field in group_by_fields:
                if file_item.sg_data.get(field):
                    sg_data_by_field[field].append(
                        file_item.sg_data[field]
                    )
                else:
                    # If there's no data for this field, we still need to make sure
                    # there's an empty list for it to build the filters.
                    sg_data_by_field[field] = []

        # Let's copy the filters so we don't modify the original list.
        filters = copy.deepcopy(filters) if filters else []

        for field, values in sg_data_by_field.items():
            if values:
                filters.append([field, "in", values])
            else:
                filters.append([field, "is", None])

        # Get the query fields. This assumes all file items in the list have the same fields.
        fields = list(items[0].sg_data.keys()) + ["version_number", "path"]
        self.logger.debug("Retrieving published files with %s, %s" % (filters, fields))
        # Highest version first or latest one
        order = [
            {"field_name": "version_number", "direction": "desc"},
            {"field_name": "created_at", "direction": "desc"}
        ]
        if data_retriever:
            # Execute async and return the background task id.
            result = data_retriever.execute_find(
                "PublishedFile",
                filters=filters,
                fields=fields,
                order=order,
            )
            return result

        # No data retriever, execute synchronously and return the published file data result.
        result = self.sgtk.shotgun.find(
            "PublishedFile",
            filters=filters,
            fields=fields,
            order=order,
        )
        self.logger.debug("Retrieved %d Published Files" % len(result))
        return result

    def get_latest_published_file(self, item, data_retriever=None, **kwargs):
        """
        Query ShotGrid to get the latest Published file for the given item.

        Get all the Published Files which have the same values for the fields defined in the
        publish_history_group_by_fields setting. Then sort them by version number and
        creation date and return the first one.

        :param item: :class`FileItem` object we want to get the latest published file for
        :param data_retriever: If provided, the api request will be async. The default value
            will execute the api request synchronously.

        :returns: If the request is async, then the request task id is returned, else the
            published file data result from the api request.
        """

        group_by_fields = self.parent.get_setting("publish_history_group_by_fields")
        filters = []
        for field in group_by_fields:
            filters.append([field, "is", item.sg_data[field]])
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
            self.logger.debug("Found latest Published File %s" % result)
        return result
