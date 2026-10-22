"""Parse source, never import or execute it. No guessed C function boundaries."""

import ast
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from shared.http import ServiceError
from shared.schemas import Language


@dataclass(frozen=True)
class Function:
    name: str
    file: str
    start_line: int
    end_line: int
    code: str
    language: Language
    extractor: str


def _python_ast(code: str, file: str) -> list[Function]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, RecursionError, ValueError):
        raise ServiceError(
            "EXTRACTION_FAILED", "Invalid or excessively nested Python source", 422
        ) from None
    lines = code.splitlines(keepends=True)
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            end = node.end_lineno or node.lineno
            result.append(
                Function(
                    node.name,
                    file,
                    start,
                    end,
                    "".join(lines[start - 1 : end]),
                    "python",
                    "python-ast",
                )
            )
    return sorted(result, key=lambda f: (f.start_line, f.name))


def extract_functions(
    code: str, language: Language, file: str, *, allow_python_ast: bool = False
) -> list[Function]:
    try:
        ts = import_module("tree_sitter")
        grammar = import_module(
            {
                "c": "tree_sitter_c",
                "cpp": "tree_sitter_cpp",
                "python": "tree_sitter_python",
            }[language]
        )
    except ImportError:
        if language == "python" and allow_python_ast:
            return _python_ast(code, file)
        raise ServiceError(
            "EXTRACTOR_UNAVAILABLE",
            "Install tree-sitter and the configured language grammar",
        ) from None
    parser = ts.Parser(ts.Language(grammar.language()))
    encoded = code.encode("utf-8")
    tree = parser.parse(encoded)
    if tree.root_node.has_error:
        raise ServiceError(
            "EXTRACTION_FAILED",
            "Source contains syntax errors or is an incomplete diff fragment",
            422,
        )
    output: list[Function] = []

    def visit(node: Any) -> None:
        if node.type in {"function_definition", "function_definition_item"}:
            name_node = node.child_by_field_name("name")
            if name_node is None:
                name_node = node.child_by_field_name("declarator")
                while name_node is not None and name_node.type not in {
                    "identifier",
                    "field_identifier",
                    "operator_name",
                    "destructor_name",
                }:
                    nested = name_node.child_by_field_name("declarator")
                    if nested is None:
                        break
                    name_node = nested
            if name_node is None:
                raise ServiceError(
                    "EXTRACTION_FAILED", "Unable to identify function name", 422
                )
            start = node.start_point.row + 1
            end = node.end_point.row + 1
            if (
                language == "python"
                and node.parent
                and node.parent.type == "decorated_definition"
            ):
                node = node.parent
                start = node.start_point.row + 1
            output.append(
                Function(
                    encoded[name_node.start_byte : name_node.end_byte].decode(),
                    file,
                    start,
                    end,
                    encoded[node.start_byte : node.end_byte].decode(),
                    language,
                    "tree-sitter",
                )
            )
        for child in node.children:
            visit(child)

    visit(tree.root_node)
    return sorted(output, key=lambda f: (f.start_line, f.name))
