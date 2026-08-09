"""Pathological-input tests for Layer 1 analyzers.

Every analyzer must be total over DataFrames: constant columns, all-missing
values, tiny samples, infinities, and mixed dtypes must never raise and must
never emit non-finite metrics.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy.stats import pointbiserialr, spearmanr

from auditlens.core.analyzers.class_distribution import analyze_class_distribution
from auditlens.core.analyzers.correlations import (
    _bin_numeric,
    _clean_pair,
    _cramers_v,
    _point_biserial,
    analyze_sensitive_correlations,
)
from auditlens.core.analyzers.missing_values import analyze_missing_values_by_group
from auditlens.core.analyzers.subgroup_analysis import (
    _resolve_positive_class,
    analyze_subgroup_label_distribution,
)


def _assert_finite_metrics(issues: list[dict]) -> None:
    for issue in issues:
        for value in issue["metrics"].values():
            if isinstance(value, float) and not math.isfinite(value):
                raise AssertionError(f"non-finite metric in {issue['issue_id']}: {value}")


# --- class distribution ---


class TestClassDistributionEdgeCases:
    @pytest.mark.parametrize(
        "df",
        [
            pd.DataFrame({"t": pd.Series([], dtype=int)}),
            pd.DataFrame({"t": pd.Series([], dtype=str)}),
        ],
    )
    def test_empty_target_yields_no_issues(self, df: pd.DataFrame) -> None:
        assert analyze_class_distribution(df, "t") == []

    def test_all_missing_target_is_single_class(self) -> None:
        df = pd.DataFrame({"t": [None, None, None]})
        issues = analyze_class_distribution(df, "t")
        assert len(issues) == 1
        assert issues[0]["severity"] == "high"
        assert "one class" in issues[0]["description"]
        assert issues[0]["metrics"]["imbalance_ratio"] == float("inf")

    def test_single_class_is_high_with_inf_ratio(self) -> None:
        df = pd.DataFrame({"t": ["x"] * 5})
        issues = analyze_class_distribution(df, "t")
        assert len(issues) == 1
        assert issues[0]["severity"] == "high"
        assert issues[0]["metrics"]["gini_impurity"] == 0.0

    @pytest.mark.parametrize(
        ("counts", "expected_severity"),
        [
            ([60, 40], "low"),
            ([70, 30], "medium"),
            ([90, 10], "high"),
        ],
    )
    def test_binary_imbalance_severity_boundaries(
        self, counts: list[int], expected_severity: str
    ) -> None:
        values = [0] * counts[0] + [1] * counts[1]
        issues = analyze_class_distribution(pd.DataFrame({"t": values}), "t")
        if expected_severity == "low":
            assert issues == []
        else:
            assert issues[0]["severity"] == expected_severity
            _assert_finite_metrics(issues)

    @pytest.mark.parametrize(
        ("counts", "expected_severity"),
        [
            ([95, 4, 1], "high"),
            ([91, 5, 4], "high"),
            ([90, 6, 4], "high"),
            ([85, 10, 5], "medium"),
            ([80, 10, 10], "low"),
        ],
    )
    def test_multiclass_min_representation_severity(
        self, counts: list[int], expected_severity: str
    ) -> None:
        values = [f"c{i}" for i, n in enumerate(counts) for _ in range(n)]
        issues = analyze_class_distribution(pd.DataFrame({"t": values}), "t")
        if expected_severity == "low":
            assert issues == []
        else:
            assert issues[0]["severity"] == expected_severity

    def test_nan_target_merged_into_missing_class(self) -> None:
        df = pd.DataFrame({"t": [0] * 9 + [1] * 1 + [None] * 2})
        issues = analyze_class_distribution(df, "t")
        metrics = issues[0]["metrics"]
        assert "__MISSING__" in metrics["class_counts"]
        assert metrics["class_counts"]["__MISSING__"] == 2

    def test_unicode_labels_are_safe(self) -> None:
        df = pd.DataFrame({"t": ["α"] * 9 + ["β"] * 1})
        issues = analyze_class_distribution(df, "t")
        assert issues[0]["metrics"]["majority_class"] == "α"

    def test_mixed_type_labels_are_stringified(self) -> None:
        df = pd.DataFrame({"t": [0, 0, 0, "0", 1, 1]})
        issues = analyze_class_distribution(df, "t")
        # "0" and 0 are distinct after normalization, so this is 3 classes.
        counts = issues[0]["metrics"]["class_counts"]
        assert set(counts) == {"0", "1"}

    def test_ratio_is_exact_for_small_integers(self) -> None:
        issues = analyze_class_distribution(pd.DataFrame({"t": [0] * 3 + [1] * 1}), "t")
        assert issues[0]["metrics"]["imbalance_ratio"] == 3.0


# --- correlations ---


class TestCorrelationEdgeCases:
    def test_constant_numeric_target_with_binary_sensitive(self) -> None:
        df = pd.DataFrame({"s": ["A"] * 6 + ["B"] * 6, "t": [1.0] * 12})
        assert analyze_sensitive_correlations(df, "t", ["s"]) == []

    def test_constant_numeric_target_with_multiclass_sensitive(self) -> None:
        df = pd.DataFrame({"s": ["A"] * 4 + ["B"] * 4 + ["C"] * 4, "t": [1.0] * 12})
        assert analyze_sensitive_correlations(df, "t", ["s"]) == []

    def test_inf_values_do_not_crash_qcut(self) -> None:
        df = pd.DataFrame(
            {"s": ["A"] * 10 + ["B"] * 10, "t": [1.0, 2.0, np.inf, 4.0, 5.0] * 4}
        )
        issues = analyze_sensitive_correlations(df, "t", ["s"])
        _assert_finite_metrics(issues)

    def test_inf_in_sensitive_column_is_dropped_not_crashed(self) -> None:
        df = pd.DataFrame({"s": [np.inf] * 6 + [1.0, 2.0, 3.0, 4.0] * 3, "t": list(range(18))})
        issues = analyze_sensitive_correlations(df, "t", ["s"])
        _assert_finite_metrics(issues)

    @pytest.mark.parametrize("rows", [0, 1])
    def test_too_few_clean_rows_are_skipped(self, rows: int) -> None:
        df = pd.DataFrame({"s": ["A"] * rows + ["B"] * rows, "t": list(range(2 * rows))})
        assert analyze_sensitive_correlations(df, "t", ["s"]) == []

    def test_four_rows_compute_point_biserial(self) -> None:
        df = pd.DataFrame({"s": ["A", "A", "B", "B"], "t": [0, 1, 2, 3]})
        issues = analyze_sensitive_correlations(df, "t", ["s"])
        assert issues
        assert issues[0]["metrics"]["method"] == "point_biserial"
        assert issues[0]["metrics"]["sample_size"] == 4

    def test_all_missing_pair_is_skipped(self) -> None:
        df = pd.DataFrame({"s": [None] * 6, "t": [None] * 6})
        assert analyze_sensitive_correlations(df, "t", ["s"]) == []

    def test_cramers_v_clamped_to_unit_interval(self) -> None:
        v = _cramers_v(pd.Series(["A", "A", "A", "B", "B"]), pd.Series(["x", "x", "x", "y", "y"]))
        assert v == 1.0
        v2 = _cramers_v(pd.Series(["A", "A", "A", "B", "B"]), pd.Series(["x", "x", "x", "y", "z"]))
        assert 0.0 <= v2 <= 1.0

    def test_cramers_v_zero_for_independent_columns(self) -> None:
        rng = np.random.default_rng(0)
        a = pd.Series(["A", "B"] * 200)
        b = pd.Series(rng.choice(["x", "y"], size=400))
        assert 0.0 <= _cramers_v(a, b) < 0.05

    def test_cramers_v_zero_when_one_dimension_singleton(self) -> None:
        assert _cramers_v(pd.Series(["A", "A", "A"]), pd.Series(["x", "y", "z"])) == 0.0

    def test_point_biserial_matches_scipy_reference(self) -> None:
        rng = np.random.default_rng(42)
        continuous = rng.normal(size=200)
        labels = pd.Series(["F"] * 100 + ["M"] * 100)
        ours = _point_biserial(labels, pd.Series(continuous))
        ref, _ = pointbiserialr([0] * 100 + [1] * 100, continuous)
        assert ours == pytest.approx(ref, abs=1e-12)

    def test_point_biserial_zero_for_constant_continuous(self) -> None:
        labels = pd.Series(["F"] * 5 + ["M"] * 5)
        assert _point_biserial(labels, pd.Series([2.5] * 10)) == 0.0

    def test_continuous_pearson_path_used_for_high_cardinality(self) -> None:
        rng = np.random.default_rng(7)
        x = rng.normal(size=500)
        y = 2.0 * x + rng.normal(size=500)
        df = pd.DataFrame({"s": x, "t": y})
        issues = analyze_sensitive_correlations(df, "t", ["s"])
        assert issues
        assert issues[0]["metrics"]["method"] == "pearson"
        assert issues[0]["metrics"]["absolute_correlation"] > 0.5

    def test_continuous_spearman_path_for_low_cardinality(self) -> None:
        x = pd.Series([0.0, 0.1] * 40)
        y = pd.Series([0.0, 0.1] * 40)
        permissive = {"cramers_v": {"medium": 0.0, "high": 1.0}}
        issues = analyze_sensitive_correlations(
            pd.DataFrame({"s": x, "t": y}), "t", ["s"], severity_thresholds=permissive
        )
        assert issues
        assert issues[0]["metrics"]["method"] == "spearman"
        ref, _ = spearmanr(x, y)
        assert issues[0]["metrics"]["correlation_value"] == pytest.approx(ref, abs=1e-12)

    def test_categorical_vs_categorical_uses_cramers_v(self) -> None:
        df = pd.DataFrame({"s": ["A", "B"] * 30, "t": ["x", "y"] * 30})
        issues = analyze_sensitive_correlations(df, "t", ["s"])
        assert issues
        assert issues[0]["metrics"]["method"] == "cramers_v"

    def test_sample_size_counts_clean_pairs_only(self) -> None:
        df = pd.DataFrame(
            {"s": ["A"] * 10 + ["B"] * 10, "t": [0] * 10 + [1] * 8 + [None, None]}
        )
        issues = analyze_sensitive_correlations(df, "t", ["s"])
        assert issues
        assert issues[0]["metrics"]["sample_size"] == 18

    def test_bin_numeric_returns_none_for_constant(self) -> None:
        assert _bin_numeric(pd.Series([1.0, 1.0, 1.0])) is None
        assert _bin_numeric(pd.Series([], dtype=float)) is None
        assert _bin_numeric(pd.Series([1.0, 2.0, np.inf, np.inf])) is not None

    def test_clean_pair_drops_non_finite(self) -> None:
        a = pd.Series([1.0, 2.0, np.inf, 4.0, np.nan])
        b = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        a_clean, b_clean = _clean_pair(a, b)
        assert list(a_clean) == [1.0, 2.0, 4.0]
        assert list(b_clean) == [1.0, 2.0, 4.0]

    def test_no_duplicate_issues_for_repeated_sensitive_cols(self) -> None:
        df = pd.DataFrame({"s": ["A"] * 4 + ["B"] * 4, "t": [0, 1] * 4})
        assert analyze_sensitive_correlations(df, "t", ["s", "s"]) == analyze_sensitive_correlations(
            df, "t", ["s"]
        )


# --- missing values ---


class TestMissingValuesEdgeCases:
    def test_empty_frame_yields_no_issues(self) -> None:
        df = pd.DataFrame({"g": pd.Series([], dtype=str), "f": pd.Series([], dtype=float)})
        assert analyze_missing_values_by_group(df, ["g"]) == []

    def test_single_group_is_skipped(self) -> None:
        df = pd.DataFrame({"g": ["A"] * 5, "f": [None] * 5, "t": [0] * 5})
        assert analyze_missing_values_by_group(df, ["g"]) == []

    def test_no_missingness_yields_no_issues(self) -> None:
        df = pd.DataFrame({"g": ["A", "B"] * 20, "f": [1] * 40, "t": [0, 1] * 20})
        assert analyze_missing_values_by_group(df, ["g"]) == []

    def test_all_missing_in_one_group_is_high_gap(self) -> None:
        df = pd.DataFrame(
            {"g": ["A"] * 10 + ["B"] * 10, "f": [None] * 10 + [1] * 10, "t": [0, 1] * 10}
        )
        issues = analyze_missing_values_by_group(df, ["g"])
        assert issues
        issue = next(i for i in issues if i["metrics"]["feature_column"] == "f")
        assert issue["severity"] == "high"
        assert issue["metrics"]["missingness_gap"] == pytest.approx(1.0)

    def test_equal_missingness_across_groups_is_skipped(self) -> None:
        df = pd.DataFrame(
            {"g": ["A", "A", "B", "B"] * 10, "f": [None, 1, None, 1] * 10, "t": [0, 1] * 20}
        )
        assert analyze_missing_values_by_group(df, ["g"]) == []

    def test_nan_sensitive_values_form_missing_group(self) -> None:
        df = pd.DataFrame(
            {"g": ["A"] * 8 + [None] * 4, "f": [1] * 8 + [None] * 4, "t": [0] * 12}
        )
        issues = analyze_missing_values_by_group(df, ["g"])
        assert issues
        assert "__MISSING_GROUP__" in issues[0]["metrics"]["missingness_rates"]

    def test_feature_equals_sensitive_column_is_skipped(self) -> None:
        df = pd.DataFrame({"g": ["A"] * 5 + ["B"] * 5, "t": [0] * 10})
        assert analyze_missing_values_by_group(df, ["g"]) == []

    def test_numeric_sensitive_column_is_supported(self) -> None:
        df = pd.DataFrame({"g": [0] * 10 + [1] * 10, "f": [None] * 8 + [1] * 12, "t": [0] * 20})
        issues = analyze_missing_values_by_group(df, ["g"])
        assert any(i["metrics"]["missingness_gap"] > 0.5 for i in issues)

    def test_metrics_carry_group_sizes(self) -> None:
        df = pd.DataFrame(
            {"g": ["A"] * 3 + ["B"] * 7, "f": [None] * 3 + [1] * 7, "t": [0] * 10}
        )
        issues = analyze_missing_values_by_group(df, ["g"])
        assert issues[0]["metrics"]["group_sizes"] == {"A": 3, "B": 7}


# --- subgroup analysis ---


class TestSubgroupEdgeCases:
    def test_empty_frame_is_skipped(self) -> None:
        df = pd.DataFrame({"g": pd.Series([], dtype=str), "t": pd.Series([], dtype=str)})
        assert analyze_subgroup_label_distribution(df, "t", ["g"]) == []

    def test_single_group_is_skipped(self) -> None:
        df = pd.DataFrame({"g": ["A"] * 5, "t": [0, 1, 0, 1, 0]})
        assert analyze_subgroup_label_distribution(df, "t", ["g"]) == []

    def test_all_missing_target_resolves_to_missing_class(self) -> None:
        df = pd.DataFrame({"g": ["A", "B"] * 3, "t": [None] * 6})
        assert _resolve_positive_class(df["t"]) == "__MISSING__"

    def test_tie_break_prefers_conventional_positive(self) -> None:
        df = pd.DataFrame({"g": ["A", "B"] * 4, "t": [0, 1, 1, 1, 0, 0, 0, 1]})
        assert _resolve_positive_class(df["t"]) == "1"

    def test_tie_break_lexicographic_when_no_conventional(self) -> None:
        df = pd.DataFrame({"g": ["A", "B"] * 2, "t": ["cat", "dog", "cat", "dog"]})
        assert _resolve_positive_class(df["t"]) == "cat"

    def test_minority_class_preferred_as_positive(self) -> None:
        df = pd.DataFrame({"g": ["A", "B"] * 3, "t": ["x", "x", "x", "y", "x", "x"]})
        assert _resolve_positive_class(df["t"]) == "y"

    def test_nan_sensitive_values_form_missing_group(self) -> None:
        df = pd.DataFrame({"g": ["A"] * 4 + [None] * 4, "t": [0, 1, 1, 1, 0, 0, 0, 0]})
        issues = analyze_subgroup_label_distribution(df, "t", ["g"])
        assert "__MISSING_GROUP__" in issues[0]["metrics"]["positive_rates"]

    def test_parity_gap_high_for_extreme_skew(self) -> None:
        df = pd.DataFrame({"g": ["A"] * 10 + ["B"] * 10, "t": [1] * 9 + [0] * 1 + [1] * 1 + [0] * 9})
        issues = analyze_subgroup_label_distribution(df, "t", ["g"])
        assert issues[0]["severity"] == "high"
        assert issues[0]["metrics"]["demographic_parity_gap"] == pytest.approx(0.8)

    def test_constant_rates_across_groups_are_skipped(self) -> None:
        df = pd.DataFrame({"g": ["A", "B"] * 10, "t": [1] * 20})
        assert analyze_subgroup_label_distribution(df, "t", ["g"]) == []

    def test_positive_class_override(self) -> None:
        df = pd.DataFrame({"g": ["A"] * 4 + ["B"] * 4, "t": [1] * 4 + [0] * 4})
        default = analyze_subgroup_label_distribution(df, "t", ["g"])
        assert default[0]["metrics"]["positive_class"] == "1"
        overridden = analyze_subgroup_label_distribution(df, "t", ["g"], positive_class="0")
        assert overridden[0]["metrics"]["positive_class"] == "0"
