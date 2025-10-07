import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import json
from typing import Any, Dict, List, Optional
import i18n

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, DropdownInput, BoolInput, IntInput, MultilineInput, Output
from lfx.schema.data import Data


class URLComponent(Component):
    display_name = i18n.t('components.data.url.display_name')
    description = i18n.t('components.data.url.description')
    icon = "link"
    name = "URL"

    inputs = [
        MessageTextInput(
            name="urls",
            display_name=i18n.t('components.data.url.urls.display_name'),
            info=i18n.t('components.data.url.urls.info'),
            required=True,
            placeholder="https://example.com,https://example2.com",
        ),
        DropdownInput(
            name="method",
            display_name=i18n.t('components.data.url.method.display_name'),
            info=i18n.t('components.data.url.method.info'),
            options=["GET", "POST", "PUT", "DELETE", "PATCH"],
            value="GET",
        ),
        MultilineInput(
            name="headers",
            display_name=i18n.t('components.data.url.headers.display_name'),
            info=i18n.t('components.data.url.headers.info'),
            placeholder='{"User-Agent": "MyBot 1.0", "Accept": "text/html"}',
            advanced=True,
        ),
        MultilineInput(
            name="body",
            display_name=i18n.t('components.data.url.body.display_name'),
            info=i18n.t('components.data.url.body.info'),
            placeholder='{"key": "value"}',
            advanced=True,
        ),
        IntInput(
            name="timeout",
            display_name=i18n.t('components.data.url.timeout.display_name'),
            info=i18n.t('components.data.url.timeout.info'),
            value=30,
            range_spec=(1, 300),
            advanced=True,
        ),
        BoolInput(
            name="follow_redirects",
            display_name=i18n.t(
                'components.data.url.follow_redirects.display_name'),
            info=i18n.t('components.data.url.follow_redirects.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="verify_ssl",
            display_name=i18n.t('components.data.url.verify_ssl.display_name'),
            info=i18n.t('components.data.url.verify_ssl.info'),
            value=True,
            advanced=True,
        ),
        DropdownInput(
            name="content_type",
            display_name=i18n.t(
                'components.data.url.content_type.display_name'),
            info=i18n.t('components.data.url.content_type.info'),
            options=["auto", "text", "html", "json", "xml"],
            value="auto",
            advanced=True,
        ),
        BoolInput(
            name="extract_metadata",
            display_name=i18n.t(
                'components.data.url.extract_metadata.display_name'),
            info=i18n.t('components.data.url.extract_metadata.info'),
            value=True,
            advanced=True,
        ),
        BoolInput(
            name="extract_links",
            display_name=i18n.t(
                'components.data.url.extract_links.display_name'),
            info=i18n.t('components.data.url.extract_links.info'),
            value=False,
            advanced=True,
        ),
        IntInput(
            name="max_content_length",
            display_name=i18n.t(
                'components.data.url.max_content_length.display_name'),
            info=i18n.t('components.data.url.max_content_length.info'),
            value=1048576,  # 1MB
            range_spec=(1024, 10485760),  # 1KB to 10MB
            advanced=True,
        ),
        MessageTextInput(
            name="text_key",
            display_name=i18n.t('components.data.url.text_key.display_name'),
            info=i18n.t('components.data.url.text_key.info'),
            value="content",
            advanced=True,
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t(
                'components.data.url.outputs.data.display_name'),
            method="fetch_url_data"
        ),
        Output(
            name="response_info",
            display_name=i18n.t(
                'components.data.url.outputs.response_info.display_name'),
            method="get_response_info"
        ),
    ]

    def fetch_url_data(self) -> List[Data]:
        """Fetch data from URLs and return as Data objects."""
        try:
            if not self.urls.strip():
                error_message = i18n.t('components.data.url.errors.empty_urls')
                self.status = error_message
                raise ValueError(error_message)

            # Parse URLs
            url_list = [url.strip()
                        for url in self.urls.split(',') if url.strip()]

            if not url_list:
                error_message = i18n.t(
                    'components.data.url.errors.no_valid_urls')
                self.status = error_message
                raise ValueError(error_message)

            # Parse headers
            headers = self._parse_headers()

            # Parse body
            body = self._parse_body()

            results = []
            successful_requests = 0

            for url in url_list:
                try:
                    # Validate URL
                    parsed_url = urlparse(url)
                    if not parsed_url.scheme or not parsed_url.netloc:
                        warning_message = i18n.t(
                            'components.data.url.warnings.invalid_url', url=url)
                        self.status = warning_message
                        continue

                    # Make request
                    response = self._make_request(url, headers, body)

                    # Process response
                    data_dict = self._process_response(url, response)

                    results.append(
                        Data(data=data_dict, text_key=self.text_key))
                    successful_requests += 1

                except requests.RequestException as e:
                    warning_message = i18n.t('components.data.url.warnings.request_failed',
                                             url=url, error=str(e))
                    self.status = warning_message
                    # Continue with other URLs
                    continue

            if not results:
                error_message = i18n.t(
                    'components.data.url.errors.no_successful_requests')
                self.status = error_message
                return []

            success_message = i18n.t('components.data.url.success.fetched_data',
                                     successful=successful_requests, total=len(url_list))
            self.status = success_message
            return results

        except Exception as e:
            error_message = i18n.t(
                'components.data.url.errors.fetch_error', error=str(e))
            self.status = error_message
            raise ValueError(error_message) from e

    def get_response_info(self) -> List[Data]:
        """Get response information for URLs."""
        try:
            if not self.urls.strip():
                error_message = i18n.t('components.data.url.errors.empty_urls')
                raise ValueError(error_message)

            url_list = [url.strip()
                        for url in self.urls.split(',') if url.strip()]
            headers = self._parse_headers()
            body = self._parse_body()

            results = []

            for url in url_list:
                try:
                    response = self._make_request(url, headers, body)

                    info_dict = {
                        "url": url,
                        "status_code": response.status_code,
                        "status_text": response.reason,
                        "headers": dict(response.headers),
                        "content_type": response.headers.get('content-type', ''),
                        "content_length": len(response.content),
                        "encoding": response.encoding,
                        "elapsed_time": response.elapsed.total_seconds(),
                        "final_url": response.url,
                        "history": [r.url for r in response.history],
                    }

                    results.append(Data(data=info_dict, text_key="url"))

                except requests.RequestException as e:
                    error_dict = {
                        "url": url,
                        "error": str(e),
                        "status": "failed"
                    }
                    results.append(Data(data=error_dict, text_key="url"))

            return results

        except Exception as e:
            error_message = i18n.t(
                'components.data.url.errors.response_info_error', error=str(e))
            raise ValueError(error_message) from e

    def _parse_headers(self) -> Dict[str, str]:
        """Parse headers from JSON string."""
        if not self.headers.strip():
            return {}

        try:
            return json.loads(self.headers)
        except json.JSONDecodeError as e:
            warning_message = i18n.t(
                'components.data.url.warnings.invalid_headers', error=str(e))
            self.status = warning_message
            return {}

    def _parse_body(self) -> Optional[str]:
        """Parse body content."""
        if not self.body.strip():
            return None

        try:
            # Try to parse as JSON to validate
            json.loads(self.body)
            return self.body
        except json.JSONDecodeError:
            # Return as plain text if not JSON
            return self.body

    def _make_request(self, url: str, headers: Dict[str, str], body: Optional[str]) -> requests.Response:
        """Make HTTP request to URL."""
        request_kwargs = {
            'timeout': self.timeout,
            'allow_redirects': self.follow_redirects,
            'verify': self.verify_ssl,
            'headers': headers,
        }

        if body and self.method.upper() in ['POST', 'PUT', 'PATCH']:
            # Try to send as JSON if possible, otherwise as text
            try:
                json.loads(body)
                request_kwargs['json'] = json.loads(body)
            except json.JSONDecodeError:
                request_kwargs['data'] = body

        response = requests.request(self.method.upper(), url, **request_kwargs)

        # Check content length
        if len(response.content) > self.max_content_length:
            warning_message = i18n.t('components.data.url.warnings.content_too_large',
                                     size=len(response.content), max_size=self.max_content_length)
            self.status = warning_message

        response.raise_for_status()
        return response

    def _process_response(self, url: str, response: requests.Response) -> Dict[str, Any]:
        """Process HTTP response and extract data."""
        data_dict = {
            "url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get('content-type', ''),
            "content_length": len(response.content),
        }

        # Determine content type
        content_type = self.content_type
        if content_type == "auto":
            response_content_type = response.headers.get(
                'content-type', '').lower()
            if 'application/json' in response_content_type:
                content_type = "json"
            elif 'text/html' in response_content_type:
                content_type = "html"
            elif 'application/xml' in response_content_type or 'text/xml' in response_content_type:
                content_type = "xml"
            else:
                content_type = "text"

        # Process content based on type
        try:
            if content_type == "json":
                data_dict["content"] = response.json()
                data_dict["raw_content"] = response.text
            elif content_type == "html":
                soup = BeautifulSoup(response.text, 'html.parser')
                data_dict["content"] = soup.get_text(strip=True)
                data_dict["raw_content"] = response.text

                if self.extract_metadata:
                    data_dict["metadata"] = self._extract_html_metadata(soup)

                if self.extract_links:
                    data_dict["links"] = self._extract_links(soup, url)

            elif content_type == "xml":
                data_dict["content"] = response.text
                data_dict["raw_content"] = response.text
            else:  # text
                data_dict["content"] = response.text
                data_dict["raw_content"] = response.text

        except Exception as e:
            # Fallback to raw text if processing fails
            data_dict["content"] = response.text
            data_dict["raw_content"] = response.text
            data_dict["processing_error"] = str(e)

        return data_dict

    def _extract_html_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract metadata from HTML."""
        metadata = {}

        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)

        # Meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            name = tag.get('name') or tag.get(
                'property') or tag.get('http-equiv')
            content = tag.get('content')
            if name and content:
                metadata[name] = content

        return metadata

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from HTML."""
        links = []

        for link_tag in soup.find_all('a', href=True):
            href = link_tag['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            links.append(absolute_url)

        return list(set(links))  # Remove duplicates
