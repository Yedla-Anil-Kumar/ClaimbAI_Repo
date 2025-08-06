import ast
from pathlib import Path
from typing import List, Dict, Set, Optional
import warnings

# ── Configuration ──
ML_FRAMEWORKS       = {"torch","tensorflow","sklearn","keras","xgboost","lightgbm"}
EXPERIMENT_TRACKERS = {"mlflow","wandb","clearml"}
VALIDATION_LIBS     = {"great_expectations","evidently","pandera"}
FEATURE_LIBS        = {"sklearn.preprocessing","featuretools","tsfresh"}
INFERENCE_LIBS      = {"fastapi","flask","streamlit"}
OPTIMIZATION_LIBS   = {"optuna","ray.tune"}
METRICS_MODULES     = {"sklearn.metrics","torchmetrics"}
HYPERPARAM_DIRS     = ["configs/hparams","configs/hyperparameters","hparams"]
PIPELINE_MODULES    = {
    "airflow": ({"dags"}, "DAG"),
    "prefect": ({"flows","src/flows"}, None),
    "luigi":   ({"tasks","src/tasks"}, None),
}
PIPELINE_CONFIGS    = ["pipeline.yaml","pipeline.yml","params.yaml"]
KEDRO_FILE          = "conf/base/parameters.yml"
MODEL_DIRS          = {"saved_model","models","model","outputs"}

