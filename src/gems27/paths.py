"""Repository and data-cache locations. Large inputs live outside git (see data/manifest.json)."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("GEMS_DATA_DIR", REPO / "data_cache"))
DOCS = REPO / "docs"
EVIDENCE = REPO / "evidence"
REGISTRY = REPO / "registry"
MANIFEST = REPO / "data" / "manifest.json"

LABELS = DATA / "labels.tif"
TEMPLATE = DATA / "sample_submission.tif"
TRAINING = DATA / "training_features.tif"
H19_5 = DATA / "h19_5_nan.tif"
DOTTED_0_2477 = DATA / "dotted_h19_5_d1_5_nan.tif"
DOTTED_D2_8 = DATA / "dotted_h19_5_d2_8_nan.tif"
LIDAR = DATA / "lidar_scarp_features_u8.tif"
EXTENSIONS = DATA / "geodawn_extensions_u8.tif"
RAD = DATA / "geodawn_rad_u8.tif"
SGMC = DATA / "derived_sgmc_faults_100m_u8.tif"
QFAULT_TRACES = DATA / "gdr_qfaults_traces.csv"
QFAULT_VECTORS = DATA / "qfaults_v2_in_footprint.json"
VOLCANIC_VENTS = DATA / "gdr_volcanic_vents_in_footprint.csv"
WELLSPRING = DATA / "gdr_wellspring_in_footprint.csv"
DEM_LINKS = DATA / "dem_links.json"
PREPARED_FEATURES = DATA / "prepared" / "features.npy"
PREPARED_META = DATA / "prepared" / "features.json"
