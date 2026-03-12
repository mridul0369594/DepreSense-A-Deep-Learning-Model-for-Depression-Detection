"""
models.py

Model + training utilities for DepreSense (EC-first).

Exports:
- build_light_cnn(input_shape=(1280, 19), lr=3e-4, l2_weight=1e-4, ...)
- train_checkpoint_soup(...)
- make_soup_from_checkpoints(...)
- save_keras_model(model, path)
- save_shap_background(X_train, path, n=100, seed=42)
"""

from __future__ import annotations

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import (
    Input,
    Conv1D,
    MaxPooling1D,
    GlobalAveragePooling1D,
    Dense,
    Dropout,
    BatchNormalization,
    SpatialDropout1D,
)
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau


# -----------------------------
# Model definition (the final lightweight CNN)
# -----------------------------
def build_light_cnn(
    input_shape: tuple[int, int] = (1280, 19),
    lr: float = 3e-4,
    l2_weight: float = 1e-4,
    clipnorm: float = 1.0,
    dropout_dense: float = 0.4,
    spatial_dropout: float = 0.15,
) -> tf.keras.Model:
    """
    Lightweight 1D CNN for binary classification.

    Input: (time=1280, features/channels=19)
    Output: sigmoid probability of MDD (1) vs Healthy (0)
    """
    model = Sequential(
        [
            Input(shape=input_shape),

            # Block 1: local temporal features
            Conv1D(
                filters=32,
                kernel_size=7,
                padding="same",
                activation="relu",
                kernel_regularizer=l2(l2_weight),
            ),
            BatchNormalization(),
            MaxPooling1D(pool_size=2),
            SpatialDropout1D(spatial_dropout),

            # Block 2: higher-level temporal features
            Conv1D(
                filters=64,
                kernel_size=5,
                padding="same",
                activation="relu",
                kernel_regularizer=l2(l2_weight),
            ),
            BatchNormalization(),
            MaxPooling1D(pool_size=2),
            SpatialDropout1D(spatial_dropout),

            # Collapse time dimension by averaging features across time
            GlobalAveragePooling1D(),

            # Dense head
            Dense(64, activation="relu", kernel_regularizer=l2(l2_weight)),
            Dropout(dropout_dense),

            # Binary output
            Dense(1, activation="sigmoid"),
        ]
    )

    opt = Adam(learning_rate=lr, clipnorm=clipnorm)
    model.compile(optimizer=opt, loss="binary_crossentropy", metrics=["accuracy"])
    return model


# -----------------------------
# Checkpoint soup utilities
# -----------------------------
def make_soup_from_checkpoints(
    input_shape: tuple[int, int],
    checkpoints: list[list[np.ndarray]],
    lr: float = 3e-4,
    l2_weight: float = 1e-4,
    selection_metric: str = "val_accuracy",
    k: int = 3,
) -> tf.keras.Model:
    """
    Build a soup model by averaging weights from selected checkpoints.

    checkpoints: list of model.get_weights() snapshots.
    """
    if len(checkpoints) == 0:
        raise ValueError("No checkpoints provided.")

    # Average weights elementwise across checkpoints
    avg_weights = [np.mean(w, axis=0) for w in zip(*checkpoints)]

    soup = build_light_cnn(input_shape=input_shape, lr=lr, l2_weight=l2_weight)
    soup.set_weights(avg_weights)
    return soup


