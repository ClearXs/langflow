from typing import cast
import i18n

from lfx.custom import Component
from lfx.io import BoolInput, HandleInput, Output, StrInput
from lfx.schema.data import Data


class NotifyComponent(Component):
    display_name = i18n.t('components.logic.notify.display_name')
    description = i18n.t('components.logic.notify.description')
    icon = "Notify"
    name = "Notify"
    beta: bool = True

    inputs = [
        StrInput(
            name="context_key",
            display_name=i18n.t(
                'components.logic.notify.context_key.display_name'),
            info=i18n.t('components.logic.notify.context_key.info'),
            required=True,
        ),
        HandleInput(
            name="input_value",
            display_name=i18n.t(
                'components.logic.notify.input_value.display_name'),
            info=i18n.t('components.logic.notify.input_value.info'),
            required=False,
            input_types=["Data", "Message", "DataFrame"],
        ),
        BoolInput(
            name="append",
            display_name=i18n.t('components.logic.notify.append.display_name'),
            info=i18n.t('components.logic.notify.append.info'),
            value=False,
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.logic.notify.outputs.result.display_name'),
            name="result",
            method="notify_components",
            cache=False,
        ),
    ]

    async def notify_components(self) -> Data:
        """Processes and stores a notification in the component's context.

        Normalizes the input value to a `Data` object and stores it under the
        specified context key. If `append` is True, adds the value to a list
        of notifications; otherwise, replaces the existing value. Updates the
        component's status and activates related state vertices in the graph.

        Returns:
            The processed `Data` object stored in the context.

        Raises:
            ValueError: If the component is not part of a graph.
        """
        if not self._vertex:
            error_message = i18n.t(
                'components.logic.notify.errors.must_be_in_graph')
            raise ValueError(error_message)

        input_value: Data | str | dict | None = self.input_value
        if input_value is None:
            input_value = Data(text="")
        elif not isinstance(input_value, Data):
            if isinstance(input_value, str):
                input_value = Data(text=input_value)
            elif isinstance(input_value, dict):
                input_value = Data(data=input_value)
            else:
                input_value = Data(text=str(input_value))

        if input_value:
            if self.append:
                current_data = self.ctx.get(self.context_key, [])
                if not isinstance(current_data, list):
                    current_data = [current_data]
                current_data.append(input_value)
                self.update_ctx({self.context_key: current_data})
                success_message = i18n.t('components.logic.notify.success.appended_to_context',
                                         key=self.context_key)
            else:
                self.update_ctx({self.context_key: input_value})
                success_message = i18n.t('components.logic.notify.success.stored_in_context',
                                         key=self.context_key)

            self.status = success_message
        else:
            no_record_message = i18n.t(
                'components.logic.notify.warnings.no_record_provided')
            self.status = no_record_message

        self._vertex.is_state = True
        self.graph.activate_state_vertices(
            name=self.context_key, caller=self._id)
        return cast("Data", input_value)
