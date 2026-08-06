"""Tools for managing relative and absolute paths."""
import os
from pathlib import Path
from typing import Optional


class RelativePathUtil:

    @staticmethod
    def maybe_relativize(f: Path, possible_ancestor_directory: Path, relative_to_directory: Path,
                         strict: bool = True) -> Path:
        """If f is under possible_ancestor_directory, return f relative to relative_to_directory;
        otherwise return f as absolute."""
        if strict:
            if not relative_to_directory.is_dir():
                raise ValueError(f"relativeTo path {relative_to_directory} is not a directory.")
            if not possible_ancestor_directory.is_dir():
                raise ValueError(f"possibleAncestor path {possible_ancestor_directory} is not a directory.")
        f_path = f.resolve()
        ancestor_path = possible_ancestor_directory.resolve()
        if f_path == ancestor_path or ancestor_path in f_path.parents:
            return Path(os.path.relpath(f_path, relative_to_directory.resolve()))
        return f_path

    @staticmethod
    def maybe_absolutize(f: Path, relative_to_directory: Optional[Path], strict: bool = True) -> Path:
        """Convert a possibly-relative File to an absolute File, resolved against relative_to_directory."""
        if relative_to_directory is None:
            relative_to_directory = Path(".")
        if strict and not relative_to_directory.is_dir():
            raise ValueError(f"relativeTo path {relative_to_directory} is not a directory.")
        if f.is_absolute():
            return Path(os.path.normpath(f))
        return Path(os.path.normpath(relative_to_directory / f))

    @staticmethod
    def normalize_file(f: Path) -> Path:
        """Eliminate /../ where possible."""
        return Path(os.path.normpath(f))
