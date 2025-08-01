"""Style introspection utilities for extracting CSS property information from Textual."""

from typing import Dict, Any, List, Optional, Type
import re
from dataclasses import dataclass


@dataclass
class PropertyInfo:
    """Information about a CSS property."""

    name: str
    description: str
    property_type: str
    valid_values: Optional[List[str]] = None
    default_value: Optional[Any] = None
    category: str = "general"
    examples: Optional[List[str]] = None
    related_properties: Optional[List[str]] = None


class StyleIntrospector:
    """Introspects Textual's CSS style properties to extract documentation."""

    def __init__(self) -> None:
        self._properties_cache: Optional[Dict[str, PropertyInfo]] = None
        self._categories = {
            "layout": [
                "display",
                "dock",
                "layers",
                "layer",
                "layout",
                "align",
                "align_horizontal",
                "align_vertical",
                "content_align",
                "content_align_horizontal",
                "content_align_vertical",
            ],
            "sizing": [
                "width",
                "height",
                "min_width",
                "min_height",
                "max_width",
                "max_height",
                "margin",
                "margin_top",
                "margin_right",
                "margin_bottom",
                "margin_left",
                "padding",
                "padding_top",
                "padding_right",
                "padding_bottom",
                "padding_left",
            ],
            "appearance": [
                "background",
                "color",
                "opacity",
                "visibility",
                "text_opacity",
                "scrollbar_background",
                "scrollbar_color",
                "scrollbar_corner_color",
                "scrollbar_gutter",
                "scrollbar_size",
            ],
            "borders": [
                "border",
                "border_top",
                "border_right",
                "border_bottom",
                "border_left",
                "border_title_align",
                "border_title_background",
                "border_title_color",
                "border_title_style",
                "border_subtitle_align",
                "border_subtitle_background",
                "border_subtitle_color",
                "border_subtitle_style",
                "outline",
                "outline_top",
                "outline_right",
                "outline_bottom",
                "outline_left",
            ],
            "text": [
                "text_align",
                "text_style",
                "link_background",
                "link_color",
                "link_hover_background",
                "link_hover_color",
                "link_hover_style",
                "link_style",
            ],
            "overflow": ["overflow", "overflow_x", "overflow_y"],
            "grid": ["grid_columns", "grid_rows", "grid_gutter", "row_span", "column_span"],
            "animation": ["transition_duration", "transition_delay", "transition_easing"],
        }

    def get_all_properties(self) -> Dict[str, PropertyInfo]:
        """Get all CSS properties from Textual's styles module."""
        if self._properties_cache is not None:
            return self._properties_cache

        try:
            # Import the styles module to inspect actual properties
            import textual.css.styles as styles_module
        except ImportError as e:
            raise ImportError(f"Failed to import Textual CSS modules: {e}")

        properties = {}

        # Get the StylesBase class which has the actual property definitions
        StylesBase = getattr(styles_module, "StylesBase", None)
        if StylesBase:
            # Use __dict__ to avoid triggering property getters
            for attr_name, attr_value in StylesBase.__dict__.items():
                if attr_name.startswith("_"):
                    continue

                # Check if it's a property instance by checking its type
                if hasattr(attr_value, "__class__") and "Property" in attr_value.__class__.__name__:
                    try:
                        prop_info = self._extract_property_info(attr_name, attr_value, StylesBase)
                        if prop_info:
                            properties[attr_name] = prop_info
                    except Exception:
                        continue

        self._properties_cache = properties
        return properties

    def _extract_property_info(
        self, name: str, prop: Any, parent_class: Type
    ) -> Optional[PropertyInfo]:
        """Extract information about a specific property."""
        try:
            # Get property type
            prop_type = type(prop).__name__

            # Get docstring
            doc = prop.__doc__ or ""
            description = self._clean_docstring(doc)

            # Extract valid values
            valid_values = self._get_valid_values(prop)

            # Get default value
            default_value = self._get_default_value(prop)

            # Determine category
            category = self._get_category(name)

            # Get examples from docstring
            examples = self._extract_examples(doc)

            # Get related properties
            related = self._get_related_properties(name)

            return PropertyInfo(
                name=name,
                description=description,
                property_type=prop_type,
                valid_values=valid_values,
                default_value=default_value,
                category=category,
                examples=examples,
                related_properties=related,
            )
        except Exception:
            # If we can't extract info, skip this property
            return None

    def _clean_docstring(self, doc: str) -> str:
        """Clean and extract the main description from a docstring."""
        if not doc:
            return "No description available."

        # Remove leading/trailing whitespace
        doc = doc.strip()

        # Take the first paragraph
        paragraphs = doc.split("\n\n")
        if paragraphs:
            first_para = paragraphs[0]
            # Remove extra whitespace
            first_para = " ".join(first_para.split())
            return first_para

        return doc

    def _get_valid_values(self, prop: Any) -> Optional[List[str]]:
        """Extract valid values for a property."""
        # Check for _valid_values attribute
        if hasattr(prop, "_valid_values"):
            return list(prop._valid_values)

        # Check for _enum_class attribute (for StringEnumProperty)
        if hasattr(prop, "_enum_class"):
            enum_class = prop._enum_class
            return [member.value for member in enum_class]

        # Check for specific property types
        prop_type_name = type(prop).__name__

        if prop_type_name == "BooleanProperty":
            return ["true", "false"]
        elif prop_type_name == "ColorProperty":
            return ["<color>", "auto", "transparent"]
        elif prop_type_name == "ScalarProperty":
            return ["<number>", "<percentage>", "auto"]
        elif prop_type_name == "AlignProperty":
            # Composite property for alignment
            return [
                "<horizontal> <vertical>",
                "left top",
                "center middle",
                "right bottom",
                "left",
                "center",
                "right",
                "top",
                "middle",
                "bottom",
            ]
        elif prop_type_name == "SpacingProperty":
            # For margin/padding properties
            return [
                "<length>",
                "<percentage>",
                "auto",
                "<top> <right> <bottom> <left>",
                "<vertical> <horizontal>",
                "<all>",
            ]
        elif prop_type_name == "BorderProperty":
            # For border/outline properties
            return [
                "<border-style>",
                "<color>",
                "<border-style> <color>",
                "none",
                "solid",
                "double",
                "dashed",
                "dotted",
                "round",
                "solid <color>",
                "double <color>",
            ]
        elif prop_type_name == "OverflowProperty":
            return ["visible", "hidden", "scroll", "auto"]
        elif prop_type_name == "StringEnumProperty":
            # Try to get the property name and look up known valid values
            # This handles cases where _valid_values isn't directly available
            if hasattr(prop, "name"):
                name = prop.name
                # Check for known StringEnumProperty values
                if "display" in name:
                    return ["none", "block"]
                elif "visibility" in name:
                    return ["visible", "hidden"]
                elif "dock" in name:
                    return ["top", "right", "bottom", "left"]
                elif "text_align" in name:
                    return ["left", "center", "right", "justify", "start", "end"]
                elif "scrollbar_gutter" in name:
                    return ["auto", "stable"]
        elif prop_type_name == "FractionalProperty":
            # For opacity properties
            return ["<number>", "0.0-1.0"]
        elif prop_type_name == "BoxProperty":
            # For box-sizing
            return ["border-box", "content-box"]
        elif prop_type_name == "LayoutProperty":
            # For layout property
            return ["vertical", "horizontal", "grid"]
        elif prop_type_name == "DockProperty":
            # For dock property
            return ["none", "top", "right", "bottom", "left"]

        return None

    def _get_default_value(self, prop: Any) -> Optional[Any]:
        """Get the default value for a property."""
        if hasattr(prop, "_default"):
            return str(prop._default)
        elif hasattr(prop, "default"):
            return prop.default
        return None

    def _get_category(self, name: str) -> str:
        """Determine the category for a property based on its name."""
        for category, props in self._categories.items():
            if name in props:
                return category

        # Try to guess based on name patterns
        if "margin" in name or "padding" in name or "width" in name or "height" in name:
            return "sizing"
        elif "color" in name or "background" in name or "opacity" in name:
            return "appearance"
        elif "border" in name or "outline" in name:
            return "borders"
        elif "text" in name or "link" in name:
            return "text"
        elif "overflow" in name:
            return "overflow"
        elif "grid" in name or "row" in name or "column" in name:
            return "grid"
        elif "align" in name or "dock" in name or "layer" in name:
            return "layout"

        return "general"

    def _extract_examples(self, doc: str) -> Optional[List[str]]:
        """Extract example usage from docstring."""
        if not doc:
            return None

        examples = []

        # Look for Example: or Examples: sections
        example_pattern = r"Example[s]?:\s*\n(.*?)(?:\n\n|$)"
        matches = re.findall(example_pattern, doc, re.DOTALL | re.IGNORECASE)

        for match in matches:
            # Clean up the example
            example = match.strip()
            if example:
                examples.append(example)

        # Also look for code blocks
        code_pattern = r"```(?:css|tcss)?\n(.*?)\n```"
        code_matches = re.findall(code_pattern, doc, re.DOTALL)

        for match in code_matches:
            examples.append(match.strip())

        return examples if examples else None

    def _get_related_properties(self, name: str) -> Optional[List[str]]:
        """Get related properties based on the property name."""
        related = []

        # Handle composite properties
        if name == "margin":
            related = ["margin_top", "margin_right", "margin_bottom", "margin_left"]
        elif name == "padding":
            related = ["padding_top", "padding_right", "padding_bottom", "padding_left"]
        elif name == "border":
            related = ["border_top", "border_right", "border_bottom", "border_left"]
        elif name == "outline":
            related = ["outline_top", "outline_right", "outline_bottom", "outline_left"]
        elif name in ["margin_top", "margin_right", "margin_bottom", "margin_left"]:
            related = ["margin"]
        elif name in ["padding_top", "padding_right", "padding_bottom", "padding_left"]:
            related = ["padding"]
        elif name in ["border_top", "border_right", "border_bottom", "border_left"]:
            related = ["border", "border_title_color", "border_title_style"]
        elif name in ["align_horizontal", "align_vertical"]:
            related = [
                "align",
                "content_align",
                "content_align_horizontal",
                "content_align_vertical",
            ]
        elif name == "align":
            related = ["align_horizontal", "align_vertical"]
        elif name == "content_align":
            related = ["content_align_horizontal", "content_align_vertical"]
        elif name == "overflow":
            related = ["overflow_x", "overflow_y"]
        elif name in ["overflow_x", "overflow_y"]:
            related = ["overflow"]
        elif "link" in name:
            related = [
                prop
                for prop in [
                    "link_background",
                    "link_color",
                    "link_style",
                    "link_hover_background",
                    "link_hover_color",
                    "link_hover_style",
                ]
                if prop != name
            ]
        elif "scrollbar" in name:
            related = [
                prop
                for prop in [
                    "scrollbar_background",
                    "scrollbar_color",
                    "scrollbar_corner_color",
                    "scrollbar_gutter",
                    "scrollbar_size",
                ]
                if prop != name
            ]

        return related if related else None

    def get_property_info(self, property_name: str) -> Optional[PropertyInfo]:
        """Get information about a specific CSS property."""
        properties = self.get_all_properties()

        # Try exact match first
        if property_name in properties:
            return properties[property_name]

        # Try with underscores replaced by hyphens
        normalized_name = property_name.replace("-", "_")
        if normalized_name in properties:
            return properties[normalized_name]

        return None

    def get_properties_by_category(self) -> Dict[str, List[PropertyInfo]]:
        """Get all properties organized by category."""
        properties = self.get_all_properties()
        categorized: Dict[str, List[PropertyInfo]] = {}

        for prop_info in properties.values():
            category = prop_info.category
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(prop_info)

        # Sort properties within each category
        for category in categorized:
            categorized[category].sort(key=lambda p: p.name)

        return categorized
