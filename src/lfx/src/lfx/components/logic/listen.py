import i18n
from lfx.custom import Component
from lfx.io import Output, StrInput
from lfx.log.logger import logger
from lfx.schema.data import Data


class ListenComponent(Component):
    display_name = i18n.t('components.logic.listen.display_name')
    description = i18n.t('components.logic.listen.description')
    name = "Listen"
    beta: bool = True
    icon = "Radio"

    inputs = [
        StrInput(
            name="context_key",
            display_name=i18n.t(
                'components.logic.listen.context_key.display_name'),
            info=i18n.t('components.logic.listen.context_key.info'),
            input_types=["Message"],
            required=True,
        )
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t(
                'components.logic.listen.outputs.data.display_name'),
            method="listen_for_data",
            cache=False
        )
    ]

    def listen_for_data(self) -> Data:
        """Retrieves a Data object from the component context using the provided context key.

        If the specified context key does not exist in the context, returns an empty Data object.
        """
        try:
            logger.debug(i18n.t('components.logic.listen.logs.listening',
                                key=self.context_key))

            if self.context_key in self.ctx:
                data = self.ctx.get(self.context_key)

                # Ensure we return a Data object
                if not isinstance(data, Data):
                    logger.debug(i18n.t('components.logic.listen.logs.converting_to_data',
                                        data_type=type(data).__name__))
                    data = Data(text=str(data))

                success_msg = i18n.t('components.logic.listen.status.data_retrieved',
                                     key=self.context_key)
                self.status = success_msg
                logger.info(i18n.t('components.logic.listen.logs.data_retrieved',
                                   key=self.context_key))
                return data

            warning_msg = i18n.t('components.logic.listen.warnings.key_not_found',
                                 key=self.context_key)
            self.status = warning_msg
            logger.warning(warning_msg)
            return Data(text="")

        except Exception as e:
            error_msg = i18n.t('components.logic.listen.errors.retrieval_failed',
                               key=self.context_key,
                               error=str(e))
            self.status = error_msg
            logger.exception(error_msg)
            return Data(text="")