def train_checkpoint_soup(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    input_shape: tuple[int, int] | None = None,
    epochs: int = 10,
    batch_size: int = 64,
    seed: int = 42,
    lr: float = 3e-4,
    l2_weight: float = 1e-4,
    k: int = 3,
    select_by: str = "val_accuracy",  # "val_accuracy" or "val_loss"
    verbose: int = 1,
    use_callbacks: bool = True,
) -> dict:
    """
    Train one base model and produce a checkpoint soup.

    Returns dict with:
      - base_model
      - soup_model
      - history (list of dicts per epoch)
      - selected_epochs (indices used for soup)
      - val_metrics_per_epoch
    """
    if input_shape is None:
        input_shape = tuple(X_train.shape[1:])  # (1280,19)

    # Reproducibility
    tf.keras.utils.set_random_seed(seed)

    base = build_light_cnn(input_shape=input_shape, lr=lr, l2_weight=l2_weight)

    callbacks = []
    if use_callbacks:
        callbacks = [
            EarlyStopping(
                monitor="val_loss",
                patience=3,
                restore_best_weights=False,  # IMPORTANT: keep epoch weights for souping
                verbose=1,
            ),
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=2,
                min_lr=1e-6,
                verbose=1,
            ),
        ]

    snapshots: list[list[np.ndarray]] = []
    val_metrics = []  # list of dicts

    # Train 1 epoch at a time so we can snapshot weights cleanly
    for e in range(epochs):
        if verbose:
            print(f"\n=== Epoch {e+1}/{epochs} ===")

        base.fit(
            X_train,
            y_train,
            epochs=1,
            batch_size=batch_size,
            validation_data=(X_val, y_val),
            shuffle=True,
            callbacks=callbacks,
            verbose=verbose,
        )

        # snapshot weights after this epoch
        snapshots.append(base.get_weights())

        # evaluate after this epoch
        vl, va = base.evaluate(X_val, y_val, verbose=0)
        val_metrics.append({"epoch": e, "val_loss": float(vl), "val_accuracy": float(va)})

        if verbose:
            print(f"VAL after epoch {e+1}: loss={vl:.4f}, acc={va:.4f}")

    # Select best-K checkpoints
    if select_by not in {"val_accuracy", "val_loss"}:
        raise ValueError("select_by must be 'val_accuracy' or 'val_loss'.")

    if select_by == "val_accuracy":
        scores = np.array([m["val_accuracy"] for m in val_metrics], dtype=float)
        best_idx = np.argsort(scores)[-k:]  # top K
    else:
        scores = np.array([m["val_loss"] for m in val_metrics], dtype=float)
        best_idx = np.argsort(scores)[:k]   # lowest K

    best_idx = np.array(sorted(best_idx))  # nicer order
    chosen = [snapshots[i] for i in best_idx]

    soup = make_soup_from_checkpoints(
        input_shape=input_shape,
        checkpoints=chosen,
        lr=lr,
        l2_weight=l2_weight,
        k=k,
        selection_metric=select_by,
    )

    base_eval = base.evaluate(X_val, y_val, verbose=0)
    soup_eval = soup.evaluate(X_val, y_val, verbose=0)

    if verbose:
        print("\nBase final model VAL:", base_eval)
        print("Soup model VAL:", soup_eval)
        print("Best epochs used:", best_idx, select_by, [val_metrics[i][select_by] for i in best_idx])

    return {
        "base_model": base,
        "soup_model": soup,
        "val_metrics_per_epoch": val_metrics,
        "selected_epochs": best_idx.tolist(),
        "base_eval": base_eval,
        "soup_eval": soup_eval,
    }


# -----------------------------
# Saving helpers
# -----------------------------
def save_keras_model(model: tf.keras.Model, path: str) -> None:
    """
    Save in Keras v3 format (.keras). Ensure the directory exists.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not path.endswith(".keras"):
        raise ValueError("Path must end with .keras for Keras 3 compatibility.")
    model.save(path)
    print(f"Saved model to: {path}")


def save_shap_background(X_train: np.ndarray, path: str, n: int = 100, seed: int = 42) -> np.ndarray:
    """
    Save a small representative background set for SHAP:
      shape: (n, 1280, 19)

    Returns the saved background array.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rng = np.random.default_rng(seed)
    n = min(n, len(X_train))
    idx = rng.choice(len(X_train), size=n, replace=False)
    X_bg = X_train[idx].astype(np.float32)
    np.save(path, X_bg)
    print(f"Saved SHAP background to: {path}  shape={X_bg.shape}")
    return X_bg
