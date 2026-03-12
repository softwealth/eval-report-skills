#!/usr/bin/env python3
"""
EVAL Skill File Validator

Validates skill files against the EVAL Skill Format Specification v1.0.
Usage:
    python validate_skill.py <path>           # Validate a file or directory
    python validate_skill.py --strict <path>  # Warnings become errors
    python validate_skill.py --json <path>    # Output results as JSON
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# --- Constants ---

VALID_CATEGORIES = {"inference", "data", "orchestration", "tracking", "training"}
VALID_CONFIDENCE = {"tested", "reviewed", "community"}

REQUIRED_FRONTMATTER = {
    "name": str,
    "version": str,
    "category": str,
    "trigger": str,
    "updated": (str, date),
    "confidence": str,
}

OPTIONAL_FRONTMATTER = {
    "eval_issue": int,
    "tags": list,
    "requires": list,
    "deprecated_by": str,
    "min_skill_format": str,
}

REQUIRED_SECTIONS = [
    "When to Use",
    "When NOT to Use",
    "Quick Start",
    "Common Patterns",
    "Configuration Reference",
    "Pitfalls & Gotchas",
    "Compared To",
]


# --- Data Classes ---

@dataclass
class ValidationResult:
    path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# --- Parsing ---

def parse_frontmatter(text: str) -> tuple[dict | None, str, str | None]:
    """Parse YAML frontmatter from markdown text.
    
    Returns:
        (frontmatter_dict, body, error_message)
    """
    if not text.startswith("---"):
        return None, text, "File does not start with YAML frontmatter (---)"

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text, "Malformed YAML frontmatter: missing closing ---"

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        return None, text, f"Invalid YAML in frontmatter: {e}"

    if not isinstance(fm, dict):
        return None, parts[2], "Frontmatter is not a YAML mapping"

    return fm, parts[2], None


def extract_sections(body: str) -> dict[str, str]:
    """Extract H2 sections from markdown body."""
    sections = {}
    current_name = None
    current_lines = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_name:
                sections[current_name] = "\n".join(current_lines).strip()
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_name:
        sections[current_name] = "\n".join(current_lines).strip()

    return sections


# --- Validators ---

def validate_frontmatter(fm: dict, result: ValidationResult) -> None:
    """Validate frontmatter fields."""
    # Check required fields
    for field_name, expected_type in REQUIRED_FRONTMATTER.items():
        if field_name not in fm:
            result.error(f"Missing required frontmatter field: '{field_name}'")
            continue

        value = fm[field_name]

        # Type check (handle tuple of types)
        if isinstance(expected_type, tuple):
            if not isinstance(value, expected_type):
                result.error(
                    f"Field '{field_name}' has wrong type: expected {expected_type}, "
                    f"got {type(value).__name__}"
                )
        else:
            if not isinstance(value, expected_type):
                # Allow date objects for string fields (YAML parses dates)
                if field_name == "updated" and isinstance(value, date):
                    pass
                else:
                    result.error(
                        f"Field '{field_name}' has wrong type: expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

    # Validate category enum
    if "category" in fm and fm["category"] not in VALID_CATEGORIES:
        result.error(
            f"Invalid category: '{fm['category']}'. "
            f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
        )

    # Validate confidence enum
    if "confidence" in fm and fm["confidence"] not in VALID_CONFIDENCE:
        result.error(
            f"Invalid confidence: '{fm['confidence']}'. "
            f"Must be one of: {', '.join(sorted(VALID_CONFIDENCE))}"
        )

    # Validate trigger field
    if "trigger" in fm:
        trigger = fm["trigger"]
        if isinstance(trigger, str):
            if len(trigger) < 20:
                result.warn("Trigger field seems too short (< 20 chars)")
            if not trigger.lower().startswith("when"):
                result.warn("Trigger field should start with 'when'")

    # Validate date format
    if "updated" in fm:
        val = fm["updated"]
        if isinstance(val, str):
            try:
                date.fromisoformat(val)
            except ValueError:
                result.error(
                    f"Invalid date format for 'updated': '{val}'. Use YYYY-MM-DD."
                )
        elif isinstance(val, date):
            pass  # YAML parsed it as a date, that's fine
        else:
            result.error(f"'updated' must be a date string (YYYY-MM-DD), got {type(val).__name__}")

    # Validate name field format
    if "name" in fm and isinstance(fm["name"], str):
        if fm["name"] != fm["name"].lower():
            result.warn(f"Name field should be lowercase: '{fm['name']}'")
        if " " in fm["name"]:
            result.error(f"Name field must not contain spaces: '{fm['name']}'")

    # Warn about unknown fields
    known = set(REQUIRED_FRONTMATTER) | set(OPTIONAL_FRONTMATTER)
    for key in fm:
        if key not in known:
            result.warn(f"Unknown frontmatter field: '{key}'")


def validate_sections(sections: dict[str, str], result: ValidationResult) -> None:
    """Validate required sections exist and have content."""
    for section_name in REQUIRED_SECTIONS:
        if section_name not in sections:
            result.error(f"Missing required section: '## {section_name}'")
        elif not sections[section_name].strip():
            result.error(f"Section '## {section_name}' is empty")

    # Check "When NOT to Use" has alternatives
    if "When NOT to Use" in sections:
        content = sections["When NOT to Use"]
        lines = [l.strip() for l in content.split("\n") if l.strip().startswith("-")]
        for line in lines:
            if "->" not in line and "instead" not in line.lower():
                result.warn(
                    f"'When NOT to Use' bullet should recommend an alternative "
                    f"(use -> format): {line[:80]}"
                )

    # Check Quick Start has code blocks
    if "Quick Start" in sections:
        if "```" not in sections["Quick Start"]:
            result.warn("Quick Start section should contain code blocks")

    # Check Configuration Reference has a table
    if "Configuration Reference" in sections:
        if "|" not in sections["Configuration Reference"]:
            result.warn("Configuration Reference should contain a markdown table")

    # Check Compared To has a table
    if "Compared To" in sections:
        if "|" not in sections["Compared To"]:
            result.warn("Compared To section should contain a comparison table")

    # Check Common Patterns has H3 subsections
    if "Common Patterns" in sections:
        if "###" not in sections["Common Patterns"]:
            result.warn("Common Patterns should have named subsections (### headings)")
        if "```" not in sections["Common Patterns"]:
            result.warn("Common Patterns should contain code examples")


def validate_filename(path: pathlib.Path, fm: dict, result: ValidationResult) -> None:
    """Validate filename conventions."""
    name = path.stem  # filename without extension

    if path.suffix != ".md":
        result.error(f"Skill files must have .md extension, got: {path.suffix}")

    if name != name.lower():
        result.warn(f"Filename should be lowercase: {path.name}")

    if " " in name:
        result.error(f"Filename must not contain spaces: {path.name}")

    # Check that filename starts with the tool name
    if "name" in fm and isinstance(fm["name"], str):
        tool_name = fm["name"].lower().replace("_", "-")
        if not name.startswith(tool_name):
            result.warn(
                f"Filename '{name}' should start with tool name '{tool_name}'"
            )


def validate_directory(path: pathlib.Path, fm: dict, result: ValidationResult) -> None:
    """Validate that the file is in the correct category directory."""
    if "category" not in fm:
        return

    parent_name = path.parent.name
    expected_category = fm["category"]

    if parent_name in VALID_CATEGORIES and parent_name != expected_category:
        result.error(
            f"File is in '{parent_name}/' but frontmatter category is "
            f"'{expected_category}'. Move to 'skills/{expected_category}/'."
        )


# --- Main Validation ---

def validate_skill(path: pathlib.Path) -> ValidationResult:
    """Validate a single skill file."""
    result = ValidationResult(path=str(path))

    # Read file
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        result.error(f"Cannot read file: {e}")
        return result

    if not text.strip():
        result.error("File is empty")
        return result

    # Parse frontmatter
    fm, body, parse_error = parse_frontmatter(text)
    if parse_error:
        result.error(parse_error)

    if fm:
        validate_frontmatter(fm, result)
        validate_filename(path, fm, result)
        validate_directory(path, fm, result)

    # Parse and validate sections
    sections = extract_sections(body)
    validate_sections(sections, result)

    return result


def validate_path(path: pathlib.Path) -> list[ValidationResult]:
    """Validate a file or directory of skill files."""
    results = []

    if path.is_file():
        if path.suffix == ".md":
            results.append(validate_skill(path))
        else:
            r = ValidationResult(path=str(path))
            r.error(f"Not a markdown file: {path}")
            results.append(r)
    elif path.is_dir():
        md_files = sorted(path.rglob("*.md"))
        if not md_files:
            r = ValidationResult(path=str(path))
            r.warn("No .md files found in directory")
            results.append(r)
        for md_path in md_files:
            # Skip non-skill files
            if md_path.name.startswith(".") or md_path.name.upper() == md_path.name:
                continue
            results.append(validate_skill(md_path))
    else:
        r = ValidationResult(path=str(path))
        r.error(f"Path does not exist: {path}")
        results.append(r)

    return results


# --- Output ---

def print_results(results: list[ValidationResult], strict: bool = False) -> int:
    """Print validation results. Returns exit code (0=pass, 1=fail)."""
    total_errors = 0
    total_warnings = 0
    total_files = len(results)

    for result in results:
        errors = result.errors[:]
        if strict:
            errors.extend(result.warnings)
            warnings = []
        else:
            warnings = result.warnings

        if errors or warnings:
            print(f"\n{'FAIL' if errors else 'WARN'} {result.path}")

            for err in errors:
                print(f"  ERROR: {err}")
            for warn in warnings:
                print(f"  WARN:  {warn}")

            total_errors += len(errors)
            total_warnings += len(warnings)
        else:
            print(f"  OK  {result.path}")

    print(f"\n{'='*60}")
    print(f"Files: {total_files}  Errors: {total_errors}  Warnings: {total_warnings}")

    if total_errors > 0:
        print("VALIDATION FAILED")
        return 1
    else:
        print("VALIDATION PASSED")
        return 0


def print_json(results: list[ValidationResult], strict: bool = False) -> int:
    """Print results as JSON. Returns exit code."""
    output = {
        "results": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.valid),
            "failed": sum(1 for r in results if not r.valid),
        },
    }

    if strict:
        for r in output["results"]:
            r["errors"].extend(r["warnings"])
            r["warnings"] = []
            r["valid"] = len(r["errors"]) == 0
        output["summary"]["passed"] = sum(1 for r in output["results"] if r["valid"])
        output["summary"]["failed"] = sum(1 for r in output["results"] if not r["valid"])

    print(json.dumps(output, indent=2))

    return 0 if output["summary"]["failed"] == 0 else 1


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(
        description="Validate EVAL Skill files against the format specification.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s skills/inference/vllm-serving.md    Validate single file
  %(prog)s skills/                             Validate all skills
  %(prog)s --strict skills/                    Warnings become errors
  %(prog)s --json skills/                      JSON output
        """,
    )
    parser.add_argument(
        "path",
        type=pathlib.Path,
        help="Path to a skill file or directory of skill files",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    results = validate_path(args.path)

    if args.json_output:
        exit_code = print_json(results, strict=args.strict)
    else:
        exit_code = print_results(results, strict=args.strict)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
