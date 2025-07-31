"""TCSS validator using Textual's native CSS parser."""

import time
from typing import List, Optional, Tuple, Any
from dataclasses import dataclass

try:
    from textual.css.parse import parse
    from textual.css.errors import (
        StylesheetError,
        DeclarationError,
        UnresolvedVariableError,
    )
    from textual.css.tokenize import tokenize_values
    from textual.theme import BUILTIN_THEMES
    from textual.design import ColorSystem
except ImportError as e:
    raise ImportError(f"Failed to import Textual CSS components: {e}")

from ..utils.errors import ValidationError, ParsingError
from ..utils.logging_config import LoggerMixin, log_validation_result
from ..config import ValidatorConfig


@dataclass
class ValidationResult:
    """Result of CSS validation."""

    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    suggestions: List[str]
    summary: str
    parse_time_ms: float
    rule_count: int
    selector_count: int


@dataclass
class SelectorInfo:
    """Information about a CSS selector."""

    selector: str
    specificity: Tuple[int, int, int]  # (id, class, type)
    line: Optional[int] = None
    column: Optional[int] = None


class TCSSValidator(LoggerMixin):
    """Main TCSS validator using Textual's native parser."""

    def __init__(self, config: ValidatorConfig):
        self.config = config
        self.strict_mode = config.strict_mode

    def validate(
        self, css_content: str, filename: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate TCSS content using Textual's native parser.

        Args:
            css_content: The CSS content to validate
            filename: Optional filename for error reporting

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        start_time = time.time()
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        suggestions: List[str] = []
        rule_count = 0
        selector_count = 0

        try:
            # Check file size limit
            if len(css_content) > self.config.max_file_size:
                errors.append(
                    ValidationError(
                        f"CSS content exceeds maximum size limit of {self.config.max_file_size} bytes"
                    )
                )
                return self._create_result(
                    False, errors, warnings, suggestions, 0, 0, 0
                )

            # Parse CSS using Textual's native parser
            try:
                # Get default theme variables
                default_theme = BUILTIN_THEMES.get("textual-dark")
                if default_theme:
                    # Generate CSS variables from the theme
                    color_system = ColorSystem(
                        primary=default_theme.primary,
                        secondary=default_theme.secondary,
                        warning=default_theme.warning,
                        error=default_theme.error,
                        success=default_theme.success,
                        accent=default_theme.accent,
                        foreground=default_theme.foreground,
                        background=default_theme.background,
                        surface=default_theme.surface,
                        panel=default_theme.panel,
                        boost=default_theme.boost,
                        dark=default_theme.dark,
                        luminosity_spread=default_theme.luminosity_spread,
                        text_alpha=default_theme.text_alpha,
                        variables=default_theme.variables,
                    )
                    theme_variables = color_system.generate()

                    # Tokenize the theme variables
                    variable_tokens = tokenize_values(theme_variables)
                else:
                    variable_tokens = None

                # Parse with theme variables
                stylesheet = parse(
                    "*", css_content, ("inline", "0"), variable_tokens=variable_tokens
                )
                # Count rules and selectors
                rules = list(stylesheet)
                rule_count = len(rules)

                for rule in rules:
                    if hasattr(rule, "selectors"):
                        selector_count += len(rule.selectors)

                # Perform additional validation checks
                self._validate_stylesheet(stylesheet, errors, warnings, suggestions)

            except StylesheetError as e:
                errors.append(self._convert_stylesheet_error(e))
            except DeclarationError as e:
                errors.append(self._convert_declaration_error(e))
            except UnresolvedVariableError as e:
                errors.append(self._convert_variable_error(e))
            except Exception as e:
                errors.append(ParsingError(f"Unexpected parsing error: {str(e)}"))

            # Perform semantic validation if no parsing errors
            if not errors:
                self._semantic_validation(css_content, warnings, suggestions)

        except Exception as e:
            self.logger.error(f"Validation failed: {e}")
            errors.append(ValidationError(f"Validation failed: {str(e)}"))

        parse_time = time.time() - start_time

        # Log validation results
        log_validation_result(len(css_content), len(errors), len(warnings), parse_time)

        return self._create_result(
            len(errors) == 0,
            errors,
            warnings,
            suggestions,
            parse_time * 1000,
            rule_count,
            selector_count,
        )

    def validate_file(self, file_path: str) -> ValidationResult:
        """Validate a TCSS file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            result: ValidationResult = self.validate(content, filename=file_path)
            return result
        except FileNotFoundError:
            error = ValidationError(f"File not found: {file_path}")
            return ValidationResult(
                valid=False,
                errors=[error],
                warnings=[],
                suggestions=[],
                summary="File not found",
                parse_time_ms=0,
                rule_count=0,
                selector_count=0,
            )
        except Exception as e:
            error = ValidationError(f"Failed to read file {file_path}: {str(e)}")
            return ValidationResult(
                valid=False,
                errors=[error],
                warnings=[],
                suggestions=[],
                summary="File read error",
                parse_time_ms=0,
                rule_count=0,
                selector_count=0,
            )

    def _validate_stylesheet(
        self,
        stylesheet: Any,
        errors: List[ValidationError],
        warnings: List[ValidationError],
        suggestions: List[str],
    ) -> None:
        """Perform additional validation on parsed stylesheet."""
        try:
            # Check for duplicate selectors
            selector_map = {}
            for rule in stylesheet:
                if hasattr(rule, "selectors"):
                    for selector in rule.selectors:
                        selector_str = str(selector)
                        if selector_str in selector_map:
                            warnings.append(
                                ValidationError(
                                    f"Duplicate selector: {selector_str}",
                                    selector=selector_str,
                                )
                            )
                        else:
                            selector_map[selector_str] = rule

            # Check for overly specific selectors
            for rule in stylesheet:
                if hasattr(rule, "selectors"):
                    for selector in rule.selectors:
                        specificity = self._calculate_specificity(selector)
                        if specificity[0] > 2:  # Too many IDs
                            warnings.append(
                                ValidationError(
                                    f"Selector has high ID specificity: {selector}",
                                    selector=str(selector),
                                )
                            )
                        elif sum(specificity) > 10:  # Overall too specific
                            suggestions.append(
                                f"Consider simplifying selector: {selector}"
                            )

            # Check for empty rules
            for rule in stylesheet:
                if hasattr(rule, "declarations") and not rule.declarations:
                    warnings.append(
                        ValidationError(
                            f"Empty rule for selector: {rule.selectors[0] if rule.selectors else 'unknown'}",
                            selector=str(rule.selectors[0]) if rule.selectors else None,
                        )
                    )

        except Exception as e:
            self.logger.warning(f"Additional validation failed: {e}")

    def _semantic_validation(
        self, css_content: str, warnings: List[ValidationError], suggestions: List[str]
    ) -> None:
        """Perform semantic validation checks."""
        lines = css_content.split("\n")

        # Check for common issues
        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Check for missing semicolons
            if ":" in line and not line.endswith((";", "{", "}")):
                if not line.endswith("*/"):  # Not a comment
                    warnings.append(
                        ValidationError(
                            "Missing semicolon at end of declaration", line=i
                        )
                    )

            # Check for color values that could be variables
            if any(
                color in line.lower() for color in ["#ffffff", "#000000", "#ff0000"]
            ):
                suggestions.append(
                    f"Line {i}: Consider using CSS variables for common colors"
                )

    def _calculate_specificity(self, selector: Any) -> Tuple[int, int, int]:
        """Calculate CSS selector specificity (id, class, type)."""
        try:
            # This is a simplified specificity calculation
            # In a real implementation, you'd parse the selector more thoroughly
            selector_str = str(selector)

            id_count = selector_str.count("#")
            class_count = (
                selector_str.count(".")
                + selector_str.count("[")
                + selector_str.count(":")
            )
            type_count = len(
                [
                    part
                    for part in selector_str.split()
                    if part and not part.startswith(("#", ".", "[", ":"))
                ]
            )

            return (id_count, class_count, type_count)
        except Exception:
            return (0, 0, 0)

    def _convert_stylesheet_error(self, error: StylesheetError) -> ValidationError:
        """Convert Textual StylesheetError to ValidationError."""
        return ParsingError(
            message=str(error),
            line=getattr(error, "line", None),
            column=getattr(error, "column", None),
        )

    def _convert_declaration_error(self, error: DeclarationError) -> ValidationError:
        """Convert Textual DeclarationError to ValidationError."""
        return ValidationError(
            message=str(error),
            line=getattr(error, "line", None),
            column=getattr(error, "column", None),
            property_name=getattr(error, "property", None),
        )

    def _convert_variable_error(
        self, error: UnresolvedVariableError
    ) -> ValidationError:
        """Convert Textual UnresolvedVariableError to ValidationError."""
        return ValidationError(
            message=f"Unresolved CSS variable: {error}",
            line=getattr(error, "line", None),
            column=getattr(error, "column", None),
        )

    def _create_result(
        self,
        valid: bool,
        errors: List[ValidationError],
        warnings: List[ValidationError],
        suggestions: List[str],
        parse_time_ms: float,
        rule_count: int,
        selector_count: int,
    ) -> ValidationResult:
        """Create a ValidationResult with summary."""
        if valid:
            if warnings:
                summary = f"Valid with {len(warnings)} warnings"
            else:
                summary = "Valid CSS"
        else:
            summary = f"Invalid CSS: {len(errors)} errors"

        if suggestions:
            summary += f", {len(suggestions)} suggestions"

        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            summary=summary,
            parse_time_ms=parse_time_ms,
            rule_count=rule_count,
            selector_count=selector_count,
        )
