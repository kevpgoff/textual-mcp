"""CSS selector validator using Textual's parse_selectors."""

from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass

try:
    from textual.css.parse import parse_selectors
    from textual.css.errors import StylesheetError
except ImportError as e:
    raise ImportError(f"Failed to import Textual CSS components: {e}")

from ..utils.logging_config import LoggerMixin


@dataclass
class SelectorValidationResult:
    """Result of selector validation."""

    valid: bool
    error: Optional[str]
    selector_type: str
    specificity: Tuple[int, int, int]  # (id, class, type)


class SelectorValidator(LoggerMixin):
    """Validator for CSS selectors."""

    def validate_selector(self, selector: str) -> SelectorValidationResult:
        """
        Validate a single CSS selector.

        Args:
            selector: CSS selector string

        Returns:
            SelectorValidationResult with validation results
        """
        try:
            # Check for unsupported combinators first
            if ">" in selector or "+" in selector or "~" in selector:
                return SelectorValidationResult(
                    valid=False,
                    error="Textual does not support child (>), adjacent sibling (+), or general sibling (~) combinators",
                    selector_type="combinator",
                    specificity=(0, 0, 0),
                )

            # Parse selector using Textual's parser
            selectors = parse_selectors(selector)

            if not selectors:
                return SelectorValidationResult(
                    valid=False,
                    error="Empty selector",
                    selector_type="unknown",
                    specificity=(0, 0, 0),
                )

            # Use the first selector for analysis
            selectors[0]
            selector_type = self._determine_selector_type(selector)

            # For type selectors, validate case (Textual expects PascalCase for widgets)
            if selector_type == "type":
                # Check if it's a lowercase widget name
                if selector.islower() or selector.isupper():
                    return SelectorValidationResult(
                        valid=False,
                        error="Textual widget selectors must use PascalCase (e.g., 'Button' not 'button')",
                        selector_type=selector_type,
                        specificity=(0, 0, 0),
                    )

            specificity = self._calculate_specificity(selector)

            return SelectorValidationResult(
                valid=True,
                error=None,
                selector_type=selector_type,
                specificity=specificity,
            )

        except StylesheetError as e:
            return SelectorValidationResult(
                valid=False,
                error=str(e),
                selector_type="unknown",
                specificity=(0, 0, 0),
            )
        except Exception as e:
            return SelectorValidationResult(
                valid=False,
                error=f"Failed to parse selector: {str(e)}",
                selector_type="unknown",
                specificity=(0, 0, 0),
            )

    def validate_selectors(self, selectors: List[str]) -> List[SelectorValidationResult]:
        """Validate multiple selectors."""
        return [self.validate_selector(selector) for selector in selectors]

    def _determine_selector_type(self, selector: str) -> str:
        """Determine the type of CSS selector."""
        selector = selector.strip()

        # Check for combinators first (they can contain other selectors)
        if ">" in selector or "+" in selector or "~" in selector:
            return "combinator"
        elif " " in selector:
            return "descendant"
        # Check for pseudo elements/classes (can be combined with type selectors)
        elif "::" in selector:
            return "pseudo-element"
        elif ":" in selector:
            return "pseudo-class"
        # Check for specific selector types
        elif selector.startswith("#"):
            return "id"
        elif selector.startswith("."):
            return "class"
        elif selector.startswith("["):
            return "attribute"
        else:
            return "type"

    def _calculate_specificity(self, selector: str) -> Tuple[int, int, int]:
        """
        Calculate CSS selector specificity.

        Returns tuple of (id_count, class_count, type_count)
        """
        try:
            # Count IDs
            id_count = selector.count("#")

            # Count classes, attributes, and pseudo-classes
            class_count = (
                selector.count(".")
                + selector.count("[")
                + selector.count(":")
                - selector.count("::")  # Pseudo-elements don't count as classes
            )

            # Count type selectors (simplified approach)
            # Remove special characters and count remaining words
            cleaned = selector
            for char in ["#", ".", "[", "]", ":", ">", "+", "~", "(", ")"]:
                cleaned = cleaned.replace(char, " ")

            words = [word.strip() for word in cleaned.split() if word.strip()]
            # Filter out pseudo-class/element names and attribute values
            type_words = [
                word
                for word in words
                if not word.startswith(("hover", "focus", "active", "visited", "before", "after"))
                and not word.isdigit()
                and len(word) > 0
            ]

            type_count = len(type_words)

            # Textual always adds 1 for type count if selector is valid
            if id_count > 0 or class_count > 0 or type_count > 0:
                type_count = max(1, type_count)

            return (id_count, max(0, class_count), max(0, type_count))

        except Exception as e:
            self.logger.warning(f"Failed to calculate specificity for '{selector}': {e}")
            return (0, 0, 0)

    def analyze_selector_complexity(self, selector: str) -> Dict[str, Any]:
        """Analyze selector complexity and provide recommendations."""
        result = self.validate_selector(selector)

        analysis: Dict[str, Any] = {
            "valid": result.valid,
            "type": result.selector_type,
            "specificity": result.specificity,
            "specificity_score": sum(result.specificity),
            "recommendations": [],
        }

        if result.valid:
            # Analyze complexity
            specificity_score = sum(result.specificity)

            if result.specificity[0] > 1:  # Multiple IDs
                recommendations = analysis.get("recommendations", [])
                if isinstance(recommendations, list):
                    recommendations.append("Avoid using multiple IDs in a single selector")

            if specificity_score > 10:
                recommendations = analysis.get("recommendations", [])
                if isinstance(recommendations, list):
                    recommendations.append("Selector is very specific, consider simplifying")
            elif specificity_score > 5:
                recommendations = analysis.get("recommendations", [])
                if isinstance(recommendations, list):
                    recommendations.append(
                        "Selector has high specificity, consider using classes instead"
                    )

            # Check for overly long selectors
            parts = selector.split()
            if len(parts) > 4:
                recommendations = analysis.get("recommendations", [])
                if isinstance(recommendations, list):
                    recommendations.append(
                        "Selector is quite long, consider using more specific classes"
                    )

            # Check for universal selector
            if "*" in selector:
                recommendations = analysis.get("recommendations", [])
                if isinstance(recommendations, list):
                    recommendations.append("Universal selector (*) can impact performance")

        return analysis
