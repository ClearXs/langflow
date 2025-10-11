import os
import urllib.request
from urllib.parse import urlparse
from xml.etree.ElementTree import Element

import i18n
from defusedxml.ElementTree import fromstring

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, IntInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class ArXivComponent(Component):
    display_name = i18n.t('components.arxiv.arxiv.display_name')
    description = i18n.t('components.arxiv.arxiv.description')
    icon = "arXiv"
    name = "ArXiv"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        MessageTextInput(
            name="search_query",
            display_name=i18n.t(
                'components.arxiv.arxiv.search_query.display_name'),
            info=i18n.t('components.arxiv.arxiv.search_query.info'),
            tool_mode=True,
        ),
        DropdownInput(
            name="search_type",
            display_name=i18n.t(
                'components.arxiv.arxiv.search_type.display_name'),
            info=i18n.t('components.arxiv.arxiv.search_type.info'),
            options=["all", "title", "abstract", "author", "cat"],
            value="all",
        ),
        IntInput(
            name="max_results",
            display_name=i18n.t(
                'components.arxiv.arxiv.max_results.display_name'),
            info=i18n.t('components.arxiv.arxiv.max_results.info'),
            value=10,
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.arxiv.arxiv.outputs.dataframe.display_name'),
            name="dataframe",
            method="search_papers_dataframe"
        ),
    ]

    def build_query_url(self) -> str:
        """Build the arXiv API query URL."""
        try:
            base_url = "http://export.arxiv.org/api/query?"

            # Build the search query
            search_query = f"{self.search_type}:{self.search_query}"

            logger.debug(i18n.t('components.arxiv.arxiv.logs.building_query',
                                type=self.search_type, query=self.search_query))

            # URL parameters
            params = {
                "search_query": search_query,
                "max_results": str(self.max_results),
            }

            # Convert params to URL query string
            query_string = "&".join(
                [f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items()])

            url = base_url + query_string
            logger.debug(
                i18n.t('components.arxiv.arxiv.logs.query_url_built', url=url))

            return url

        except Exception as e:
            error_msg = i18n.t(
                'components.arxiv.arxiv.errors.query_build_failed', error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def parse_atom_response(self, response_text: str) -> list[dict]:
        """Parse the Atom XML response from arXiv."""
        try:
            self.status = i18n.t(
                'components.arxiv.arxiv.status.parsing_response')

            # Parse XML safely using defusedxml
            root = fromstring(response_text)

            # Define namespace dictionary for XML parsing
            ns = {"atom": "http://www.w3.org/2005/Atom",
                  "arxiv": "http://arxiv.org/schemas/atom"}

            papers = []
            # Process each entry (paper)
            for entry in root.findall("atom:entry", ns):
                paper = {
                    "id": self._get_text(entry, "atom:id", ns),
                    "title": self._get_text(entry, "atom:title", ns),
                    "summary": self._get_text(entry, "atom:summary", ns),
                    "published": self._get_text(entry, "atom:published", ns),
                    "updated": self._get_text(entry, "atom:updated", ns),
                    "authors": [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)],
                    "arxiv_url": self._get_link(entry, "alternate", ns),
                    "pdf_url": self._get_link(entry, "related", ns),
                    "comment": self._get_text(entry, "arxiv:comment", ns),
                    "journal_ref": self._get_text(entry, "arxiv:journal_ref", ns),
                    "primary_category": self._get_category(entry, ns),
                    "categories": [cat.get("term") for cat in entry.findall("atom:category", ns)],
                }
                papers.append(paper)

            logger.info(
                i18n.t('components.arxiv.arxiv.logs.papers_parsed', count=len(papers)))
            return papers

        except Exception as e:
            error_msg = i18n.t(
                'components.arxiv.arxiv.errors.response_parse_failed', error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    def _get_text(self, element: Element, path: str, ns: dict) -> str | None:
        """Safely extract text from an XML element."""
        el = element.find(path, ns)
        return el.text.strip() if el is not None and el.text else None

    def _get_link(self, element: Element, rel: str, ns: dict) -> str | None:
        """Get link URL based on relation type."""
        for link in element.findall("atom:link", ns):
            if link.get("rel") == rel:
                return link.get("href")
        return None

    def _get_category(self, element: Element, ns: dict) -> str | None:
        """Get primary category."""
        cat = element.find("arxiv:primary_category", ns)
        return cat.get("term") if cat is not None else None

    def run_model(self) -> DataFrame:
        return self.search_papers_dataframe()

    def search_papers(self) -> list[Data]:
        """Search arXiv and return results."""
        try:
            self.status = i18n.t(
                'components.arxiv.arxiv.status.searching', query=self.search_query)

            # Build the query URL
            url = self.build_query_url()

            # Validate URL scheme and host
            parsed_url = urlparse(url)
            if parsed_url.scheme not in {"http", "https"}:
                error_msg = i18n.t('components.arxiv.arxiv.errors.invalid_url_scheme',
                                   scheme=parsed_url.scheme)
                raise ValueError(error_msg)
            if parsed_url.hostname != "export.arxiv.org":
                error_msg = i18n.t('components.arxiv.arxiv.errors.invalid_host',
                                   host=parsed_url.hostname)
                raise ValueError(error_msg)

            logger.debug(i18n.t('components.arxiv.arxiv.logs.url_validated'))

            # Create a custom opener that only allows http/https schemes
            class RestrictedHTTPHandler(urllib.request.HTTPHandler):
                def http_open(self, req):
                    return super().http_open(req)

            class RestrictedHTTPSHandler(urllib.request.HTTPSHandler):
                def https_open(self, req):
                    return super().https_open(req)

            # Build opener with restricted handlers
            opener = urllib.request.build_opener(
                RestrictedHTTPHandler, RestrictedHTTPSHandler)
            urllib.request.install_opener(opener)

            self.status = i18n.t(
                'components.arxiv.arxiv.status.fetching_results')

            # Make the request with validated URL using restricted opener
            try:
                response = opener.open(url)
                response_text = response.read().decode("utf-8")
                logger.debug(
                    i18n.t('components.arxiv.arxiv.logs.response_received'))
            except urllib.error.URLError as e:
                error_msg = i18n.t(
                    'components.arxiv.arxiv.errors.request_failed', error=str(e))
                logger.error(error_msg)
                raise

            # Parse the response
            papers = self.parse_atom_response(response_text)

            # Convert to Data objects
            results = [Data(data=paper) for paper in papers]

            success_msg = i18n.t(
                'components.arxiv.arxiv.success.papers_found', count=len(results))
            logger.info(success_msg)
            self.status = success_msg

            return results

        except urllib.error.URLError as e:
            error_msg = i18n.t(
                'components.arxiv.arxiv.errors.request_error', error=str(e))
            logger.error(error_msg)
            error_data = Data(data={"error": error_msg})
            self.status = error_data
            return [error_data]
        except ValueError as e:
            logger.error(str(e))
            error_data = Data(data={"error": str(e)})
            self.status = error_data
            return [error_data]
        except Exception as e:
            error_msg = i18n.t(
                'components.arxiv.arxiv.errors.search_failed', error=str(e))
            logger.exception(error_msg)
            error_data = Data(data={"error": error_msg})
            self.status = error_data
            return [error_data]

    def search_papers_dataframe(self) -> DataFrame:
        """Convert the Arxiv search results to a DataFrame.

        Returns:
            DataFrame: A DataFrame containing the search results.
        """
        try:
            self.status = i18n.t(
                'components.arxiv.arxiv.status.converting_to_dataframe')
            data = self.search_papers()
            df = DataFrame(data)

            logger.info(
                i18n.t('components.arxiv.arxiv.logs.dataframe_created', rows=len(data)))
            return df

        except Exception as e:
            error_msg = i18n.t('components.arxiv.arxiv.errors.dataframe_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
