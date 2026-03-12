"""
train_ec_soup.py

Train EC-only lightweight CNN + checkpoint soup, with subject-level split.
Saves:
- ./output/saved_model/soup_model_EC.keras
- ./output/saved_model/base_model_EC.keras (optional)
- ./output/assets/shap_bg_ec.npy

Run:
  python train_ec_soup.py
"""

from __future__ import annotations

import os
import re
import numpy as np

from sklearn.model_selection import GroupShuffleSplit
import tensorflow as tf

from preprocessing_ec import read_data, preprocess_eeg, to_model_input
from models import train_checkpoint_soup, save_keras_model, save_shap_background

# -----------------------------
# Config
# -----------------------------
EDF_DIR = "dataset"  # <-- change if needed
CONDITION_SUFFIX = "EC.edf"  # EC-only
OUT_MODEL_SOUP = "../output/model/soup_model_EC.keras"
OUT_MODEL_BASE = "../output/model/base_model_EC.keras"
OUT_SHAP_BG = "../output/assets/shap_bg_ec.npy"

# Preprocessing params (must match training/inference)
PREP = dict(
    l_freq=0.5,
    h_freq=70.0,
    notch_freq=50.0,
    n_components=4,
    epoch_duration=5.0,
    epoch_overlap=0.5,
    ica_method="fastica",
    seed=42,
)

# Training params
TRAIN = dict(
    epochs=10,
    batch_size=64,
    seed=42,
    lr=3e-4,
    l2_weight=1e-4,
    k=3,                  # best-K epochs for soup
    select_by="val_accuracy",  # "val_accuracy" recommended
    use_callbacks=True,
    verbose=1,
)


# -----------------------------
# Helpers
# -----------------------------
def normalize_edf_filename(filename: str) -> str:
    """
    Normalize EDF filename to canonical format:
      - Replace spaces with underscores
      - Remove leading numeric IDs (e.g., 6921959_)
      - Zero-pad single-digit subject IDs (S4 -> S04)

    Example:
      '6921959_H S4 EC.edf' -> 'H_S04_EC.edf'
    """
    name = filename

    # Remove leading numeric ID 6921959_ (not for all numbers because of duplicate file)
    name = re.sub(r'6921959_', '', name)

    # Replace spaces with underscores
    name = re.sub(r'\s+', '_', name)

    # Zero-pad subject numbers (S4 -> S04)
    name = re.sub(r'S(\d)(?!\d)', r'S0\1', name)

    return name

def normalize_dataset_directory(folder_path: str, verbose: bool = True) -> None:
    """
    Rename all EDF files in folder to canonical format.
    Safe to run once before training or deployment.
    """
    for fname in os.listdir(folder_path):
        if not fname.lower().endswith(".edf"):
            continue

        new_name = normalize_edf_filename(fname)

        if new_name != fname:
            src = os.path.join(folder_path, fname)
            dst = os.path.join(folder_path, new_name)

            if os.path.exists(dst):
                if verbose:
                    print(f"Skipping (already exists): {new_name}")
                continue

            os.rename(src, dst)

            if verbose:
                print(f"Renamed: {fname} -> {new_name}")

def list_ec_files(edf_dir: str) -> list[str]:
    files = [
        os.path.join(edf_dir, f)
        for f in os.listdir(edf_dir)
        if f.endswith(CONDITION_SUFFIX)
    ]
    files.sort()
    return files


def label_from_filename(fname: str) -> int:
    """
    Your naming convention: Healthy files start with 'H_', MDD files start with 'MDD_'
    """
    base = os.path.basename(fname)
    if base.startswith("MDD"):
        return 1
    if base.startswith("H"):
        return 0
    raise ValueError(f"Cannot infer label from filename: {base}")


def subject_id_from_filename(fname: str) -> str:
    """
    Extract subject ID like S04, S26 from filename. Works for 'H_S04_EC.edf', 'MDD_S26_EC.edf'.
    """
    base = os.path.basename(fname)
    m = re.search(r"(S\d{2})", base)
    if not m:
        raise ValueError(f"Could not parse subject ID from filename: {base}")
    return m.group(1)