# ── Helpers ──
def safe_parse(path: Path) -> Optional[ast.AST]:
    """Safely parse a Python file with proper error handling."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as e:
        warnings.warn(f"Could not parse {path}: {e}")
        return None

def detect_imports(tree: ast.AST) -> Dict[str, Set[str]]:
    """
    Extract all imports from an AST tree.
    Returns dict with:
    - 'top_level': set of top-level package names (e.g., 'torch')
    - 'full_paths': set of full module paths (e.g., 'sklearn.metrics')
    """
    top, full = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top.add(a.name.split(".",1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            full.add(node.module)
            top.add(node.module.split(".",1)[0])
    return {"top_level": top, "full_paths": full}

# ── Detectors ──

def detect_ml_frameworks(py_files: List[Path]) -> Dict[str,int]:
    """Count occurrences of ML framework imports."""
    counts = {f"framework_{fw}":0 for fw in ML_FRAMEWORKS}
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        for fw in ML_FRAMEWORKS:
            if fw in imps["top_level"] or any(m.startswith(fw) for m in imps["full_paths"]):
                counts[f"framework_{fw}"] += 1
    return counts

def detect_data_pipeline_configs(root: Path, py_files: List[Path]) -> Dict[str,bool]:
    """Detect pipeline tools and configuration files."""
    flags = {f"has_{m}":False for m in PIPELINE_MODULES}
    # FS detection
    for m,(dirs,_) in PIPELINE_MODULES.items():
        if any((root/d).is_dir() for d in dirs):
            flags[f"has_{m}"] = True
    # standard pipeline configs (Argo/KF)
    flags["has_argo"]  = any((root/c).exists() for c in PIPELINE_CONFIGS)
    flags["has_kedro"] = (root/KEDRO_FILE).exists()
    # AST detection
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        for m,(_,dc) in PIPELINE_MODULES.items():
            if m in imps["top_level"]:
                flags[f"has_{m}"] = True
            if dc:
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        fn = node.func
                        if (isinstance(fn, ast.Attribute) and fn.attr==dc) or \
                           (isinstance(fn, ast.Name) and fn.id==dc):
                            flags[f"has_{m}"] = True
    return flags

def detect_experiment_tracking(py_files: List[Path]) -> Dict[str,bool]:
    """Detect experiment tracking tools."""
    flags = {f"uses_{t}":False for t in EXPERIMENT_TRACKERS}
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        for t in EXPERIMENT_TRACKERS:
            if t in imps["top_level"] or any(m.startswith(t) for m in imps["full_paths"]):
                flags[f"uses_{t}"] = True
    return flags

def detect_model_training_scripts(py_files: List[Path]) -> Dict[str,int]:
    """Detect training scripts and entry points."""
    scripts = [p for p in py_files if p.name.startswith(("train_","training_"))]
    has_main = False
    for p in scripts:
        tree = safe_parse(p)
        if not tree: continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
             and getattr(node.test.left,"id",None)=="__name__"
             and getattr(node.test.comparators[0],"value",None)=="__main__"):
                has_main = True
                break
    return {"train_script_count":len(scripts),"has_entrypoint_training":has_main}

def detect_model_evaluation(py_files: List[Path]) -> Dict[str, bool]:
    """Detect evaluation scripts and metrics usage."""
    evals = [p for p in py_files if any(t in p.stem.lower() for t in ("eval","metrics"))]
    has = False
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        if any(m.startswith(tuple(METRICS_MODULES)) for m in imps["full_paths"]):
            has = True
            break
    return {"eval_script_count":len(evals),"uses_metrics_library":has}

def detect_hyperparameter_configs(root: Path, py_files: List[Path]) -> Dict[str, bool]:
    """
    FS‐check for hyperparameter config files under known dirs,
    AST‐detect optuna & ray.tune imports.
    """
    # 1) File‐based detection
    has_file = False
    for cfg_dir in HYPERPARAM_DIRS: 
        cfg_path = root / cfg_dir
        if cfg_path.is_dir():
            if any(p.suffix.lower() in {".yml", ".yaml", ".json"} for p in cfg_path.rglob("*")):
                has_file = True
                break

    # 2) AST‐based detection
    uses_optuna = False
    uses_ray_tune = False
    for p in py_files:
        tree = safe_parse(p)
        if not tree:
            continue
        imps = detect_imports(tree)
        # top‐level imports
        if "optuna" in imps["top_level"] or any(m.startswith("optuna") for m in imps["full_paths"]):
            uses_optuna = True
        if "ray" in imps["top_level"] or any(m.startswith("ray.tune") for m in imps["full_paths"]):
            uses_ray_tune = True
        # early exit
        if uses_optuna and uses_ray_tune:
            break

    return {
        "has_hyperparam_file": has_file,
        "uses_optuna":        uses_optuna,
        "uses_ray_tune":      uses_ray_tune
    }


def detect_data_validation(py_files: List[Path]) -> Dict[str,bool]:
    """Detect data validation libraries."""
    flags = {}
    for lib in VALIDATION_LIBS:
        flags[f"uses_{lib}"] = False
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        for lib in VALIDATION_LIBS:
            if lib in imps["top_level"] or any(m.startswith(lib) for m in imps["full_paths"]):
                flags[f"uses_{lib}"] = True
    return flags

def detect_feature_engineering(py_files: List[Path]) -> Dict[str,bool]:
    """Detect feature engineering libraries."""
    flags = {}
    for lib in FEATURE_LIBS:
        flags[f"uses_{lib.replace('.','_')}"] = False
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        for lib in FEATURE_LIBS:
            if any(m.startswith(lib) for m in imps["full_paths"]):
                flags[f"uses_{lib.replace('.','_')}"] = True
    return flags

def detect_model_export(py_files: List[Path], root: Path) -> Dict[str,bool]:
    """Detect model export patterns and directories."""
    flags = {
      "exports_torch_model": False,
      "exports_sklearn_model": False,
      "has_saved_model_dir": any((root/d).is_dir() for d in MODEL_DIRS)
    }
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                val = node.func.value
                if getattr(val,"id",None)=="torch" and node.func.attr=="save":
                    flags["exports_torch_model"] = True
                if getattr(val,"id",None) in ("joblib","pickle") and node.func.attr=="dump":
                    flags["exports_sklearn_model"] = True
    return flags

def detect_inference_endpoints(py_files: List[Path]) -> Dict[str,bool]:
    """Detect inference endpoint libraries."""
    flags = {}
    for lib in INFERENCE_LIBS:
        flags[f"uses_{lib}"] = False
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        imps = detect_imports(tree)
        for lib in INFERENCE_LIBS:
            if lib in imps["top_level"] or any(m.startswith(lib) for m in imps["full_paths"]):
                flags[f"uses_{lib}"] = True
    return flags

def detect_parallel_patterns(py_files: List[Path]) -> Dict[str,bool]:
    out = {"uses_threading":False,"uses_multiprocessing":False,"uses_concurrent":False}
    for p in py_files:
        txt = p.read_text(errors="ignore")
        if "import threading" in txt:      out["uses_threading"]=True
        if "import multiprocessing" in txt:out["uses_multiprocessing"]=True
        if "import concurrent.futures" in txt: out["uses_concurrent"]=True
    return out

def detect_nested_loops(py_files: List[Path]) -> Dict[str,int]:
    """Count files containing nested loops (depth >= 2)."""
    class V(ast.NodeVisitor):
        def __init__(self): self.depth=0; self.max=0
        def visit_For(self,node):  self.depth+=1; self.max=max(self.max,self.depth); self.generic_visit(node); self.depth-=1
        def visit_While(self,node):self.depth+=1; self.max=max(self.max,self.depth); self.generic_visit(node); self.depth-=1
    cnt=0
    for p in py_files:
        tree = safe_parse(p)
        if not tree: continue
        v=V(); v.visit(tree)
        if v.max>=2: cnt+=1
    return {"nested_loop_files":cnt}