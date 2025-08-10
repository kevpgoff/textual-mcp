"""CSS property and value validator for Textual stylesheets."""

import re
from typing import List, Optional
from dataclasses import dataclass

from ..utils.logging_config import LoggerMixin


@dataclass
class PropertyValidationError:
    """Represents a property validation error."""

    property_name: str
    value: str
    message: str
    line: Optional[int] = None
    column: Optional[int] = None


class TextualPropertyValidator(LoggerMixin):
    """Validates CSS properties and values according to Textual's rules."""

    def __init__(self):
        # Define valid Textual CSS properties
        # Based on Textual's documentation and source code
        self.valid_properties = {
            # Layout properties
            "display",
            "layout",
            "dock",
            "layer",
            "layers",
            "align",
            "align-horizontal",
            "align-vertical",
            "content-align",
            "content-align-horizontal",
            "content-align-vertical",
            # Size properties
            "width",
            "height",
            "min-width",
            "min-height",
            "max-width",
            "max-height",
            # Spacing properties
            "margin",
            "margin-top",
            "margin-right",
            "margin-bottom",
            "margin-left",
            "padding",
            "padding-top",
            "padding-right",
            "padding-bottom",
            "padding-left",
            # Position properties
            "offset",
            "offset-x",
            "offset-y",
            # Border properties
            "border",
            "border-top",
            "border-right",
            "border-bottom",
            "border-left",
            "border-title-align",
            "border-subtitle-align",
            # Text properties
            "text-align",
            "text-style",
            "text-opacity",
            # Color properties
            "color",
            "background",
            "tint",
            "link-color",
            "link-background",
            "link-style",
            "link-hover-color",
            "link-hover-background",
            "link-hover-style",
            # Scrollbar properties
            "scrollbar-color",
            "scrollbar-color-hover",
            "scrollbar-color-active",
            "scrollbar-background",
            "scrollbar-background-hover",
            "scrollbar-background-active",
            "scrollbar-size",
            "scrollbar-size-horizontal",
            "scrollbar-size-vertical",
            "scrollbar-corner-color",
            # Grid properties
            "grid-size",
            "grid-columns",
            "grid-rows",
            "grid-gutter",
            "row-span",
            "column-span",
            # Overflow properties
            "overflow",
            "overflow-x",
            "overflow-y",
            # Visibility
            "visibility",
            "opacity",
            # Box model
            "box-sizing",
            # Outline
            "outline",
            "outline-top",
            "outline-right",
            "outline-bottom",
            "outline-left",
            # Keyline
            "keyline",
            # Hatch
            "hatch",
        }

        # Properties that require integer values (no units or percentages)
        self.integer_only_properties = {
            "margin",
            "margin-top",
            "margin-right",
            "margin-bottom",
            "margin-left",
            "padding",
            "padding-top",
            "padding-right",
            "padding-bottom",
            "padding-left",
            "offset-x",
            "offset-y",
            "grid-gutter",
            "row-span",
            "column-span",
            "scrollbar-size",
            "scrollbar-size-horizontal",
            "scrollbar-size-vertical",
        }

        # Properties that accept percentages
        self.percentage_properties = {
            "width",
            "height",
            "min-width",
            "min-height",
            "max-width",
            "max-height",
            "opacity",
            "text-opacity",
        }

        # Properties that accept fr units (fractional units for grid)
        self.fr_properties = {
            "width",
            "height",
            "min-width",
            "min-height",
            "max-width",
            "max-height",
            "grid-columns",
            "grid-rows",
        }

        # Properties that accept specific keywords
        self.keyword_properties = {
            "display": {"block", "none"},
            "visibility": {"visible", "hidden"},
            "overflow": {"scroll", "hidden", "auto"},
            "overflow-x": {"scroll", "hidden", "auto"},
            "overflow-y": {"scroll", "hidden", "auto"},
            "dock": {"top", "right", "bottom", "left"},
            "align": {"left", "center", "right"},
            "align-horizontal": {"left", "center", "right"},
            "align-vertical": {"top", "middle", "bottom"},
            "content-align": {"left", "center", "right", "top", "middle", "bottom"},
            "content-align-horizontal": {"left", "center", "right"},
            "content-align-vertical": {"top", "middle", "bottom"},
            "text-align": {"left", "center", "right", "justify"},
            "text-style": {"bold", "italic", "reverse", "strike", "underline", "none"},
            "border": {
                "solid",
                "double",
                "round",
                "ascii",
                "none",
                "hidden",
                "blank",
                "heavy",
                "thick",
                "panel",
                "tall",
                "wide",
            },
            "border-title-align": {"left", "center", "right"},
            "border-subtitle-align": {"left", "center", "right"},
            "box-sizing": {"border-box", "content-box"},
            "layout": {"horizontal", "vertical", "grid"},
        }

    def validate_property(
        self, property_name: str, value: str, line: Optional[int] = None
    ) -> Optional[PropertyValidationError]:
        """
        Validate a CSS property and its value.

        Args:
            property_name: Name of the CSS property
            value: Value of the CSS property
            line: Optional line number for error reporting

        Returns:
            PropertyValidationError if validation fails, None if valid
        """
        # Check if property is valid for Textual
        if property_name not in self.valid_properties:
            # Special case: 'gap' is not a valid Textual property
            # (it might be confused with 'grid-gutter' or spacing properties)
            if property_name == "gap":
                return PropertyValidationError(
                    property_name=property_name,
                    value=value,
                    message=f"Invalid CSS property '{property_name}'",
                    line=line,
                )
            return PropertyValidationError(
                property_name=property_name,
                value=value,
                message=f"Unknown CSS property '{property_name}'",
                line=line,
            )

        # Validate the value based on property type
        return self._validate_value(property_name, value, line)

    def _validate_value(
        self, property_name: str, value: str, line: Optional[int] = None
    ) -> Optional[PropertyValidationError]:
        """Validate the value for a specific property."""
        value = value.strip()

        # Check keyword properties
        if property_name in self.keyword_properties:
            valid_keywords = self.keyword_properties[property_name]
            # Some properties accept multiple keywords
            if property_name == "text-style":
                # text-style can have multiple values
                styles = value.split()
                for style in styles:
                    if style not in valid_keywords:
                        return PropertyValidationError(
                            property_name=property_name,
                            value=value,
                            message=f"Invalid value '{style}' for {property_name}. Valid values: {', '.join(valid_keywords)}",
                            line=line,
                        )
            elif value not in valid_keywords and not self._is_css_variable(value):
                # Single keyword check
                if not any(self._matches_pattern(value, kw) for kw in valid_keywords):
                    return PropertyValidationError(
                        property_name=property_name,
                        value=value,
                        message=f"Invalid value for {property_name}. Valid values: {', '.join(valid_keywords)}",
                        line=line,
                    )

        # Check integer-only properties
        if property_name in self.integer_only_properties:
            error = self._validate_integer_value(property_name, value)
            if error:
                error.line = line
                return error

        # Check margin/padding special rules
        if property_name in ["margin", "padding"]:
            error = self._validate_spacing_value(property_name, value)
            if error:
                error.line = line
                return error

        # Check width/height values
        if property_name in [
            "width",
            "height",
            "min-width",
            "min-height",
            "max-width",
            "max-height",
        ]:
            error = self._validate_dimension_value(property_name, value)
            if error:
                error.line = line
                return error

        # Check color values
        if "color" in property_name or property_name in ["background", "tint"]:
            error = self._validate_color_value(property_name, value)
            if error:
                error.line = line
                return error

        return None

    def _validate_integer_value(
        self, property_name: str, value: str
    ) -> Optional[PropertyValidationError]:
        """Validate that a value is an integer or valid integer expression."""
        # Check for CSS variables
        if self._is_css_variable(value):
            return None

        # Check for auto keyword
        if value == "auto":
            return None

        # Split value into parts (for shorthand properties)
        parts = value.split()

        for part in parts:
            # Check if it's a valid integer
            if not self._is_valid_integer(part):
                return PropertyValidationError(
                    property_name=property_name,
                    value=value,
                    message=f"Invalid value for {property_name}. Expected integer value(s), got '{part}'",
                )

        return None

    def _validate_spacing_value(
        self, property_name: str, value: str
    ) -> Optional[PropertyValidationError]:
        """Validate margin/padding values according to Textual rules."""
        if self._is_css_variable(value):
            return None

        parts = value.split()

        # Check that we have 1, 2, or 4 parts
        if len(parts) not in [1, 2, 4]:
            return PropertyValidationError(
                property_name=property_name,
                value=value,
                message=f"Invalid value for the {property_name} property\n"
                f"└── Supply 1, 2 or 4 integers separated by a space\n"
                f"      e.g. {property_name}: 1;\n"
                f"      e.g. {property_name}: 1 2;     # Vertical, horizontal\n"
                f"      e.g. {property_name}: 1 2 3 4; # Top, right, bottom, left",
            )

        # Check each part is a valid integer (no percentages allowed in margin/padding)
        for part in parts:
            if not self._is_valid_integer(part):
                return PropertyValidationError(
                    property_name=property_name,
                    value=value,
                    message=f"Invalid value for the {property_name} property",
                )

        return None

    def _validate_dimension_value(
        self, property_name: str, value: str
    ) -> Optional[PropertyValidationError]:
        """Validate width/height dimension values."""
        if self._is_css_variable(value):
            return None

        # Check for valid keywords
        if value in ["auto", "1fr", "100%", "100vh", "100vw"]:
            return None

        # Check for percentage
        if value.endswith("%"):
            try:
                float(value[:-1])
                return None
            except ValueError:
                pass

        # Check for fr units
        if value.endswith("fr"):
            try:
                float(value[:-2])
                return None
            except ValueError:
                pass

        # Check for viewport units
        if value.endswith(("vh", "vw", "vmin", "vmax")):
            try:
                float(value[:-2])
                return None
            except ValueError:
                pass

        # Check for integer
        if self._is_valid_integer(value):
            return None

        return PropertyValidationError(
            property_name=property_name,
            value=value,
            message=f"Invalid value '{value}' for {property_name}. Expected integer, percentage, fr units, or 'auto'.",
        )

    def _validate_color_value(
        self, property_name: str, value: str
    ) -> Optional[PropertyValidationError]:
        """Validate color values."""
        if self._is_css_variable(value):
            return None

        # Check for transparent
        if value in ["transparent", "auto"]:
            return None

        # Check for hex color
        if re.match(r"^#[0-9a-fA-F]{3}$|^#[0-9a-fA-F]{6}$|^#[0-9a-fA-F]{8}$", value):
            return None

        # Check for rgb/rgba
        if re.match(r"^rgba?\([^)]+\)$", value):
            return None

        # Check for hsl/hsla
        if re.match(r"^hsla?\([^)]+\)$", value):
            return None

        # Check for color names (basic set)
        color_names = {
            "black",
            "white",
            "red",
            "green",
            "blue",
            "yellow",
            "cyan",
            "magenta",
            "gray",
            "grey",
            "orange",
            "purple",
            "brown",
            "pink",
            "lime",
            "olive",
            "navy",
            "teal",
            "silver",
            "maroon",
            "aqua",
            "fuchsia",
        }
        if value.lower() in color_names:
            return None

        # Check for ANSI color names used by Textual
        if re.match(
            r"^ansi_(default|black|red|green|yellow|blue|magenta|cyan|white)(_dim)?$", value
        ):
            return None

        if re.match(r"^ansi_bright_(black|red|green|yellow|blue|magenta|cyan|white)$", value):
            return None

        # If none of the above, it's invalid
        return PropertyValidationError(
            property_name=property_name,
            value=value,
            message=f"Invalid color value '{value}' for {property_name}",
        )

    def _is_css_variable(self, value: str) -> bool:
        """Check if value is a CSS variable reference."""
        return value.startswith("$") or value.startswith("var(")

    def _is_valid_integer(self, value: str) -> bool:
        """Check if value is a valid integer."""
        try:
            int(value)
            return True
        except ValueError:
            return False

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if value matches a pattern (for keyword matching)."""
        return value == pattern

    def validate_css_content(self, css_content: str) -> List[PropertyValidationError]:
        """
        Validate all properties in CSS content.

        Args:
            css_content: The CSS content to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Simple regex-based extraction of properties
        # This is a simplified approach - in production, you'd use the parsed AST
        lines = css_content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments and empty lines
            line = line.strip()
            if not line or line.startswith("/*") or line.startswith("//"):
                continue

            # Look for property declarations
            # First remove comments from the line
            if "/*" in line:
                line = line[: line.index("/*")]

            match = re.match(r"^\s*([a-z-]+)\s*:\s*(.+?)\s*;?\s*$", line)
            if match:
                property_name = match.group(1)
                # Remove trailing semicolon and any whitespace
                value = match.group(2).rstrip(";").strip()

                error = self.validate_property(property_name, value, line_num)
                if error:
                    errors.append(error)

        return errors
