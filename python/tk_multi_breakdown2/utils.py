# Copyright (c) 2021 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk, Inc.

from .framework_qtwidgets import utils


def get_ui_published_file_fields(app):
    """
    Returns a list of ShotGrid fields we want to retrieve when querying ShotGrid. We're going through each widget
    configuration in order to be sure to have all the necessary data to fill the fields.

    :param app: The app we're running the command from
    :returns: A list of ShotGrid Published File fields
    """

    fields = []

    # in order to be able to return all the needed ShotGrid fields, we need to look for the way the UI is configured
    file_item_config = app.execute_hook_method("hook_ui_config", "file_item_details")

    fields += utils.resolve_sg_fields(file_item_config.get("top_left"))
    fields += utils.resolve_sg_fields(file_item_config.get("top_right"))
    fields += utils.resolve_sg_fields(file_item_config.get("body"))
    if file_item_config["thumbnail"]:
        fields.append("image")
        # Add the linked Version's image field to be able to fall back on it if needed.
        fields.append("version.Version.image")

    main_file_history_config = app.execute_hook_method(
        "hook_ui_config", "main_file_history_details"
    )

    fields += utils.resolve_sg_fields(main_file_history_config.get("header"))
    fields += utils.resolve_sg_fields(main_file_history_config.get("body"))
    if main_file_history_config["thumbnail"]:
        if "image" not in fields:
            fields.append("image")
        # Add the linked Version's image field to be able to fall back on it if needed.
        if "version.Version.image" not in fields:
            fields.append("version.Version.image")

    file_history_config = app.execute_hook_method(
        "hook_ui_config", "file_history_details"
    )

    fields += utils.resolve_sg_fields(file_history_config.get("top_left"))
    fields += utils.resolve_sg_fields(file_history_config.get("top_right"))
    fields += utils.resolve_sg_fields(file_history_config.get("body"))
    if file_history_config["thumbnail"]:
        if "image" not in fields:
            fields.append("image")
        # We need the linked Version's image if setting
        # use_version_thumbnail_as_fallback is enabled.
        if "version.Version.image" not in fields:
            fields.append("version.Version.image")

    return list(set(fields))


def get_thumbnail_field_for_item(item, use_version_thumbnail_as_fallback=True):
    """
    Get the field to use for the thumbnail for the given item.

    Check if a thumbnail is available for the given item, and return
    the field name to download it from. If not available and falling back
    on the Version is allowed, check if one is available for it and,
    if so, return the dotted field to use to retrieve it.

    If there's no image field or no image to use, it returns None.

    :param item: The QStandardItem to get the thumbnail field for.
    :param use_version_thumbnail_as_fallback: Whether to use the Version's
        thumbnail as a fallback if the item doesn't have one.
    :returns: A SG field, e.g. "image", or ``None``.
    """
    sg_data = item.sg_data
    if not sg_data:
        return None
    # When it's an empty thumbnail, it's an AWS link with a "no_preview_t.jpg" image.
    if sg_data.get("image") and "no_preview_t.jpg" not in sg_data.get("image"):
        return "image"
    elif (
            use_version_thumbnail_as_fallback and sg_data.get("version.Version.image")
            and "no_preview_t.jpg" not in sg_data.get("version.Version.image")
    ):
        return "version.Version.image"
    return None
