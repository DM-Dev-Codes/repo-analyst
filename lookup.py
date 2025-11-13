"""Code symbol lookup builder for httpx library."""

import ast
import logging
import os
from pathlib import Path
from typing import List

from metadata import SymbolMetadata

HTTPX_DIR = os.getenv(
    "HTTPX_SOURCE_DIR", 
    str(Path(__file__).parent / "httpx" / "httpx")
)

logger = logging.getLogger(__name__)


class LookupBuilder:
    """Build and query symbol lookup table from Python source files."""
    
    def __init__(self, httpx_dir: str | None = None) -> None:
        """Initialize lookup builder.

        Args:
            httpx_dir: Path to httpx source directory

        Raises:
            ValueError: If directory doesn't exist
        """
        if httpx_dir:
            self.root_dir = Path(httpx_dir)
        else:
            self.root_dir = Path(HTTPX_DIR)

        if not self.root_dir.exists():
            raise ValueError(f"httpx directory not found: {self.root_dir}")

        self.lookup_table: dict[str, list[SymbolMetadata]] = {}
        logger.debug(f"Initialized with root_dir: {self.root_dir}")

    def build(self) -> dict[str, list[SymbolMetadata]]:
        """Build lookup table from source files.
        
        Returns:
            Symbol lookup table mapping qualified names to metadata
        """
        results = self._read_file_content()
        self._extract_metadata_from_trees(results)
        logger.info(f"Built lookup table with {len(self.lookup_table)} keys")
        return self.lookup_table

    def _read_file_content(self) -> list[tuple[Path, Path, ast.AST]]:
        """Parse Python files into AST trees.
        
        Returns:
            List of (absolute_path, relative_path, ast_tree) tuples
        """
        logger.debug(f"Scanning directory: {self.root_dir}")
        py_files = list(self.root_dir.rglob("*.py"))
        logger.info(f"Found {len(py_files)} Python files")

        results: list[tuple[Path, Path, ast.AST]] = []
        for file_path in py_files:
            try:
                with file_path.open(encoding="utf-8") as f:
                    source = f.read()
                tree = ast.parse(source, filename=str(file_path))
                relative_path = file_path.relative_to(self.root_dir)
                results.append((file_path, relative_path, tree))
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error reading {file_path}: {e}")
                continue

        return results

    def _extract_metadata_from_trees(
        self, results: list[tuple[Path, Path, ast.AST]]
    ) -> None:
        """Extract symbol metadata from AST trees.
        
        Args:
            results: List of (absolute_path, relative_path, ast_tree) tuples
        """
        for absolute_path, relative_path, tree in results:
            for node in tree.body:
                match node:
                    case ast.ClassDef():
                        self._add_metadata(node, "class", absolute_path, relative_path)
                        for item in node.body:
                            match item:
                                case ast.FunctionDef() | ast.AsyncFunctionDef():
                                    self._add_metadata(
                                        item,
                                        "method",
                                        absolute_path,
                                        relative_path,
                                        parent_class=node.name,
                                    )
                    case ast.FunctionDef() | ast.AsyncFunctionDef():
                        self._add_metadata(
                            node, "function", absolute_path, relative_path
                        )

    def _add_metadata(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        node_type: str,
        absolute_path: Path,
        relative_path: Path,
        parent_class: str | None = None,
    ) -> None:
        """Add symbol metadata to lookup table.
        
        Args:
            node: AST node (function, method, or class)
            node_type: Type string ('class', 'function', or 'method')
            absolute_path: Full file path
            relative_path: Path relative to source root
            parent_class: Parent class name for methods
        """
        metadata = SymbolMetadata(
            type=node_type,
            name=node.name,
            parent_class=parent_class,
            docstring=ast.get_docstring(node),
            start_line=node.lineno,
            end_line=node.end_lineno,
            file_path=str(absolute_path),  # Store ABSOLUTE path for reading
            module_name=self._get_module_name(relative_path),
        )

        key = (
            f"{metadata.module_name}.{parent_class}.{node.name}"
            if parent_class
            else f"{metadata.module_name}.{node.name}"
        )
        self.lookup_table.setdefault(key, []).append(metadata)

    def _get_module_name(self, file_path: Path) -> str:
        """Convert file path to module name."""
        return ".".join(file_path.with_suffix("").parts)

    def query_symbols(self, symbols: List[str]) -> List[SymbolMetadata]:
        """Query lookup table for symbols.
        
        Args:
            symbols: List of symbol names to find
            
        Returns:
            List of matching symbol metadata
        """
        logger.debug(f"Querying symbols: {symbols}")
        all_results = []

        for symbol in symbols:
            # Exact match
            if symbol in self.lookup_table:
                matches = self.lookup_table[symbol]
                logger.debug(f"Exact match for '{symbol}': {len(matches)} results")
                all_results.extend(matches)
                continue

            # Suffix matching for partial paths
            matches = [
                metadata
                for key, metadata_list in self.lookup_table.items()
                if key.endswith(f".{symbol}") or key == symbol
                for metadata in metadata_list
            ]

            logger.debug(f"Suffix match for '{symbol}': {len(matches)} results")
            all_results.extend(matches)

        logger.debug(f"Total results: {len(all_results)}")
        return all_results

    def get_code_chunk(self, metadata: SymbolMetadata) -> str:
        """Read code chunk from file.
        
        Args:
            metadata: Symbol metadata with file path and line numbers
            
        Returns:
            Source code string
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If line numbers are invalid
        """
        file_path = Path(metadata.file_path)

        logger.debug(f"Reading code from: {file_path}")
        logger.debug(f"Lines {metadata.start_line}-{metadata.end_line}")

        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        with file_path.open(encoding="utf-8") as f:
            lines = f.readlines()

        if metadata.start_line < 1:
            raise ValueError(f"Invalid start_line: {metadata.start_line}")
        if metadata.end_line > len(lines):
            raise ValueError(
                f"end_line {metadata.end_line} exceeds file length {len(lines)}"
            )

        code = "".join(lines[metadata.start_line - 1 : metadata.end_line])
        logger.debug(f"Successfully read {len(code)} characters")
        return code
