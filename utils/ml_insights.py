import ast
from pathlib import Path
from typing import List, Dict, Union, Set, Optional
import warnings

# ─── Configurable Constants ──────────────────────────────────────────────

ML_FRAMEWORKS = {"torch", "tensorflow", "sklearn", "keras", "xgboost", "lightgbm"}
EXPERIMENT_TRACKERS = {"mlflow", "wandb", "clearml"}
VALIDATION_LIBS = {"great_expectations", "evidently", "pandera"}
FEATURE_LIBS = {"sklearn.preprocessing", "featuretools", "tsfresh"}
INFERENCE_LIBS = {"fastapi", "flask", "streamlit"}
OPTIMIZATION_LIBS = {"optuna", "ray.tune"}
METRICS_MODULES = {"sklearn.metrics", "torchmetrics"}
DEP_FILES = {"requirements.txt", "Pipfile", "pyproject.toml"}

HYPERPARAM_CONFIG_DIRS = ["configs/hparams", "configs/hyperparameters", "hparams"]
PIPELINE_MODULES = {
    "airflow": ({"dags"}, "DAG"),
    "prefect": ({"flows", "src/flows"}, None),
    "luigi": ({"tasks", "src/tasks"}, None),
}
PIPELINE_CONFIG_FILES = ["pipeline.yaml", "pipeline.yml", "params.yaml"]
KEDRO_CONFIG_FILE = "conf/base/parameters.yml"
MODEL_DIRS = {"saved_model", "models", "model", "outputs"}
DOC_FILES = {"README.md", "README.rst", "docs"}

# ─── Helper Functions ────────────────────────────────────────────────────

