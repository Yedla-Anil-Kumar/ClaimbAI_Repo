from radon.complexity import cc_visit
from radon.metrics import mi_visit

ML_FRAMEWORK_KEYWORDS = {
    'import torch', 'import tensorflow', 'from sklearn', 'from keras',
    'import mxnet', 'import xgboost', 'import lightgbm'
}

ADVANCED_ML_KEYWORDS = {
    'import optuna', 'import ray', 'from hyperopt', 'import shap', 'import lime',
    'import dask', 'from pyspark', 'import horovod', 'import kubeflow'
}

def average_cyclomatic_complexity(py_files):
    """
    Compute average cyclomatic complexity across all Python files.
    """
    total, count = 0, 0
    for path in py_files:
        try:
            src = open(path, 'r').read()
            for block in cc_visit(src):
                total += block.complexity
                count += 1
        except Exception:
            continue
    return (total / count) if count else 0

def maintainability_index(py_files):
    """
    Compute average Maintainability Index across Python files.
    """
    scores = []
    for path in py_files:
        try:
            src = open(path, 'r').read()
            mi = mi_visit(src, True)
            scores.extend(mi.values())
        except Exception:
            continue
    return (sum(scores) / len(scores)) if scores else 0

def detect_ml_usage(py_files):
    """
    Return True if any standard ML framework imports are found.
    """
    for path in py_files:
        try:
            text = open(path, 'r').read()
            if any(kw in text for kw in ML_FRAMEWORK_KEYWORDS):
                return True
        except Exception:
            continue
    return False

def detect_advanced_tech_usage(py_files):
    """
    Return True if any advanced ML/AutoML keywords are found.
    """
    for path in py_files:
        try:
            text = open(path, 'r').read().lower()
            if any(kw in text for kw in ADVANCED_ML_KEYWORDS):
                return True
        except Exception:
            continue
    return False
