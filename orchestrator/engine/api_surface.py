"""Deterministic guards against "verified" changes that quietly break callers.

An LLM that is allowed to rewrite both the code and its tests can make its own tests pass while removing or
reshaping the public API. These checks compare the patched Python files with the originals and report removed or
changed public names and deleted tests, so the gate can reject the patch (or ask for a revision) without trusting
the model's self-assessment.
"""
from __future__ import annotations

import ast
import re
from typing import Dict, List, Set


def _signature(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f"{node.name}({ast.unparse(node.args)})"
    if isinstance(node, ast.ClassDef):
        bases = ", ".join(ast.unparse(b) for b in node.bases)
        return f"class {node.name}({bases})"
    return ""


def public_surface(source: str) -> Dict[str, str]:
    """Public top-level functions/classes (and public methods of public classes) -> signature."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out: Dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            out[node.name] = _signature(node)
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                        out[f"{node.name}.{item.name}"] = _signature(item)
        elif isinstance(node, ast.Assign):  # public module constants / state other modules may import
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_") and target.id.isupper():
                    out[target.id] = target.id
    return out


def test_names(source: str) -> Set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test")
    }


def _mentioned(goal: str, *words: str) -> bool:
    text = goal.lower()
    return any(w and re.search(rf"(?<![a-z0-9_]){re.escape(w.lower())}(?![a-z0-9_])", text) for w in words)


def _params(sig: str) -> Set[str]:
    inner = sig[sig.find("(") + 1: sig.rfind(")")]
    names = set()
    for part in inner.split(","):
        name = part.strip().lstrip("*").split(":")[0].split("=")[0].strip()
        if name and name not in ("self", "cls"):
            names.add(name)
    return names


def contract_problems(filename: str, old: str, new: str, goal: str) -> List[str]:
    """Problems for one file. A removal/change is allowed only if the goal actually talks about it."""
    problems: List[str] = []
    is_test_file = bool(re.search(r"(^|/)(test_[^/]*|[^/]*_test)\.py$", filename))
    if is_test_file:
        removed = sorted(test_names(old) - test_names(new))
        if removed:
            problems.append(
                f"{filename}: existing tests were deleted ({', '.join(removed[:6])}). Keep them; update their "
                "assertions only where the goal requires the behaviour to change."
            )
        return problems

    before, after = public_surface(old), public_surface(new)
    for name, sig in before.items():
        bare = name.split(".")[-1]
        if name not in after:
            if not _mentioned(goal, name, bare):
                problems.append(
                    f"{filename}: public API removed without the goal asking for it: {sig}. Keep existing public "
                    "names and signatures; extend them instead of replacing them."
                )
        elif after[name] != sig:
            changed_params = _params(sig) ^ _params(after[name])
            if not _mentioned(goal, name, bare, *changed_params):
                problems.append(
                    f"{filename}: public signature changed without the goal asking for it: {sig} -> {after[name]}. "
                    "Keep it backward compatible (add optional parameters instead)."
                )
    return problems
