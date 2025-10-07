import uuid
from typing import Any
import i18n

from typing_extensions import override

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.dotdict import dotdict
from lfx.schema.message import Message


class IDGeneratorComponent(Component):
    display_name = i18n.t('components.helpers.id_generator.display_name')
    description = i18n.t('components.helpers.id_generator.description')
    icon = "fingerprint"
    name = "IDGenerator"
    legacy = True

    inputs = [
        MessageTextInput(
            name="unique_id",
            display_name=i18n.t(
                'components.helpers.id_generator.unique_id.display_name'),
            info=i18n.t('components.helpers.id_generator.unique_id.info'),
            refresh_button=True,
            tool_mode=True,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.id_generator.outputs.id.display_name'),
            name="id",
            method="generate_id"
        ),
    ]

    @override
    def update_build_config(self, build_config: dotdict, field_value: Any, field_name: str | None = None):
        try:
            if field_name == "unique_id":
                new_id = str(uuid.uuid4())
                build_config[field_name]["value"] = new_id

                success_message = i18n.t(
                    'components.helpers.id_generator.success.id_refreshed', id=new_id)
                self.status = success_message

        except Exception as e:
            error_message = i18n.t(
                'components.helpers.id_generator.errors.refresh_failed', error=str(e))
            self.status = error_message

        return build_config

    def generate_id(self) -> Message:
        try:
            # Use existing ID if provided, otherwise generate a new one
            unique_id = self.unique_id if self.unique_id and self.unique_id.strip() else str(uuid.uuid4())

            success_message = i18n.t(
                'components.helpers.id_generator.success.id_generated', id=unique_id)
            self.status = success_message

            return Message(text=unique_id)

        except Exception as e:
            error_message = i18n.t(
                'components.helpers.id_generator.errors.generation_failed', error=str(e))
            self.status = error_message
            return Message(text=error_message)
