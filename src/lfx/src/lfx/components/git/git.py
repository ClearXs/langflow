import os
import i18n
import re
import tempfile
from contextlib import asynccontextmanager
from fnmatch import fnmatch
from pathlib import Path

import anyio
from langchain_community.document_loaders.git import GitLoader

from lfx.custom.custom_component.component import Component
from lfx.io import DropdownInput, MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data


class GitLoaderComponent(Component):
    display_name = "Git"
    description = i18n.t('components.git.git.description')
    trace_type = "tool"
    icon = "GitLoader"

    ignore: bool = os.getenv("LANGFLOW_IGNORE_COMPONENT", "false") == "true"

    inputs = [
        DropdownInput(
            name="repo_source",
            display_name=i18n.t('components.git.git.repo_source.display_name'),
            options=[
                i18n.t('components.git.git.repo_source.options.local'),
                i18n.t('components.git.git.repo_source.options.remote')
            ],
            required=True,
            info=i18n.t('components.git.git.repo_source.info'),
            real_time_refresh=True,
        ),
        MessageTextInput(
            name="repo_path",
            display_name=i18n.t('components.git.git.repo_path.display_name'),
            required=False,
            info=i18n.t('components.git.git.repo_path.info'),
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="clone_url",
            display_name=i18n.t('components.git.git.clone_url.display_name'),
            required=False,
            info=i18n.t('components.git.git.clone_url.info'),
            dynamic=True,
            show=False,
        ),
        MessageTextInput(
            name="branch",
            display_name=i18n.t('components.git.git.branch.display_name'),
            required=False,
            value="main",
            info=i18n.t('components.git.git.branch.info'),
        ),
        MessageTextInput(
            name="file_filter",
            display_name=i18n.t('components.git.git.file_filter.display_name'),
            required=False,
            advanced=True,
            info=i18n.t('components.git.git.file_filter.info'),
        ),
        MessageTextInput(
            name="content_filter",
            display_name=i18n.t(
                'components.git.git.content_filter.display_name'),
            required=False,
            advanced=True,
            info=i18n.t('components.git.git.content_filter.info'),
        ),
    ]

    outputs = [
        Output(
            name="data",
            display_name=i18n.t(
                'components.git.git.outputs.data.display_name'),
            method="load_documents"
        ),
    ]

    @staticmethod
    def is_binary(file_path: str | Path) -> bool:
        """Check if a file is binary by looking for null bytes."""
        try:
            with Path(file_path).open("rb") as file:
                content = file.read(1024)
                is_bin = b"\x00" in content
                if is_bin:
                    logger.debug(i18n.t('components.git.git.logs.binary_file_detected',
                                        path=str(file_path)))
                return is_bin
        except Exception as e:
            logger.debug(i18n.t('components.git.git.logs.binary_check_failed',
                                path=str(file_path),
                                error=str(e)))
            return True

    @staticmethod
    def check_file_patterns(file_path: str | Path, patterns: str) -> bool:
        """Check if a file matches the given patterns.

        Args:
            file_path: Path to the file to check
            patterns: Comma-separated list of glob patterns

        Returns:
            bool: True if file should be included, False if excluded
        """
        # Handle empty or whitespace-only patterns
        if not patterns or patterns.isspace():
            return True

        path_str = str(file_path)
        file_name = Path(path_str).name
        pattern_list: list[str] = [pattern.strip()
                                   for pattern in patterns.split(",") if pattern.strip()]

        # If no valid patterns after stripping, treat as include all
        if not pattern_list:
            return True

        # Process exclusion patterns first
        for pattern in pattern_list:
            if pattern.startswith("!"):
                # For exclusions, match against both full path and filename
                exclude_pattern = pattern[1:]
                if fnmatch(path_str, exclude_pattern) or fnmatch(file_name, exclude_pattern):
                    logger.debug(i18n.t('components.git.git.logs.file_excluded',
                                        path=path_str,
                                        pattern=exclude_pattern))
                    return False

        # Then check inclusion patterns
        include_patterns = [p for p in pattern_list if not p.startswith("!")]
        # If no include patterns, treat as include all
        if not include_patterns:
            return True

        # For inclusions, match against both full path and filename
        matched = any(fnmatch(path_str, pattern) or fnmatch(
            file_name, pattern) for pattern in include_patterns)
        if matched:
            logger.debug(i18n.t('components.git.git.logs.file_included',
                                path=path_str))
        return matched

    @staticmethod
    def check_content_pattern(file_path: str | Path, pattern: str) -> bool:
        """Check if file content matches the given regex pattern.

        Args:
            file_path: Path to the file to check
            pattern: Regex pattern to match against content

        Returns:
            bool: True if content matches, False otherwise
        """
        try:
            # Check if file is binary
            with Path(file_path).open("rb") as file:
                content = file.read(1024)
                if b"\x00" in content:
                    logger.debug(i18n.t('components.git.git.logs.content_check_skipped_binary',
                                        path=str(file_path)))
                    return False

            # Try to compile the regex pattern first
            try:
                # Use the MULTILINE flag to better handle text content
                content_regex = re.compile(pattern, re.MULTILINE)
                # Test the pattern with a simple string to catch syntax errors
                test_str = "test\nstring"
                if not content_regex.search(test_str):
                    # Pattern is valid but doesn't match test string
                    pass
            except (re.error, TypeError, ValueError) as e:
                logger.warning(i18n.t('components.git.git.logs.invalid_regex',
                                      pattern=pattern,
                                      error=str(e)))
                return False

            # If not binary and regex is valid, check content
            with Path(file_path).open(encoding="utf-8") as file:
                file_content = file.read()
            matched = bool(content_regex.search(file_content))
            if matched:
                logger.debug(i18n.t('components.git.git.logs.content_matched',
                                    path=str(file_path)))
            return matched
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(i18n.t('components.git.git.logs.content_check_failed',
                                path=str(file_path),
                                error=str(e)))
            return False

    def build_combined_filter(self, file_filter_patterns: str | None = None, content_filter_pattern: str | None = None):
        """Build a combined filter function from file and content patterns.

        Args:
            file_filter_patterns: Comma-separated glob patterns
            content_filter_pattern: Regex pattern for content

        Returns:
            callable: Filter function that takes a file path and returns bool
        """
        logger.debug(i18n.t('components.git.git.logs.building_filter',
                            file_patterns=file_filter_patterns or "None",
                            content_pattern=content_filter_pattern or "None"))

        def combined_filter(file_path: str) -> bool:
            try:
                path = Path(file_path)

                # Check if file exists and is readable
                if not path.exists():
                    logger.debug(i18n.t('components.git.git.logs.file_not_exists',
                                        path=str(path)))
                    return False

                # Check if file is binary
                if self.is_binary(path):
                    return False

                # Apply file pattern filters
                if file_filter_patterns and not self.check_file_patterns(path, file_filter_patterns):
                    return False

                # Apply content filter
                return not (content_filter_pattern and not self.check_content_pattern(path, content_filter_pattern))
            except Exception as e:
                logger.debug(i18n.t('components.git.git.logs.filter_error',
                                    path=file_path,
                                    error=str(e)))
                return False

        return combined_filter

    @asynccontextmanager
    async def temp_clone_dir(self):
        """Context manager for handling temporary clone directory."""
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(prefix="langflow_clone_")
            logger.debug(i18n.t('components.git.git.logs.temp_dir_created',
                                path=temp_dir))
            yield temp_dir
        finally:
            if temp_dir:
                try:
                    await anyio.Path(temp_dir).rmdir()
                    logger.debug(i18n.t('components.git.git.logs.temp_dir_removed',
                                        path=temp_dir))
                except Exception as e:
                    logger.warning(i18n.t('components.git.git.logs.temp_dir_remove_failed',
                                          path=temp_dir,
                                          error=str(e)))

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None) -> dict:
        """Update build configuration based on field changes."""
        # Hide fields by default
        build_config["repo_path"]["show"] = False
        build_config["clone_url"]["show"] = False

        local_label = i18n.t('components.git.git.repo_source.options.local')
        remote_label = i18n.t('components.git.git.repo_source.options.remote')

        if field_name == "repo_source":
            if field_value == local_label:
                build_config["repo_path"]["show"] = True
                build_config["repo_path"]["required"] = True
                build_config["clone_url"]["required"] = False
                logger.debug(
                    i18n.t('components.git.git.logs.config_updated_local'))
            elif field_value == remote_label:
                build_config["clone_url"]["show"] = True
                build_config["clone_url"]["required"] = True
                build_config["repo_path"]["required"] = False
                logger.debug(
                    i18n.t('components.git.git.logs.config_updated_remote'))

        return build_config

    async def build_gitloader(self) -> GitLoader:
        """Build GitLoader with configured parameters."""
        logger.info(i18n.t('components.git.git.logs.building_gitloader'))

        file_filter_patterns = getattr(self, "file_filter", None)
        content_filter_pattern = getattr(self, "content_filter", None)

        combined_filter = self.build_combined_filter(
            file_filter_patterns, content_filter_pattern)

        local_label = i18n.t('components.git.git.repo_source.options.local')
        remote_label = i18n.t('components.git.git.repo_source.options.remote')

        repo_source = getattr(self, "repo_source", None)

        if repo_source == local_label:
            repo_path = self.repo_path
            clone_url = None
            logger.info(i18n.t('components.git.git.logs.using_local_repo',
                               path=repo_path))
        else:
            # Clone source
            clone_url = self.clone_url
            logger.info(i18n.t('components.git.git.logs.using_remote_repo',
                               url=clone_url))
            async with self.temp_clone_dir() as temp_dir:
                repo_path = temp_dir

        # Only pass branch if it's explicitly set
        branch = getattr(self, "branch", None)
        if not branch:
            branch = None
        else:
            logger.debug(i18n.t('components.git.git.logs.using_branch',
                                branch=branch))

        try:
            gitloader = GitLoader(
                repo_path=repo_path,
                clone_url=clone_url if repo_source == remote_label else None,
                branch=branch,
                file_filter=combined_filter,
            )
            logger.info(i18n.t('components.git.git.logs.gitloader_created'))
            return gitloader
        except Exception as e:
            error_msg = i18n.t('components.git.git.errors.gitloader_creation_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e

    async def load_documents(self) -> list[Data]:
        """Load documents from Git repository.

        Returns:
            list[Data]: List of loaded documents.

        Raises:
            ValueError: If loading fails.
        """
        try:
            logger.info(i18n.t('components.git.git.logs.loading_documents'))

            gitloader = await self.build_gitloader()
            data = [Data.from_document(doc) async for doc in gitloader.alazy_load()]

            logger.info(i18n.t('components.git.git.logs.documents_loaded',
                               count=len(data)))

            self.status = data
            return data

        except Exception as e:
            error_msg = i18n.t('components.git.git.errors.loading_failed',
                               error=str(e))
            logger.exception(error_msg)
            raise ValueError(error_msg) from e