def safe_parse(file_path: Path) -> Optional[ast.AST]:
    """Safely parse a Python file with proper error handling."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return ast.parse(f.read(), filename=str(file_path))
    except (SyntaxError, UnicodeDecodeError) as e:
        warnings.warn(f"Could not parse {file_path}: {str(e)}")
    except Exception as e:
        warnings.warn(f"Unexpected error parsing {file_path}: {str(e)}")
    return None

def detect_imports(tree: ast.AST) -> Dict[str, Set[str]]:
    """
    Extract all imports from an AST tree.
    Returns dict with:
    - 'top_level': set of top-level package names (e.g., 'torch')
    - 'full_paths': set of full module paths (e.g., 'sklearn.metrics')
    """
    top_level_imports = set()
    full_module_paths = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level_imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                full_module_paths.add(node.module)
                top_level_imports.add(node.module.split(".")[0])
    
    return {"top_level": top_level_imports, "full_paths": full_module_paths}

def get_py_files(root: Path) -> List[Path]:
    """List all Python files in a directory, ignoring hidden ones."""
    return [p for p in root.rglob("*.py") if ".git" not in p.parts]

def check_imports(py_files: List[Path], libraries: Set[str], prefix: str) -> Dict[str, Union[bool, int]]:
    """
    Helper to check for library imports across multiple files.
    Returns counts for each library detected.
    """
    counts = {f"{prefix}_{lib.replace('.', '_')}": 0 for lib in libraries}
    for path in py_files:
        tree = safe_parse(path)
        if not tree:
            continue
            
        imports = detect_imports(tree)
        for lib in libraries:
            if lib in imports["top_level"] or any(m.startswith(lib) for m in imports["full_paths"]):
                counts[f"{prefix}_{lib.replace('.', '_')}"] += 1
    return counts

# ─── Detection Functions ──────────────────────────────────────────────────

def detect_ml_frameworks(py_files: List[Path]) -> Dict[str, int]:
    """Count occurrences of ML framework imports."""
    return check_imports(py_files, ML_FRAMEWORKS, "framework")

def detect_data_pipeline_configs(root: Path, py_files: List[Path]) -> Dict[str, bool]:
    """Detect pipeline tools and configuration files."""
    flags = {f"has_{k}": False for k in PIPELINE_MODULES}
    flags.update({
        "has_argo": any((root / cfg).exists() for cfg in PIPELINE_CONFIG_FILES),
        "has_kedro": (root / KEDRO_CONFIG_FILE).exists(),
    })

    imported_modules = set()
    for path in py_files:
        tree = safe_parse(path)
        if not tree:
            continue
            
        imports = detect_imports(tree)
        imported_modules.update(imports["top_level"])
        
        for module, (_, dag_class) in PIPELINE_MODULES.items():
            if not dag_class:
                continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if (isinstance(func, ast.Attribute) and func.attr == dag_class) or \
                       (isinstance(func, ast.Name) and func.id == dag_class):
                        flags[f"has_{module}"] = True

    for module, _ in PIPELINE_MODULES.items():
        if module in imported_modules:
            flags[f"has_{module}"] = True

    return flags

def detect_experiment_tracking(py_files: List[Path]) -> Dict[str, bool]:
    """Detect experiment tracking tools."""
    return {f"uses_{lib}": bool(count) for lib, count in check_imports(py_files, EXPERIMENT_TRACKERS, "uses").items()}

def detect_model_training_scripts(py_files: List[Path]) -> Dict[str, int]:
    """Detect training scripts and entry points."""
    scripts = [p for p in py_files if p.name.startswith(("train_", "training_"))]
    has_entry = False
    
    for p in scripts:
        tree = safe_parse(p)
        if not tree:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and \
               isinstance(node.test, ast.Compare) and \
               len(node.test.ops) == 1 and \
               isinstance(node.test.ops[0], ast.Eq) and \
               isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__" and \
               isinstance(node.test.comparators[0], ast.Constant) and node.test.comparators[0].value == "__main__":
                has_entry = True
                break
        if has_entry:
            break
            
    return {"train_script_count": len(scripts), "has_entrypoint_training": has_entry}

def detect_model_evaluation(py_files: List[Path]) -> Dict[str, bool]:
    """Detect evaluation scripts and metrics usage."""
    eval_files = [
        p for p in py_files 
        if any(term in p.stem.lower() for term in {"eval", "evaluate", "metrics"})
    ]
    uses_metrics = any(
        any(m.startswith(tuple(METRICS_MODULES)) for m in detect_imports(safe_parse(p))["full_paths"])
        for p in py_files if safe_parse(p)
    )
        
    return {
        "eval_script_count": len(eval_files),
        "uses_metrics_library": uses_metrics
    }

def detect_hyperparameter_configs(root: Path, py_files: List[Path]) -> Dict[str, bool]:
    """Detect hyperparameter config files and optimization libraries."""
    has_file = any(
        (root / cfg_dir).exists() and any(p.suffix.lower() in {".yml", ".yaml", ".json"} for p in (root / cfg_dir).rglob("*"))
        for cfg_dir in HYPERPARAM_CONFIG_DIRS
    )

    optimization_libs_flags = check_imports(py_files, OPTIMIZATION_LIBS, "uses")
    return {
        "has_hyperparam_file": has_file,
        "uses_optuna": bool(optimization_libs_flags.get("uses_optuna")),
        "uses_ray_tune": bool(optimization_libs_flags.get("uses_ray_tune"))
    }

def detect_data_validation(py_files: List[Path]) -> Dict[str, bool]:
    """Detect data validation libraries."""
    flags = check_imports(py_files, VALIDATION_LIBS, "uses")
    return {key: bool(value) for key, value in flags.items()}

def detect_feature_engineering(py_files: List[Path]) -> Dict[str, bool]:
    """Detect feature engineering libraries."""
    flags = check_imports(py_files, FEATURE_LIBS, "uses")
    return {key: bool(value) for key, value in flags.items()}

def detect_model_export(py_files: List[Path], root: Path) -> Dict[str, bool]:
    """Detect model export patterns and directories."""
    flags = {
        "exports_torch_model": False,
        "exports_sklearn_model": False,
        "has_saved_model_dir": any((root / d).is_dir() for d in MODEL_DIRS)
    }

    for p in py_files:
        tree = safe_parse(p)
        if not tree:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    module_name = node.func.value.id
                    func_name = node.func.attr
                    if module_name == "torch" and func_name == "save":
                        flags["exports_torch_model"] = True
                    elif module_name in ("joblib", "pickle") and func_name == "dump":
                        flags["exports_sklearn_model"] = True

    return flags

def detect_inference_endpoints(py_files: List[Path]) -> Dict[str, bool]:
    """Detect inference endpoint libraries."""
    flags = check_imports(py_files, INFERENCE_LIBS, "uses")
    return {key: bool(value) for key, value in flags.items()}

def detect_metric_reporting(py_files: List[Path]) -> Dict[str, bool]:
    """Detect if proper metrics are being calculated and reported."""
    cls_metrics = {"precision_score", "recall_score", "f1_score", "classification_report"}
    reg_metrics = {"r2_score", "mean_squared_error", "mean_absolute_error"}
    
    flags = {
        "reports_precision_recall_f1": False,
        "reports_regression_metrics": False
    }

    for p in py_files:
        tree = safe_parse(p)
        if not tree:
            continue
            
        imports = detect_imports(tree)
        
        # We only care about this if a metrics library is imported
        if not any(m.startswith(tuple(METRICS_MODULES)) for m in imports["full_paths"]):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name)):
                func_name = getattr(node.func, 'attr', None) or getattr(node.func, 'id', None)
                if func_name in cls_metrics:
                    flags["reports_precision_recall_f1"] = True
                if func_name in reg_metrics:
                    flags["reports_regression_metrics"] = True
        
        if all(flags.values()):
            break

    return flags

def detect_nested_loops(py_files: List[Path]) -> Dict[str, int]:
    """Count files containing nested loops (depth >= 2)."""
    nested_count = 0

    class LoopVisitor(ast.NodeVisitor):
        def __init__(self):
            self.depth = 0
            self.max_depth = 0
            
        def visit_For(self, node):
            self.depth += 1
            self.max_depth = max(self.max_depth, self.depth)
            self.generic_visit(node)
            self.depth -= 1
            
        def visit_While(self, node):
            self.depth += 1
            self.max_depth = max(self.max_depth, self.depth)
            self.generic_visit(node)
            self.depth -= 1

    for p in py_files:
        tree = safe_parse(p)
        if not tree:
            continue
            
        visitor = LoopVisitor()
        visitor.visit(tree)
        if visitor.max_depth >= 2:
            nested_count += 1

    return {"nested_loop_files": nested_count}

def detect_dependency_files(root: Path) -> Dict[str, bool]:
    """Detect common dependency management files."""
    flags = {f"has_{f.replace('.', '_')}": False for f in DEP_FILES}
    for f in DEP_FILES:
        if (root / f).exists():
            flags[f"has_{f.replace('.', '_')}"] = True
    return flags

def detect_documentation(root: Path) -> Dict[str, bool]:
    """Detect common documentation files and directories."""
    flags = {f"has_{f.replace('.', '_')}": False for f in DOC_FILES}
    for f in DOC_FILES:
        if (root / f).exists():
            flags[f"has_{f.replace('.', '_')}"] = True
    return flags