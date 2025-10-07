import requests
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import hashlib
import hmac
import base64
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, DropdownInput, BoolInput, IntInput, MultilineInput, Output
from lfx.schema.data import Data


class WebhookComponent(Component):
    display_name = i18n.t('components.data.webhook.display_name')
    description = i18n.t('components.data.webhook.description')
    icon = "webhook"
    name = "Webhook"

    inputs = [
        MessageTextInput(
            name="webhook_url",
            display_name=i18n.t(
                'components.data.webhook.webhook_url.display_name'),
            info=i18n.t('components.data.webhook.webhook_url.info'),
            required=True,
            placeholder="https://hooks.example.com/webhook",
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t('components.data.webhook.method.display_name'),
            info=i18n.t('components.data.webhook.method.info'),
            options=["POST", "PUT", "PATCH", "GET"],
            value="POST",
        ),
        MultilineInput(
            name="payload",
            display_name=i18n.t(
                'components.data.webhook.payload.display_name'),
            info=i18n.t('components.data.webhook.payload.info'),
            placeholder='{"message": "Hello from LangFlow", "timestamp": "{{timestamp}}"}',
        ),
        MultilineInput(
            name="headers",
            display_name=i18n.t(
                'components.data.webhook.headers.display_name'),
            info=i18n.t('components.data.webhook.headers.info'),
            placeholder='{"Content-Type": "application/json", "Authorization": "Bearer token"}',
            advanced=True,
        ),
        DropdownInput(
            name="content_type",
            display_name=i18n.t(
                'components.data.webhook.content_type.display_name'),
            info=i18n.t('components.data.webhook.content_type.info'),
            options=["application/json", "application/x-www-form-urlencoded",
                     "text/plain", "application/xml"],
            value="application/json",
            advanced=True,
        ),
        MessageTextInput(
            name="secret_key",
            display_name=i18n.t(
                'components.data.webhook.secret_key.display_name'),
            info=i18n.t('components.data.webhook.secret_key.info'),
            password=True,
            advanced=True,
        ),
        DropdownInput(
            name="signature_method",
            display_name=i18n.t(
                'components.data.webhook.signature_method.display_name'),
            info=i18n.t('components.data.webhook.signature_method.info'),
            options=["none", "sha1", "sha256", "md5"],
            value="none",
            advanced=True,
        ),
        MessageTextInput(
            name="signature_header",
            display_name=i18n.t(
                'components.data.webhook.signature_header.display_name'),
            info=i18n.t('components.data.webhook.signature_header.info'),
            value="X-Signature",
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t(
                'components.data.webhook.timeout.display_name'),
            info=i18n.t('components.data.webhook.timeout.info'),
            value=30,
            range_spec=(1, 300),
            advanced=True,
        ),
        IntInput(
            name="retry_count",
            display_name=i18n.t(
                'components.data.webhook.retry_count.display_name'),
            info=i18n.t('components.data.webhook.retry_count.info'),
            value=3,
            range_spec=(0, 10),
            advanced=True,
        ),
        BoolInput(
            name="verify_ssl",
            display_name=i18n.t(
                'components.data.webhook.verify_ssl.display_name'),
            info=i18n.t('components.data.webhook.verify_ssl.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="follow_redirects",
            display_name=i18n.t(
                'components.data.webhook.follow_redirects.display_name'),
            info=i18n.t('components.data.webhook.follow_redirects.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="include_request_info",
            display_name=i18n.t(
                'components.data.webhook.include_request_info.display_name'),
            info=i18n.t('components.data.webhook.include_request_info.info'),
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t(
                'components.data.webhook.text_key.display_name'),
            info=i18n.t('components.data.webhook.text_key.info'),
            value="response",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="response",
            display_name=i18n.t(
                'components.data.webhook.outputs.response.display_name'),
            method="send_webhook"
        ),
        Output(
            name="request_info",
            display_name=i18n.t(
                'components.data.webhook.outputs.request_info.display_name'),
            method="get_request_info"
        ),
    ]

    def send_webhook(self) -> List[Data]:
        """Send webhook request and return response data."""
        try:
            if not self.webhook_url.strip():
                error_message = i18n.t(
                    'components.data.webhook.errors.empty_url')
                self.status = error_message
                raise ValueError(error_message)

            # Prepare payload
            prepared_payload = self._prepare_payload()

            # Prepare headers
            headers = self._prepare_headers(prepared_payload)

            # Send webhook with retries
            response = self._send_with_retries(prepared_payload, headers)

            # Process response
            response_data = self._process_response(response)

            success_message = i18n.t('components.data.webhook.success.webhook_sent',
                                     status_code=response.status_code, url=self.webhook_url)
            self.status = success_message

            return [Data(data=response_data, text_key=self.text_key)]

        except Exception as e:
            error_message = i18n.t(
                'components.data.webhook.errors.webhook_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_request_info(self) -> Data:
        """Get information about the webhook request."""
        try:
            prepared_payload = self._prepare_payload()
            headers = self._prepare_headers(prepared_payload)

            request_info = {
                "webhook_url": self.webhook_url,
                "method": self.method,
                "payload": prepared_payload,
                "headers": {k: v for k, v in headers.items() if k.lower() not in ['authorization', 'x-signature']},
                "content_type": self.content_type,
                "timeout": self.timeout,
                "retry_count": self.retry_count,
                "verify_ssl": self.verify_ssl,
                "follow_redirects": self.follow_redirects,
                "timestamp": datetime.now().isoformat(),
            }

            # Add signature info if used
            if self.signature_method != "none" and self.secret_key:
                request_info["signature_method"] = self.signature_method
                request_info["signature_header"] = self.signature_header
                request_info["has_signature"] = True
            else:
                request_info["has_signature"] = False

            return Data(data=request_info, text_key="webhook_url")

        except Exception as e:
            error_message = i18n.t(
                'components.data.webhook.errors.request_info_error', error=str(e))
            raise ValueError(error_message) from e

    def _prepare_payload(self) -> str:
        """Prepare and process the webhook payload."""
        if not self.payload.strip():
            return ""

        # Replace placeholders
        payload_str = self.payload

        # Common placeholder replacements
        replacements = {
            "{{timestamp}}": datetime.now().isoformat(),
            "{{unix_timestamp}}": str(int(datetime.now().timestamp())),
            "{{date}}": datetime.now().strftime("%Y-%m-%d"),
            "{{time}}": datetime.now().strftime("%H:%M:%S"),
        }

        for placeholder, value in replacements.items():
            payload_str = payload_str.replace(placeholder, value)

        # Validate JSON if content type is JSON
        if self.content_type == "application/json":
            try:
                json.loads(payload_str)
            except json.JSONDecodeError as e:
                error_message = i18n.t(
                    'components.data.webhook.errors.invalid_json_payload', error=str(e))
                raise ValueError(error_message) from e

        return payload_str

    def _prepare_headers(self, payload: str) -> Dict[str, str]:
        """Prepare request headers including signature if needed."""
        headers = {"Content-Type": self.content_type}

        # Add custom headers
        if self.headers.strip():
            try:
                custom_headers = json.loads(self.headers)
                headers.update(custom_headers)
            except json.JSONDecodeError as e:
                warning_message = i18n.t(
                    'components.data.webhook.warnings.invalid_headers', error=str(e))
                self.status = warning_message

        # Add signature header if needed
        if self.signature_method != "none" and self.secret_key and payload:
            signature = self._generate_signature(payload)
            headers[self.signature_header] = signature

        return headers

    def _generate_signature(self, payload: str) -> str:
        """Generate signature for the payload."""
        if not self.secret_key:
            return ""

        payload_bytes = payload.encode('utf-8')
        secret_bytes = self.secret_key.encode('utf-8')

        if self.signature_method == "sha1":
            signature = hmac.new(secret_bytes, payload_bytes,
                                 hashlib.sha1).hexdigest()
            return f"sha1={signature}"
        elif self.signature_method == "sha256":
            signature = hmac.new(secret_bytes, payload_bytes,
                                 hashlib.sha256).hexdigest()
            return f"sha256={signature}"
        elif self.signature_method == "md5":
            signature = hmac.new(
                secret_bytes, payload_bytes, hashlib.md5).hexdigest()
            return f"md5={signature}"

        return ""

    def _send_with_retries(self, payload: str, headers: Dict[str, str]) -> requests.Response:
        """Send webhook request with retry logic."""
        last_exception = None

        for attempt in range(max(1, self.retry_count + 1)):
            try:
                request_kwargs = {
                    'timeout': self.timeout,
                    'verify': self.verify_ssl,
                    'allow_redirects': self.follow_redirects,
                    'headers': headers,
                }

                # Add payload based on method
                if self.method.upper() in ['POST', 'PUT', 'PATCH']:
                    if self.content_type == "application/json":
                        request_kwargs['data'] = payload
                    elif self.content_type == "application/x-www-form-urlencoded":
                        # Convert JSON payload to form data if needed
                        try:
                            json_data = json.loads(payload)
                            request_kwargs['data'] = json_data
                        except (json.JSONDecodeError, TypeError):
                            request_kwargs['data'] = payload
                    else:
                        request_kwargs['data'] = payload

                response = requests.request(
                    self.method.upper(), self.webhook_url, **request_kwargs)
                response.raise_for_status()
                return response

            except requests.RequestException as e:
                last_exception = e
                if attempt < self.retry_count:
                    warning_message = i18n.t('components.data.webhook.warnings.retry_attempt',
                                             attempt=attempt + 1, total=self.retry_count + 1, error=str(e))
                    self.status = warning_message
                    continue
                else:
                    break

        # If we get here, all retries failed
        if last_exception:
            raise last_exception
        else:
            error_message = i18n.t(
                'components.data.webhook.errors.max_retries_exceeded')
            raise ValueError(error_message)

    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """Process webhook response and extract data."""
        response_data = {
            "status_code": response.status_code,
            "status_text": response.reason,
            "headers": dict(response.headers),
            "url": response.url,
            "elapsed_time": response.elapsed.total_seconds(),
            "timestamp": datetime.now().isoformat(),
        }

        # Try to parse response content
        try:
            # Try JSON first
            response_data["response"] = response.json()
            response_data["content_type"] = "json"
        except (json.JSONDecodeError, ValueError):
            # Fallback to text
            response_data["response"] = response.text
            response_data["content_type"] = "text"

        # Add request info if requested
        if self.include_request_info:
            response_data["request"] = {
                "method": self.method,
                "url": self.webhook_url,
                "headers": {k: v for k, v in response.request.headers.items()
                            if k.lower() not in ['authorization', 'x-signature']},
            }

        return response_data
