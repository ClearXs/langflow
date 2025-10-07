from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, Output
from lfx.log.logger import logger
from lfx.schema.message import Message


class CurrentDateComponent(Component):
    display_name = i18n.t('components.helpers.current_date.display_name')
    description = i18n.t('components.helpers.current_date.description')
    documentation: str = "https://docs.langflow.org/components-helpers#current-date"
    icon = "clock"
    name = "CurrentDate"

    inputs = [
        DropdownInput(
            name="timezone",
            display_name=i18n.t(
                'components.helpers.current_date.timezone.display_name'),
            options=list(available_timezones()),
            value="UTC",
            info=i18n.t('components.helpers.current_date.timezone.info'),
            tool_mode=True,
        ),
    ]
    outputs = [
        Output(
            display_name=i18n.t(
                'components.helpers.current_date.outputs.current_date.display_name'),
            name="current_date",
            method="get_current_date"
        ),
    ]

    def get_current_date(self) -> Message:
        try:
            if not self.timezone:
                error_message = i18n.t(
                    'components.helpers.current_date.errors.no_timezone')
                self.status = error_message
                return Message(text=error_message)

            tz = ZoneInfo(self.timezone)
            current_date = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S %Z")

            result = i18n.t('components.helpers.current_date.success.current_datetime',
                            timezone=self.timezone, datetime=current_date)
            self.status = result

            log_message = i18n.t('components.helpers.current_date.info.datetime_retrieved',
                                 timezone=self.timezone)
            logger.debug(log_message)

            return Message(text=result)

        except Exception as e:
            logger.debug("Error getting current date", exc_info=True)
            error_message = i18n.t('components.helpers.current_date.errors.retrieval_failed',
                                   timezone=self.timezone, error=str(e))
            self.status = error_message
            return Message(text=error_message)
