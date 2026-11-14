"""Static sanity check for AI-generated Playwright scripts BEFORE they can be saved for review/approval.

This is a guard-rail, not a sandbox: the real control is mandatory human review.
"""
import ast

ALLOWED_IMPORT_ROOTS = {"pytest", "playwright", "automation", "re", "csv", "json", "typing", "pathlib"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "open", "__import__", "input", "breakpoint"}
FORBIDDEN_ATTRS = {"system", "popen", "sleep", "rmtree", "remove", "unlink"}


def check_script(code: str) -> list[dict]:
    issues: list[dict] = []

    def err(msg):
        issues.append({"severity": "error", "code": "unsafe_or_invalid_script", "message": msg})

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        err(f"Script is not valid Python: {e.msg} (line {e.lineno}).")
        return issues
    has_test = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORT_ROOTS:
                    err(f"Import '{a.name}' is not allowed.")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORT_ROOTS or node.level:
                err(f"Import from '{node.module}' is not allowed.")
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id in FORBIDDEN_CALLS:
                err(f"Call to '{f.id}()' is not allowed.")
            if isinstance(f, ast.Attribute) and f.attr in FORBIDDEN_ATTRS:
                err(f"Call to '.{f.attr}()' is not allowed (no fixed sleeps / shell / file deletion).")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            has_test = True
    if not has_test:
        err("Script must define at least one function named test_*.")
    if "assert" not in code:
        issues.append({"severity": "warning", "code": "no_assertions", "message": "Script contains no assert statements."})
    return issues


def test_function_names(code: str) -> list[str]:
    try:
        return [n.name for n in ast.walk(ast.parse(code)) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    except SyntaxError:
        return []
