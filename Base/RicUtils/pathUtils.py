from pathlib import Path
from functools import lru_cache
import os


@lru_cache(maxsize=None)
def find_project_root(marker_files=None):
    """
    从当前文件向上查找项目根目录，依据是否存在 marker_files 中的任一文件。

    Args:
        marker_files: 用于识别根目录的文件名列表，如 ['.env', 'pyproject.toml', 'requirements.txt']

    Returns:
        Path: 项目根目录的 Path 对象
    """
    if marker_files is None:
        marker_files = ['.env', 'pyproject.toml', 'requirements.txt', '.git']

    current_path = Path(__file__).resolve().parent
    while current_path != current_path.parent:  # 防止无限循环到根目录
        if any((current_path / marker).exists() for marker in marker_files):
            return current_path
        current_path = current_path.parent
    # 如果没找到，回退到当前文件所在目录的父级（或抛异常）
    return Path(__file__).resolve().parent.parent  # 保守回退


def to_absolute_path(file_path: str) -> str:
    """
    将相对路径转换为基于项目根目录的绝对路径。

    Args:
        file_path: 文件路径（可以是相对路径或绝对路径）

    Returns:
        绝对路径字符串

    Examples:
        >>> to_absolute_path("data/config.json")
        '/path/to/project/data/config.json'

        >>> to_absolute_path("/absolute/path/file.txt")
        '/absolute/path/file.txt'
    """
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(str(find_project_root()), file_path)
