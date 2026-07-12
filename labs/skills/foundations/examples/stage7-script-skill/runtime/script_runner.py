"""ScriptRunner：统一处理 Skill 私有脚本的安全执行。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .types import ScriptCallResult, ScriptDeclaration


class ScriptRunner:
    """受控脚本执行器。

    Executor 可以决定“这次要调用哪个脚本”，但脚本能不能执行、如何执行、
    参数是否合法，都集中放在这里处理。
    """

    def run(
        self,
        *,
        skill_dir: Path,
        declarations: tuple[ScriptDeclaration, ...],
        script_name: str,
        arguments: dict[str, Any],
    ) -> ScriptCallResult:
        declaration = _find_declaration(declarations, script_name)
        if declaration is None:
            return ScriptCallResult(
                name=script_name,
                path="",
                status="rejected",
                error="script is not declared by selected skill",
            )

        script_path, error = _resolve_script_path(skill_dir, declaration.path)
        if error:
            return ScriptCallResult(
                name=declaration.name,
                path=declaration.path,
                status="rejected",
                error=error,
            )

        schema_error = _validate_arguments(arguments, declaration.input_schema)
        if schema_error:
            return ScriptCallResult(
                name=declaration.name,
                path=_relative_to_skill(script_path, skill_dir),
                status="rejected",
                error=schema_error,
            )

        try:
            completed = subprocess.run(
                [sys.executable, str(script_path)],
                input=json.dumps(arguments, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=declaration.timeout_seconds,
                cwd=skill_dir,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ScriptCallResult(
                name=declaration.name,
                path=_relative_to_skill(script_path, skill_dir),
                status="timeout",
                error=f"script timed out after {declaration.timeout_seconds} seconds",
                stdout_preview=_preview(exc.stdout),
                stderr_preview=_preview(exc.stderr),
            )

        result: dict[str, Any] = {}
        error_text = ""
        if completed.stdout.strip():
            try:
                parsed = json.loads(completed.stdout)
                if isinstance(parsed, dict):
                    result = parsed
                else:
                    error_text = "script stdout must be a JSON object"
            except json.JSONDecodeError as exc:
                error_text = f"script stdout is not valid JSON: {exc.msg}"

        status = "completed" if completed.returncode == 0 and not error_text else "failed"
        return ScriptCallResult(
            name=declaration.name,
            path=_relative_to_skill(script_path, skill_dir),
            status=status,
            exit_code=completed.returncode,
            result=result,
            stdout_preview=_preview(completed.stdout),
            stderr_preview=_preview(completed.stderr),
            error=error_text,
        )


def _find_declaration(
    declarations: tuple[ScriptDeclaration, ...],
    script_name: str,
) -> ScriptDeclaration | None:
    for declaration in declarations:
        if declaration.name == script_name:
            return declaration
    return None


def _resolve_script_path(skill_dir: Path, declared_path: str) -> tuple[Path, str]:
    raw_path = Path(declared_path)
    if raw_path.is_absolute():
        return raw_path, "script path must be relative to selected skill"

    scripts_dir = (skill_dir / "scripts").resolve()
    script_path = (skill_dir / raw_path).resolve()

    if scripts_dir not in script_path.parents:
        return script_path, "script path must stay inside selected skill scripts directory"
    if not script_path.is_file():
        return script_path, "script file does not exist"

    return script_path, ""


def _validate_arguments(arguments: dict[str, Any], schema: dict[str, Any]) -> str:
    if not isinstance(arguments, dict):
        return "script arguments must be a JSON object"

    required = schema.get("required", [])
    if not isinstance(required, list):
        return "input_schema.required must be a list"

    for key in required:
        if key not in arguments:
            return f"missing required argument: {key}"

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return "input_schema.properties must be an object"

    for key, rules in properties.items():
        if key not in arguments:
            continue
        if not isinstance(rules, dict):
            return f"schema rules for {key} must be an object"
        value = arguments[key]
        expected_type = rules.get("type")
        if expected_type == "string" and not isinstance(value, str):
            return f"argument {key} must be a string"
        max_length = rules.get("max_length")
        if isinstance(max_length, int) and isinstance(value, str) and len(value) > max_length:
            return f"argument {key} exceeds max_length {max_length}"

    return ""


def _relative_to_skill(path: Path, skill_dir: Path) -> str:
    try:
        return str(path.relative_to(skill_dir.resolve()))
    except ValueError:
        return str(path)


def _preview(value: str | bytes | None, limit: int = 240) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "..."
