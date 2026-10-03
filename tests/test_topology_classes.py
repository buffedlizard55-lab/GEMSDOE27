import pytest

from gems27.topology_classes import (
    H27_5B_PRIORITY_CLASS,
    INTER_NAME_KINEMATIC_CLASS,
    KINEMATIC_REVIEW_CLASS,
    SAME_FID_CLASS,
    classify_review_class,
    geometry_setting_hint,
)


@pytest.mark.parametrize(
    ("same_fid", "same_name", "kinematic_compat", "expected"),
    [
        (True, True, True, SAME_FID_CLASS),
        (False, True, True, H27_5B_PRIORITY_CLASS),
        (False, False, True, INTER_NAME_KINEMATIC_CLASS),
        (False, True, False, KINEMATIC_REVIEW_CLASS),
        (False, False, False, KINEMATIC_REVIEW_CLASS),
    ],
)
def test_review_classes_are_exclusive_and_h27_5b_requires_all_three_attributes(
    same_fid, same_name, kinematic_compat, expected
):
    assert classify_review_class(same_fid, same_name, kinematic_compat) == expected


def test_geometry_hints_are_cautious_and_require_known_candidate_kinds():
    assert "continuation" in geometry_setting_hint("end-to-end")
    assert "termination" in geometry_setting_hint("abutting")
    assert "step-over-like" in geometry_setting_hint("tip-to-tip oblique")
    with pytest.raises(ValueError, match="unsupported"):
        geometry_setting_hint("unknown")
