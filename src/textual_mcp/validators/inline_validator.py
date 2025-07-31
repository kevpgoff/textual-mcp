"""Inline CSS validator using Textual's parse_declarations."""

from typing import List, Any
from dataclasses import dataclass

try:
    from textual.css.parse import parse_declarations
    from textual.css.errors import DeclarationError
except ImportError as e:
    raise ImportError(f"Failed to import Textual CSS components: {e}")

from ..utils.errors import ValidationError
from ..utils.logging_config import LoggerMixin


@dataclass
class InlineValidationResult:
    """Result of inline CSS validation."""

    valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]


class InlineValidator(LoggerMixin):
    """Validator for inline CSS declarations."""

    def validate(self, style_string: str) -> InlineValidationResult:
        """
        Validate inline style declarations.

        Args:
            style_string: CSS declarations string (e.g., "color: red; margin: 10px;")

        Returns:
            InlineValidationResult with validation results
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        try:
            # Parse declarations using Textual's parser
            declarations = parse_declarations(style_string, ("inline", "0"))

            # Additional validation checks
            self._validate_declarations(declarations, style_string, warnings)

        except DeclarationError as e:
            errors.append(
                ValidationError(
                    message=str(e),
                    line=getattr(e, "line", None),
                    column=getattr(e, "column", None),
                    property_name=getattr(e, "property", None),
                )
            )
        except Exception as e:
            errors.append(ValidationError(f"Failed to parse inline styles: {str(e)}"))

        return InlineValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_declarations(
        self, declarations: Any, original_string: str, warnings: List[ValidationError]
    ) -> None:
        """Perform additional validation on parsed declarations."""
        try:
            # Check for duplicate properties
            seen_properties = set()
            for declaration in declarations:
                prop_name = (
                    str(declaration.name)
                    if hasattr(declaration, "name")
                    else str(declaration)
                )
                if prop_name in seen_properties:
                    warnings.append(
                        ValidationError(
                            f"Duplicate property: {prop_name}", property_name=prop_name
                        )
                    )
                seen_properties.add(prop_name)

            # Check for missing semicolons (basic check)
            if original_string.strip() and not original_string.strip().endswith(";"):
                # Only warn if there are multiple declarations
                if ";" in original_string:
                    warnings.append(
                        ValidationError("Missing semicolon at end of declarations")
                    )

        except Exception as e:
            self.logger.warning(f"Additional inline validation failed: {e}")
