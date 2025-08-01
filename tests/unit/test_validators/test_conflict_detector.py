"""Tests for CSS conflict detection system."""

from textual_mcp.validators.conflict_detector import (
    ConflictDetector,
    SelectorOverlapAnalyzer,
    PropertyConflictDetector,
    ConflictResolutionSuggester,
    StyleConflict,
    SelectorOverlap,
    ConflictAnalysisResult,
)


class TestSelectorOverlapAnalyzer:
    """Test cases for selector overlap analysis."""

    def test_exact_overlap(self):
        """Test detection of exact selector matches."""
        analyzer = SelectorOverlapAnalyzer()

        assert analyzer.analyze_overlap("Button", "Button") == "exact"
        assert analyzer.analyze_overlap(".class1", ".class1") == "exact"
        assert analyzer.analyze_overlap("#id1", "#id1") == "exact"

    def test_no_overlap(self):
        """Test selectors with no overlap."""
        analyzer = SelectorOverlapAnalyzer()

        assert analyzer.analyze_overlap("Button", "Label") is None
        assert analyzer.analyze_overlap(".class1", ".class2") is None
        assert analyzer.analyze_overlap("#id1", "#id2") is None

    def test_subset_overlap(self):
        """Test detection of subset relationships."""
        analyzer = SelectorOverlapAnalyzer()

        # Button is a subset of Button.active
        result = analyzer.analyze_overlap("Button", "Button.active")
        assert result == "subset"

        # .class1 is a subset of Button.class1
        result = analyzer.analyze_overlap(".class1", "Button.class1")
        assert result == "subset"

    def test_partial_overlap(self):
        """Test detection of partial overlaps."""
        analyzer = SelectorOverlapAnalyzer()

        # Both target Button elements
        result = analyzer.analyze_overlap("Button.primary", "Button.secondary")
        assert result == "partial"

        # Same ID means they overlap
        result = analyzer.analyze_overlap("#main.active", "#main.inactive")
        assert result == "partial"

    def test_specificity_calculation(self):
        """Test CSS specificity calculation."""
        analyzer = SelectorOverlapAnalyzer()

        # Test ID specificity
        assert analyzer._calculate_specificity("#id") == (1, 0, 0)

        # Test class specificity
        assert analyzer._calculate_specificity(".class") == (0, 1, 0)

        # Test type specificity
        assert analyzer._calculate_specificity("Button") == (0, 0, 1)

        # Test combined specificity
        assert analyzer._calculate_specificity("#id.class") == (1, 1, 0)
        assert analyzer._calculate_specificity("Button.class") == (0, 1, 1)
        assert analyzer._calculate_specificity("Button#id.class") == (1, 1, 1)

        # Test pseudo-classes
        assert analyzer._calculate_specificity("Button:hover") == (0, 1, 1)
        assert analyzer._calculate_specificity("Button:hover:focus") == (0, 2, 1)

    def test_find_overlapping_groups(self):
        """Test finding groups of overlapping selectors."""
        analyzer = SelectorOverlapAnalyzer()

        selectors = [
            "Button",
            "Button.primary",
            "Button.secondary",
            "Label",
            "Label.title",
            "#unique-id",
        ]

        groups = analyzer.find_overlapping_groups(selectors)

        # Should find Button group and Label group
        assert len(groups) >= 2

        # Check Button group
        button_group = next((g for g in groups if "Button" in g.selectors), None)
        assert button_group is not None
        assert set(button_group.selectors) >= {"Button", "Button.primary", "Button.secondary"}

        # Check Label group
        label_group = next((g for g in groups if "Label" in g.selectors), None)
        assert label_group is not None
        assert set(label_group.selectors) >= {"Label", "Label.title"}