# -----------------------------
# Main
# -----------------------------
def main():
    print("=== DepreSense EC-only training (checkpoint soup) ===")
    print("EDF_DIR:", EDF_DIR)

    normalize_dataset_directory(EDF_DIR)

    ec_files = list_ec_files(EDF_DIR)
    if len(ec_files) == 0:
        raise RuntimeError(f"No EC EDF files found in {EDF_DIR} (suffix {CONDITION_SUFFIX})")

    print(f"Found {len(ec_files)} EC files")

    X_list = []
    y_list = []
    groups = []

    # Track subject counts
    subj_epoch_counts = {}

    for path in ec_files:
        base = os.path.basename(path)
        print(f"\n--- Loading + preprocessing: {base}")

        raw = read_data(path, preload=True)
        data_4d = preprocess_eeg(raw, verbose=True, **PREP)

        if data_4d is None:
            print(f"!! Skipping (preprocess failed): {base}")
            continue

        X_sub = to_model_input(data_4d)  # (n_epochs, 1280, 19)
        y = label_from_filename(base)
        sid = subject_id_from_filename(base)

        # Append epochs
        X_list.append(X_sub)
        y_list.extend([y] * X_sub.shape[0])
        groups.extend([sid] * X_sub.shape[0])

        subj_epoch_counts[sid] = subj_epoch_counts.get(sid, 0) + X_sub.shape[0]
        print(f"Added {X_sub.shape[0]} epochs | label={y} | subject={sid}")

    if len(X_list) == 0:
        raise RuntimeError("No files were successfully preprocessed.")

    # Concatenate
    X = np.concatenate(X_list, axis=0).astype(np.float32)  # (N,1280,19)
    y = np.array(y_list, dtype=np.int64)
    groups = np.array(groups)

    print("\n=== Dataset summary ===")
    print("X:", X.shape, X.dtype)
    print("y:", y.shape, y.dtype)
    u, c = np.unique(y, return_counts=True)
    print("Label dist:", dict(zip(u.tolist(), c.tolist())))
    print("Unique subjects:", len(np.unique(groups)))
    print("Epochs per subject (min/mean/max):",
          int(np.min(list(subj_epoch_counts.values()))),
          float(np.mean(list(subj_epoch_counts.values()))),
          int(np.max(list(subj_epoch_counts.values()))))

    # Group split
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, val_idx = next(gss.split(X, y, groups=groups))

    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    groups_train, groups_val = groups[train_idx], groups[val_idx]

    print("\n=== Split summary (GroupShuffleSplit) ===")
    print("Train:", X_train.shape, "Val:", X_val.shape)
    print("Train label dist:", np.unique(y_train, return_counts=True))
    print("Val label dist:", np.unique(y_val, return_counts=True))
    print("Unique subjects train:", len(np.unique(groups_train)))
    print("Unique subjects val:", len(np.unique(groups_val)))

    # Train checkpoint soup (single run)
    results = train_checkpoint_soup(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        input_shape=tuple(X_train.shape[1:]),
        **TRAIN
    )

    base_model = results["base_model"]
    soup_model = results["soup_model"]

    # Save models
    save_keras_model(soup_model, OUT_MODEL_SOUP)
    save_keras_model(base_model, OUT_MODEL_BASE)

    # Save SHAP background subset from training epochs
    save_shap_background(X_train, OUT_SHAP_BG, n=100, seed=42)

    print("\n=== Done ===")
    print("Soup model:", OUT_MODEL_SOUP)
    print("Base model:", OUT_MODEL_BASE)
    print("SHAP background:", OUT_SHAP_BG)
    print("Selected epochs:", results["selected_epochs"])
    print("Soup eval (val):", results["soup_eval"])
    print("Base eval (val):", results["base_eval"])


if __name__ == "__main__":
    # Reduce Tensorflow log spam
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
    main()
