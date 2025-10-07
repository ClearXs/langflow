import i18n

from lfx.base.prompts.api_utils import process_prompt_template
from lfx.custom.custom_component.component import Component
from lfx.inputs.inputs import DefaultPromptField
from lfx.io import MessageTextInput, Output, PromptInput
from lfx.schema.message import Message
from lfx.template.utils import update_template_values


class PromptComponent(Component):
    display_name: str = i18n.t('components.processing.prompt.display_name')
    description: str = i18n.t('components.processing.prompt.description')
    documentation: str = "https://docs.langflow.org/components-prompts"
    icon = "braces"
    trace_type = "prompt"
    name = "Prompt Template"
    priority = 0  # Set priority to 0 to make it appear first

    inputs = [
        PromptInput(
            name="template",
            display_name=i18n.t(
                'components.processing.prompt.template.display_name'),
            info=i18n.t('components.processing.prompt.template.info'),
        ),
        MessageTextInput(
            name="tool_placeholder",
            display_name=i18n.t(
                'components.processing.prompt.tool_placeholder.display_name'),
            tool_mode=True,
            advanced=True,
            info=i18n.t('components.processing.prompt.tool_placeholder.info'),
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.processing.prompt.outputs.prompt.display_name'),
            name="prompt",
            method="build_prompt"
        ),
    ]

    async def build_prompt(self) -> Message:
        """Build the prompt message from template and variables."""
        try:
            # Validate template
            if not hasattr(self, 'template') or not self.template:
                error_msg = i18n.t(
                    'components.processing.prompt.errors.empty_template')
                self.status = error_msg
                raise ValueError(error_msg)

            # Create prompt from template
            prompt = Message.from_template(**self._attributes)

            if not prompt or not prompt.text:
                warning_msg = i18n.t(
                    'components.processing.prompt.warnings.empty_prompt_generated')
                self.status = warning_msg
                return Message(text="")

            # Log successful creation
            self.log(i18n.t(
                'components.processing.prompt.logs.prompt_created', length=len(prompt.text)))

            # Set status with truncated prompt for display
            max_display_length = 200
            if len(prompt.text) > max_display_length:
                display_text = prompt.text[:max_display_length] + "..."
            else:
                display_text = prompt.text

            success_msg = i18n.t(
                'components.processing.prompt.success.prompt_built', preview=display_text)
            self.status = success_msg

            return prompt

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.prompt.errors.prompt_build_failed', error=str(e))
            self.status = error_msg
            self.log(error_msg, "error")
            raise ValueError(error_msg) from e

    def _update_template(self, frontend_node: dict):
        """Update the template in the frontend node."""
        try:
            prompt_template = frontend_node["template"]["template"]["value"]
            custom_fields = frontend_node["custom_fields"]
            frontend_node_template = frontend_node["template"]

            # Process the prompt template
            _ = process_prompt_template(
                template=prompt_template,
                name="template",
                custom_fields=custom_fields,
                frontend_node_template=frontend_node_template,
            )

            self.log(i18n.t('components.processing.prompt.logs.template_updated'))
            return frontend_node

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.prompt.errors.template_update_failed', error=str(e))
            self.log(error_msg, "error")
            # Return original node if update fails
            return frontend_node

    async def update_frontend_node(self, new_frontend_node: dict, current_frontend_node: dict):
        """This function is called after the code validation is done."""
        try:
            frontend_node = await super().update_frontend_node(new_frontend_node, current_frontend_node)
            template = frontend_node["template"]["template"]["value"]

            # Process the prompt template
            # Kept it duplicated for backwards compatibility
            _ = process_prompt_template(
                template=template,
                name="template",
                custom_fields=frontend_node["custom_fields"],
                frontend_node_template=frontend_node["template"],
            )

            # Update template values from current node
            # Now that template is updated, we need to grab any values that were set in the current_frontend_node
            # and update the frontend_node with those values
            update_template_values(
                new_template=frontend_node, previous_template=current_frontend_node["template"])

            self.log(
                i18n.t('components.processing.prompt.logs.frontend_node_updated'))
            return frontend_node

        except Exception as e:
            error_msg = i18n.t(
                'components.processing.prompt.errors.frontend_node_update_failed', error=str(e))
            self.log(error_msg, "error")
            # Return the new node if update fails
            return new_frontend_node

    def _get_fallback_input(self, **kwargs):
        """Get fallback input for prompt fields."""
        try:
            return DefaultPromptField(**kwargs)
        except Exception as e:
            error_msg = i18n.t(
                'components.processing.prompt.errors.fallback_input_failed', error=str(e))
            self.log(error_msg, "error")
            # Return a basic fallback
            return DefaultPromptField()
