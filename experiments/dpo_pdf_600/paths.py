"""Paths for the final experiment, independent of the working directory.

Saved manifests describe the original run. Never rewrite their paths or hashes
when relocating files; use the current paths here only to access local data.
"""
from pathlib import Path, PureWindowsPath

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DATA_DIR = EXPERIMENT_ROOT / 'data'
DATASET_DIR = DATA_DIR / 'dataset_consegna'
RUNS_DIR = EXPERIMENT_ROOT / 'runs'
RESULTS_DIR = EXPERIMENT_ROOT / 'results'
EVALUATION_DIR = RESULTS_DIR / 'evaluation'
FIGURES_DIR = RESULTS_DIR / 'figures'
REPORT_DIR = RESULTS_DIR / 'reports'
DEMO_DIR = EXPERIMENT_ROOT / 'demo'


def comparison_training_manifest(training):
    """Return the training metadata used to fingerprint a comparison.

    Old trainers did not record dataset_path. Their comparison scripts added the
    original experiment's dataset_consegna path before hashing. Reconstruct that
    same value for old runs; new runs record the dataset path explicitly.
    """
    if 'dataset_path' in training:
        return dict(training)
    output = training['dpo']['output_dir']
    path_type = PureWindowsPath if '\\' in output else Path
    original_root = path_type(output).parent.parent
    return {**training, 'dataset_path': str(original_root / 'dataset_consegna')}
