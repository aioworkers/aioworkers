# SPDX-FileCopyrightText: 2022-present Alexander Malev <malev@somedev.ru>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from datetime import datetime
from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl


class CustomMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "custom"

    def make_readme(self, version: str):
        with open(self.config["readme"]) as readme_file:
            readme = readme_file.read()

        history_item = "{} ({})".format(
            version,
            datetime.now().date(),
        )
        with open(self.config["history"]) as history_file:
            history = history_file.read().split("\n" * 4, 4)
            history[0] = history[0].replace(
                "Development\n-----------",
                history_item + "\n" + "-" * len(history_item),
            )
            history.pop()
            history.append("")
        return "\n\n\n".join([readme] + history)

    def update(self, metadata: dict[str, Any]) -> None:
        """
        Update the project table's metadata.
        """

        metadata["readme"] = {
            "content-type": self.config["readme_content_type"],
            "text": self.make_readme(metadata["version"]),
        }


@hookimpl  # type: ignore[misc]
def hatch_register_metadata_hook() -> type[MetadataHookInterface]:
    return CustomMetadataHook
