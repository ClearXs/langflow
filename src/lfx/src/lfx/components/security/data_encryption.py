import base64

import i18n
import pandas as pd
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

from lfx.custom.custom_component.component import Component
from lfx.io import BoolInput, DataInput, DropdownInput, Output, SecretStrInput, TableInput
from lfx.schema import Data


class ETLDataEncryptionComponent(Component):
    display_name = i18n.t("components.security.data_encryption.display_name")
    description = i18n.t("components.security.data_encryption.description")
    icon = "lock"
    name = "ETLDataEncryption"

    inputs = [
        DataInput(
            name="data_input",
            display_name=i18n.t("components.security.data_encryption.data_input.display_name"),
            info=i18n.t("components.security.data_encryption.data_input.info"),
            is_list=True,
            required=True,
        ),
        DropdownInput(
            name="operation",
            display_name=i18n.t("components.security.data_encryption.operation.display_name"),
            info=i18n.t("components.security.data_encryption.operation.info"),
            options=["encrypt", "decrypt"],
            value="encrypt",
        ),
        SecretStrInput(
            name="encryption_key",
            display_name=i18n.t("components.security.data_encryption.encryption_key.display_name"),
            info=i18n.t("components.security.data_encryption.encryption_key.info"),
            required=True,
        ),
        TableInput(
            name="field_configs",
            display_name=i18n.t("components.security.data_encryption.field_configs.display_name"),
            info=i18n.t("components.security.data_encryption.field_configs.info"),
            table_schema=[{"name": "field", "display_name": "Field", "type": "str"}],
            value=[],
            required=True,
        ),
        BoolInput(
            name="use_base64",
            display_name=i18n.t("components.security.data_encryption.use_base64.display_name"),
            info=i18n.t("components.security.data_encryption.use_base64.info"),
            value=True,
            advanced=True,
        ),
    ]

    outputs = [Output(name="data", display_name="Processed Data", method="process_encryption")]

    def process_encryption(self) -> list[Data]:
        try:
            if not self.data_input or not self.field_configs or not self.encryption_key:
                raise ValueError(i18n.t("components.security.data_encryption.errors.missing_config"))
            df = pd.DataFrame([d.data if hasattr(d, "data") else d for d in self.data_input])
            cipher = self._get_cipher()
            for config in self.field_configs:
                field = config["field"]
                if field in df.columns:
                    if self.operation == "encrypt":
                        df[field] = df[field].apply(
                            lambda x: self._encrypt_value(str(x), cipher) if pd.notnull(x) else x
                        )
                    else:
                        df[field] = df[field].apply(
                            lambda x: self._decrypt_value(str(x), cipher) if pd.notnull(x) else x
                        )
            result = [Data(data=row.to_dict()) for _, row in df.iterrows()]
            self.status = i18n.t(
                "components.security.data_encryption.status.success", operation=self.operation, count=len(result)
            )
            return result
        except Exception as e:
            error_msg = i18n.t("components.security.data_encryption.errors.process_failed", error=str(e))
            self.status = error_msg
            raise ValueError(error_msg) from e

    def _get_cipher(self):
        key_bytes = self.encryption_key.encode()
        if len(key_bytes) != 32:
            from cryptography.hazmat.backends import default_backend

            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"langflow_etl_salt",
                iterations=100000,
                backend=default_backend(),
            )
            key_bytes = kdf.derive(key_bytes)
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(fernet_key)

    def _encrypt_value(self, value: str, cipher) -> str:
        encrypted = cipher.encrypt(value.encode())
        return base64.b64encode(encrypted).decode() if self.use_base64 else encrypted.decode()

    def _decrypt_value(self, value: str, cipher) -> str:
        encrypted_bytes = base64.b64decode(value) if self.use_base64 else value.encode()
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