class TestPropertyConflictDetector:
    """Test cases for property conflict detection."""

    def test_direct_property_conflicts(self):
        """Test detection of direct property conflicts."""
        detector = PropertyConflictDetector()

        rule1 = {
            "properties": {
                "color": "red",
                "background": "blue",
                "margin": "1 2",
            }
        }

        rule2 = {
            "properties": {
                "color": "green",  # Conflicts
                "background": "blue",  # Same value, no conflict
                "padding": "2 4",  # Different property
            }
        }

        conflicts = detector.detect_conflicts(rule1, rule2)
        assert "color" in conflicts
        assert "background" not in conflicts
        assert "padding" not in conflicts

    def test_shorthand_longhand_conflicts(self):
        """Test detection of shorthand vs longhand conflicts."""
        detector = PropertyConflictDetector()

        rule1 = {
            "properties": {
                "margin": "1 2 3 4",
            }
        }

        rule2 = {
            "properties": {
                "margin-top": "5",
                "margin-left": "6",
            }
        }

        conflicts = detector.detect_conflicts(rule1, rule2)
        assert "margin-top" in conflicts
        assert "margin-left" in conflicts

    def test_property_expansion(self):
        """Test expansion of shorthand properties."""
        detector = PropertyConflictDetector()

        props = {
            "margin": "1 2",
            "border": "solid red",
        }

        expanded = detector._expand_properties(props)

        # Check margin expansion
        assert "margin-top" in expanded
        assert "margin-right" in expanded
        assert "margin-bottom" in expanded
        assert "margin-left" in expanded

        # Check border expansion
        assert "border-width" in expanded
        assert "border-style" in expanded
        assert "border-color" in expanded

    def test_categorize_conflicts(self):
        """Test categorization of conflicts by property group."""
        detector = PropertyConflictDetector()

        conflicts = [
            "margin",
            "margin-top",
            "padding",
            "color",
            "background",
            "width",
            "height",
            "dock",
            "unknown-property",
        ]

        categorized = detector.categorize_conflicts(conflicts)

        assert "spacing" in categorized
        assert set(categorized["spacing"]) >= {"margin", "margin-top", "padding"}

        assert "colors" in categorized
        assert set(categorized["colors"]) >= {"color", "background"}

        assert "sizing" in categorized
        assert set(categorized["sizing"]) >= {"width", "height"}

        assert "positioning" in categorized
        assert "dock" in categorized["positioning"]

        assert "other" in categorized
        assert "unknown-property" in categorized["other"]


class TestConflictResolutionSuggester:
    """Test cases for conflict resolution suggestions."""

    def test_equal_specificity_suggestion(self):
        """Test suggestions for equal specificity conflicts."""
        suggester = ConflictResolutionSuggester()

        conflict = StyleConflict(
            selector1=".class1",
            selector2=".class2",
            conflicting_properties=["color"],
            specificity1=(0, 1, 0),
            specificity2=(0, 1, 0),
        )

        suggestion = suggester.suggest_resolution(conflict)
        assert "equal specificity" in suggestion.lower()

    def test_high_specificity_suggestion(self):
        """Test suggestions for high specificity selectors."""
        suggester = ConflictResolutionSuggester()

        conflict = StyleConflict(
            selector1="#id1.class1.class2",
            selector2=".simple",
            conflicting_properties=["color"],
            specificity1=(1, 2, 0),  # High specificity
            specificity2=(0, 1, 0),
        )

        suggestion = suggester.suggest_resolution(conflict)
        assert "higher specificity" in suggestion.lower()

    def test_multiple_conflicts_suggestion(self):
        """Test suggestions for multiple property conflicts."""
        suggester = ConflictResolutionSuggester()

        conflict = StyleConflict(
            selector1="Button",
            selector2="Button.primary",
            conflicting_properties=["color", "background", "border", "margin", "padding"],
            specificity1=(0, 0, 1),
            specificity2=(0, 1, 1),
        )

        suggestion = suggester.suggest_resolution(conflict)
        assert (
            "multiple properties" in suggestion.lower() or "shared base class" in suggestion.lower()
        )

    def test_id_conflict_suggestion(self):
        """Test suggestions for ID selector conflicts."""
        suggester = ConflictResolutionSuggester()

        conflict = StyleConflict(
            selector1="#id1",
            selector2="#id2",
            conflicting_properties=["color"],
            specificity1=(1, 0, 0),
            specificity2=(1, 0, 0),
        )

        suggestion = suggester.suggest_resolution(conflict)
        assert "IDs" in suggestion or "unique" in suggestion.lower()

    def test_selector_improvement_suggestions(self):
        """Test suggestions for selector improvements."""
        suggester = ConflictResolutionSuggester()

        # Test exact duplicate suggestion
        overlap = SelectorOverlap(
            selectors=["Button", "Button"],
            overlap_type="exact",
            specificity_scores=[(0, 0, 1), (0, 0, 1)],
        )

        suggestions = suggester.suggest_selector_improvements(overlap)
        assert any("duplicate" in s.lower() for s in suggestions)

        # Test high specificity suggestion
        overlap = SelectorOverlap(
            selectors=["#id1.class1.class2.class3"],
            overlap_type="exact",
            specificity_scores=[(1, 3, 0)],
        )

        suggestions = suggester.suggest_selector_improvements(overlap)
        assert any("high specificity" in s.lower() for s in suggestions)


