import i18n
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import git

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.log.logger import logger
from lfx.schema.data import Data
from lfx.schema.message import Message


class GitExtractorComponent(Component):
    display_name = "GitExtractor"
    description = i18n.t('components.git.gitextractor.description')
    icon = "GitLoader"

    inputs = [
        MessageTextInput(
            name="repository_url",
            display_name=i18n.t(
                'components.git.gitextractor.repository_url.display_name'),
            info=i18n.t('components.git.gitextractor.repository_url.info'),
            value="",
        ),
    ]

    outputs = [
        Output(
            display_name=i18n.t(
                'components.git.gitextractor.outputs.text_based_file_contents.display_name'),
            name="text_based_file_contents",
            method="get_text_based_file_contents",
        ),
        Output(
            display_name=i18n.t(
                'components.git.gitextractor.outputs.directory_structure.display_name'),
            name="directory_structure",
            method="get_directory_structure"
        ),
        Output(
            display_name=i18n.t(
                'components.git.gitextractor.outputs.repository_info.display_name'),
            name="repository_info",
            method="get_repository_info"
        ),
        Output(
            display_name=i18n.t(
                'components.git.gitextractor.outputs.statistics.display_name'),
            name="statistics",
            method="get_statistics"
        ),
        Output(
            display_name=i18n.t(
                'components.git.gitextractor.outputs.files_content.display_name'),
            name="files_content",
            method="get_files_content"
        ),
    ]

    @asynccontextmanager
    async def temp_git_repo(self):
        """Async context manager for temporary git repository cloning."""
        temp_dir = tempfile.mkdtemp()
        logger.debug(i18n.t('components.git.gitextractor.logs.temp_dir_created',
                            path=temp_dir))
        try:
            logger.info(i18n.t('components.git.gitextractor.logs.cloning_repository',
                               url=self.repository_url))
            # Clone is still sync but wrapped in try/finally
            git.Repo.clone_from(self.repository_url, temp_dir)
            logger.info(i18n.t('components.git.gitextractor.logs.repository_cloned',
                               path=temp_dir))
            yield temp_dir
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.debug(i18n.t('components.git.gitextractor.logs.temp_dir_removed',
                                path=temp_dir))

    async def get_repository_info(self) -> list[Data]:
        """Get comprehensive repository information.

        Returns:
            list[Data]: Repository information including branches, commits, and remotes.
        """
        try:
            logger.info(
                i18n.t('components.git.gitextractor.logs.getting_repo_info'))

            async with self.temp_git_repo() as temp_dir:
                repo = git.Repo(temp_dir)

                repo_info = {
                    "name": self.repository_url.split("/")[-1],
                    "url": self.repository_url,
                    "default_branch": repo.active_branch.name,
                    "remote_urls": [remote.url for remote in repo.remotes],
                    "last_commit": {
                        "hash": repo.head.commit.hexsha,
                        "author": str(repo.head.commit.author),
                        "message": repo.head.commit.message.strip(),
                        "date": str(repo.head.commit.committed_datetime),
                    },
                    "branches": [str(branch) for branch in repo.branches],
                }

                logger.info(i18n.t('components.git.gitextractor.logs.repo_info_retrieved',
                                   name=repo_info["name"],
                                   branch=repo_info["default_branch"],
                                   branch_count=len(repo_info["branches"])))

                result = [Data(data=repo_info)]
                self.status = result
                return result

        except git.GitError as e:
            error_msg = i18n.t('components.git.gitextractor.errors.repo_info_failed',
                               error=str(e))
            logger.error(error_msg)
            error_result = [Data(data={"error": error_msg})]
            self.status = error_result
            return error_result

    async def get_statistics(self) -> list[Data]:
        """Calculate repository statistics.

        Returns:
            list[Data]: Statistics including file counts, sizes, and lines of code.
        """
        try:
            logger.info(
                i18n.t('components.git.gitextractor.logs.calculating_statistics'))

            async with self.temp_git_repo() as temp_dir:
                total_files = 0
                total_size = 0
                total_lines = 0
                binary_files = 0
                directories = 0

                for root, dirs, files in os.walk(temp_dir):
                    total_files += len(files)
                    directories += len(dirs)

                    for file in files:
                        file_path = Path(root) / file
                        total_size += file_path.stat().st_size

                        try:
                            async with aiofiles.open(file_path, encoding="utf-8") as f:
                                total_lines += sum(1 for _ in await f.readlines())
                        except UnicodeDecodeError:
                            binary_files += 1
                            logger.debug(i18n.t('components.git.gitextractor.logs.binary_file_detected',
                                                path=str(file_path.relative_to(temp_dir))))

                statistics = {
                    "total_files": total_files,
                    "total_size_bytes": total_size,
                    "total_size_kb": round(total_size / 1024, 2),
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "total_lines": total_lines,
                    "binary_files": binary_files,
                    "directories": directories,
                }

                logger.info(i18n.t('components.git.gitextractor.logs.statistics_calculated',
                                   files=total_files,
                                   size_mb=statistics["total_size_mb"],
                                   lines=total_lines,
                                   binary=binary_files))

                result = [Data(data=statistics)]
                self.status = result
                return result

        except git.GitError as e:
            error_msg = i18n.t('components.git.gitextractor.errors.statistics_failed',
                               error=str(e))
            logger.error(error_msg)
            error_result = [Data(data={"error": error_msg})]
            self.status = error_result
            return error_result

    async def get_directory_structure(self) -> Message:
        """Generate a tree view of the repository directory structure.

        Returns:
            Message: Directory structure as a tree diagram.
        """
        try:
            logger.info(
                i18n.t('components.git.gitextractor.logs.generating_directory_structure'))

            async with self.temp_git_repo() as temp_dir:
                tree = [
                    i18n.t('components.git.gitextractor.logs.directory_structure_header')]

                for root, _dirs, files in os.walk(temp_dir):
                    level = root.replace(temp_dir, "").count(os.sep)
                    indent = "    " * level

                    if level == 0:
                        tree.append(f"└── {Path(root).name}")
                    else:
                        tree.append(f"{indent}├── {Path(root).name}")

                    subindent = "    " * (level + 1)
                    tree.extend(f"{subindent}├── {f}" for f in files)

                directory_structure = "\n".join(tree)

                logger.info(i18n.t('components.git.gitextractor.logs.directory_structure_generated',
                                   lines=len(tree)))

                self.status = directory_structure
                return Message(text=directory_structure)

        except git.GitError as e:
            error_message = i18n.t('components.git.gitextractor.errors.directory_structure_failed',
                                   error=str(e))
            logger.error(error_message)
            self.status = error_message
            return Message(text=error_message)

    async def get_files_content(self) -> list[Data]:
        """Extract content from all files in the repository.

        Returns:
            list[Data]: List of file contents with metadata.
        """
        try:
            logger.info(
                i18n.t('components.git.gitextractor.logs.extracting_files_content'))

            async with self.temp_git_repo() as temp_dir:
                content_list = []
                file_count = 0

                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(temp_dir)
                        file_size = file_path.stat().st_size

                        try:
                            async with aiofiles.open(file_path, encoding="utf-8") as f:
                                file_content = await f.read()
                        except UnicodeDecodeError:
                            file_content = i18n.t(
                                'components.git.gitextractor.logs.binary_file_marker')

                        content_list.append(
                            Data(data={
                                "path": str(relative_path),
                                "size": file_size,
                                "content": file_content
                            })
                        )
                        file_count += 1

                logger.info(i18n.t('components.git.gitextractor.logs.files_content_extracted',
                                   count=file_count))

                self.status = content_list
                return content_list

        except git.GitError as e:
            error_msg = i18n.t('components.git.gitextractor.errors.files_content_failed',
                               error=str(e))
            logger.error(error_msg)
            error_result = [Data(data={"error": error_msg})]
            self.status = error_result
            return error_result

    async def get_text_based_file_contents(self) -> Message:
        """Get all text-based file contents as a single formatted string.

        Returns:
            Message: Concatenated file contents with headers.
        """
        try:
            logger.info(
                i18n.t('components.git.gitextractor.logs.getting_text_contents'))

            char_limit = 300000
            truncation_notice = i18n.t('components.git.gitextractor.logs.truncation_notice',
                                       limit=char_limit // 1000)

            async with self.temp_git_repo() as temp_dir:
                content_list = [truncation_notice]
                total_chars = 0
                file_count = 0

                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        relative_path = file_path.relative_to(temp_dir)

                        content_list.extend([
                            "=" * 50,
                            f"File: /{relative_path}",
                            "=" * 50
                        ])

                        try:
                            async with aiofiles.open(file_path, encoding="utf-8") as f:
                                file_content = await f.read()

                                if total_chars + len(file_content) > char_limit:
                                    remaining_chars = char_limit - total_chars
                                    truncated_marker = i18n.t(
                                        'components.git.gitextractor.logs.content_truncated')
                                    file_content = file_content[:remaining_chars] + \
                                        f"\n{truncated_marker}"

                                content_list.append(file_content)
                                total_chars += len(file_content)
                                file_count += 1

                        except UnicodeDecodeError:
                            binary_marker = i18n.t(
                                'components.git.gitextractor.logs.binary_file_marker')
                            content_list.append(binary_marker)

                        content_list.append("")

                        if total_chars >= char_limit:
                            logger.warning(i18n.t('components.git.gitextractor.logs.char_limit_reached',
                                                  limit=char_limit))
                            break

                text_content = "\n".join(content_list)

                logger.info(i18n.t('components.git.gitextractor.logs.text_contents_generated',
                                   files=file_count,
                                   chars=total_chars))

                self.status = text_content
                return Message(text=text_content)

        except git.GitError as e:
            error_message = i18n.t('components.git.gitextractor.errors.text_contents_failed',
                                   error=str(e))
            logger.error(error_message)
            self.status = error_message
            return Message(text=error_message)
