from typing import Any
import i18n
import pandas as pd
import re
import hashlib

from lfx.custom.custom_component.component import Component
from lfx.io import DataInput, TableInput, Output
from lfx.schema import Data


class ETLDataMaskingComponent(Component):
    display_name = i18n.t('components.security.data_masking.display_name')
    description = i18n.t('components.security.data_masking.description')
    icon = "eye-off"
    name = "ETLDataMasking"

    inputs = [
        DataInput(name="data_input", display_name=i18n.t('components.security.data_masking.data_input.display_name'), info=i18n.t('components.security.data_masking.data_input.info'), is_list=True, required=True),
        TableInput(name="masking_rules", display_name=i18n.t('components.security.data_masking.masking_rules.display_name'), info=i18n.t('components.security.data_masking.masking_rules.info'), table_schema=[{"name": "field", "display_name": "Field", "type": "str"}, {"name": "masking_type", "display_name": "Masking Type", "type": "str"}, {"name": "mask_char", "display_name": "Mask Character", "type": "str"}], value=[], required=True)
    ]

    outputs = [Output(name="data", display_name="Masked Data", method="mask_data")]

    def mask_data(self) -> list[Data]:
        try:
            if not self.data_input or not self.masking_rules:
                raise ValueError(i18n.t('components.security.data_masking.errors.missing_config'))
            df = pd.DataFrame([d.data if hasattr(d, 'data') else d for d in self.data_input])
            for rule in self.masking_rules:
                field = rule['field']
                masking_type = rule['masking_type'].lower()
                mask_char = rule.get('mask_char', '*')
                if field in df.columns:
                    if masking_type == 'phone':
                        df[field] = df[field].apply(lambda x: self._mask_phone(str(x), mask_char) if pd.notnull(x) else x)
                    elif masking_type == 'email':
                        df[field] = df[field].apply(lambda x: self._mask_email(str(x), mask_char) if pd.notnull(x) else x)
                    elif masking_type == 'id':
                        df[field] = df[field].apply(lambda x: self._mask_id(str(x), mask_char) if pd.notnull(x) else x)
                    elif masking_type == 'credit_card':
                        df[field] = df[field].apply(lambda x: self._mask_credit_card(str(x), mask_char) if pd.notnull(x) else x)
                    elif masking_type == 'full':
                        df[field] = df[field].apply(lambda x: mask_char * len(str(x)) if pd.notnull(x) else x)
                    elif masking_type == 'hash':
                        df[field] = df[field].apply(lambda x: hashlib.sha256(str(x).encode()).hexdigest() if pd.notnull(x) else x)
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t('components.security.data_masking.status.success', count=len(result))
            return result
        except Exception as e:
            error_msg = i18n.t('components.security.data_masking.errors.masking_failed', error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _mask_phone(self, phone: str, mask_char: str) -> str:
        if len(phone) > 4:
            return mask_char * (len(phone) - 4) + phone[-4:]
        return phone

    def _mask_email(self, email: str, mask_char: str) -> str:
        if '@' in email:
            local, domain = email.split('@', 1)
            if len(local) > 2:
                return local[0] + mask_char * (len(local) - 2) + local[-1] + '@' + domain
        return email

    def _mask_id(self, id_str: str, mask_char: str) -> str:
        if len(id_str) > 6:
            return id_str[:3] + mask_char * (len(id_str) - 6) + id_str[-3:]
        return id_str

    def _mask_credit_card(self, card: str, mask_char: str) -> str:
        card_digits = re.sub(r'\D', '', card)
        if len(card_digits) >= 4:
            return mask_char * (len(card_digits) - 4) + card_digits[-4:]
        return card