class TestConflictDetector:
    """Test cases for the main ConflictDetector."""

    def test_analyze_simple_conflicts(self):
        """Test analysis of simple CSS conflicts."""
        detector = ConflictDetector()

        css = """
        Button {
            color: red;
            background: blue;
        }

        Button {
            color: green;
            background: yellow;
        }
        """

        result = detector.analyze_conflicts(css)

        assert isinstance(result, ConflictAnalysisResult)
        assert len(result.conflicts) > 0
        assert len(result.overlapping_selectors) > 0

        # Check that Button selector overlap was detected
        button_overlap = next(
            (o for o in result.overlapping_selectors if "Button" in o.selectors), None
        )
        assert button_overlap is not None
        assert button_overlap.overlap_type == "exact"

    def test_analyze_complex_conflicts(self):
        """Test analysis of complex CSS with multiple conflict types."""
        detector = ConflictDetector()

        css = """
        /* Base button styles */
        Button {
            color: $text;
            background: $primary;
            margin: 1 2;
            padding: 1;
        }

        /* Primary button override */
        Button.primary {
            color: white;
            background: blue;
            margin-top: 2;
        }

        /* Another button style that conflicts */
        Button {
            padding: 2 3;
            border: solid red;
        }

        /* High specificity selector */
        #main Button.primary {
            color: black;
            margin: 0;
        }
        """

        result = detector.analyze_conflicts(css)

        # Should detect multiple conflicts
        assert len(result.conflicts) > 0
        assert len(result.overlapping_selectors) > 0

        # Should detect specificity issues
        assert len(result.specificity_issues) > 0

        # Should have resolution suggestions
        assert len(result.resolution_suggestions) > 0

        # Should categorize property conflicts
        assert len(result.property_conflicts) > 0

    def test_analyze_no_conflicts(self):
        """Test analysis when there are no conflicts."""
        detector = ConflictDetector()

        css = """
        Button {
            color: red;
        }

        Label {
            color: blue;
        }

        Input {
            background: white;
        }
        """

        result = detector.analyze_conflicts(css)

        assert len(result.conflicts) == 0
        assert len(result.overlapping_selectors) == 0

    def test_analyze_textual_specific_css(self):
        """Test analysis with Textual-specific CSS properties."""
        detector = ConflictDetector()

        css = """
        Screen {
            dock: top;
            layer: overlay;
        }

        Screen {
            dock: bottom;
            layer: base;
        }

        Button {
            tint: $primary 50%;
            offset: 1 2;
        }

        Button.primary {
            tint: $accent 75%;
            offset-x: 3;
        }
        """

        result = detector.analyze_conflicts(css)

        # Should detect conflicts in Textual-specific properties
        assert len(result.conflicts) > 0

        # Check that dock and layer conflicts are detected
        screen_conflicts = [c for c in result.conflicts if "Screen" in c.selector1]
        assert len(screen_conflicts) > 0
        assert any("dock" in c.conflicting_properties for c in screen_conflicts)
        assert any("layer" in c.conflicting_properties for c in screen_conflicts)

    def test_empty_css_handling(self):
        """Test handling of empty CSS content."""
        detector = ConflictDetector()

        result = detector.analyze_conflicts("")

        assert isinstance(result, ConflictAnalysisResult)
        assert len(result.conflicts) == 0
        assert len(result.overlapping_selectors) == 0
        assert result.summary.get("has_issues") is False

    def test_invalid_css_handling(self):
        """Test handling of invalid CSS content."""
        detector = ConflictDetector()

        # This should not crash, but might not detect conflicts
        invalid_css = """
        Button {
            color: ;
            background:
        }
        """

        result = detector.analyze_conflicts(invalid_css)
        assert isinstance(result, ConflictAnalysisResult)

    def test_pseudo_class_conflicts(self):
        """Test detection of conflicts with pseudo-classes."""
        detector = ConflictDetector()

        css = """
        Button:hover {
            background: red;
            color: white;
        }

        Button:hover {
            background: blue;
            border: solid white;
        }

        Button:focus {
            background: green;
        }
        """

        result = detector.analyze_conflicts(css)

        # Should detect hover conflicts
        hover_conflicts = [
            c for c in result.conflicts if ":hover" in c.selector1 and ":hover" in c.selector2
        ]
        assert len(hover_conflicts) > 0
        assert any("background" in c.conflicting_properties for c in hover_conflicts)

    def test_complex_selector_analysis(self):
        """Test analysis of complex nested selectors."""
        detector = ConflictDetector()

        css = """
        #main .container Button.primary {
            color: red;
            margin: 1;
        }

        #main Button.primary {
            color: blue;
            padding: 2;
        }

        .container Button.primary {
            color: green;
            margin: 2;
        }
        """

        result = detector.analyze_conflicts(css)

        # Should detect partial overlaps
        assert len(result.overlapping_selectors) > 0

        # Should identify high specificity issues
        high_spec_issues = [issue for issue in result.specificity_issues if issue["score"] >= 3]
        assert len(high_spec_issues) > 0
