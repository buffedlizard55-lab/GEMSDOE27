"""Reviewer-facing classes for the 345 T-v2 topology candidates.

The H27-5b class prioritizes a measured vector-holdout stratum, not a graph-centrality score or a
claim that each link is a mapped/verified fault. A different NBMG FID is a distinct feature record
within the same source dataset, not an independent survey.
"""

from __future__ import annotations

H27_5B_PRIORITY_CLASS = "H27-5b_inter-FID_same-name_kinematic-compatible"
SAME_FID_CLASS = "same-FID_multipart-continuity"
INTER_NAME_KINEMATIC_CLASS = "inter-FID_other-name_kinematic-compatible"
KINEMATIC_REVIEW_CLASS = "inter-FID_kinematic-conflict-or-unknown"

REVIEW_CLASS_NAMES = (
    SAME_FID_CLASS,
    H27_5B_PRIORITY_CLASS,
    INTER_NAME_KINEMATIC_CLASS,
    KINEMATIC_REVIEW_CLASS,
)

NBMG_LAYER_URL = "https://web2.nbmg.unr.edu/arcgis/rest/services/Qfaults/Qfaults_INGENIOUS/MapServer/0"
FAULDS_HINZ_URL = "https://www.osti.gov/servlets/purl/1724082"


def classify_review_class(same_fid: bool, same_name: bool, kinematic_compat: bool) -> str:
    """Assign a mutually exclusive reviewer class from the frozen NBMG H27-5 attributes."""
    if same_fid:
        return SAME_FID_CLASS
    if same_name and kinematic_compat:
        return H27_5B_PRIORITY_CLASS
    if kinematic_compat:
        return INTER_NAME_KINEMATIC_CLASS
    return KINEMATIC_REVIEW_CLASS


def geometry_setting_hint(kind: str) -> str:
    """Translate candidate geometry to a cautious map-review cue, not a tectonic interpretation."""
    if kind == "end-to-end":
        return "along-strike endpoint gap; assess continuation, relay, or cartographic segmentation"
    if kind == "abutting":
        return "abutment/termination geometry; verify fault intersections and cross-cutting relations"
    if kind == "tip-to-tip oblique":
        return "oblique step-over-like geometry; verify overlap, slip sense, and relay direction"
    raise ValueError(f"unsupported T-v2 link geometry: {kind}")
