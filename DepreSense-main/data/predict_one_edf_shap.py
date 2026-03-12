"""
predict_one_edf_shap.py

Single-EDF inference + SHAP channel-importance visualization (EC model).

Outputs (in ./output/shap_vis/):
- channel_importance_abs.png
- channel_importance_abs.csv
- epoch_probs.csv

Run:
  python predict_one_edf_shap.py --edf "../edf_dataset_2/H_S04_EC.edf"
"""

from __future__ import annotations

import os
import argparse
import numpy as np
import pandas as pd
import tensorflow as tf
import shap
import matplotlib.pyplot as plt

from preprocessing_ec import infer_one_edf, CHANNELS_19


MODEL_PATH = "../output/model/soup_model_EC.keras"
BG_PATH = "../output/assets/shap_bg_ec.npy"
OUT_DIR = "../output/shap_vis"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def subject_predict(model: tf.keras.Model, X_subject: np.ndarray) -> tuple[float, np.ndarray]:
    """
    Returns:
      subject_prob: mean probability across epochs
      epoch_probs: (n_epochs,) probabilities
    """
    epoch_probs = model.predict(X_subject, verbose=0).reshape(-1)
    subject_prob = float(np.mean(epoch_probs))
    return subject_prob, epoch_probs


def compute_shap_channel_importance(
    model: tf.keras.Model,
    X_bg: np.ndarray,
    X_explain: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute SHAP values and aggregate to channel-level importance.

    X_bg: (B, 1280, 19)
    X_explain: (E, 1280, 19)

    Returns:
      channel_abs: (19,) mean(|shap|) aggregated over epochs+time
      channel_signed: (19,) mean(shap) aggregated over epochs+time  (not plotted by default)
    """
    # GradientExplainer works well for TF/Keras differentiable models
    explainer = shap.GradientExplainer(model, X_bg)

    # shap_values may be:
    # - np.ndarray for single-output models, or
    # - list with one array (for binary output)
    shap_values = explainer.shap_values(X_explain)

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    # Handle possible output shape (E, 1280, 19, 1)
    if shap_values.ndim == 4 and shap_values.shape[-1] == 1:
        shap_values = shap_values[..., 0]  # remove output dim

    if shap_values.ndim != 3 or shap_values.shape[-1] != 19:
        raise ValueError(
            f"Unexpected SHAP shape after squeeze: {shap_values.shape} "
            "(expected (E,1280,19))"
        )

    channel_abs = np.mean(np.abs(shap_values), axis=(0, 1))     # (19,)
    channel_signed = np.mean(shap_values, axis=(0, 1))          # (19,)

    return channel_abs, channel_signed


def plot_channel_importance(channel_abs: np.ndarray, out_path: str) -> None:
    """
    Save a clean bar chart for channel importance (magnitude).
    """
    # Sort descending
    order = np.argsort(channel_abs)[::-1]
    labels = [CHANNELS_19[i] for i in order]
    vals = channel_abs[order]

    plt.figure(figsize=(10, 5))
    plt.bar(labels, vals)
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Mean |SHAP value| (impact)")
    plt.title("EEG Channel Importance (Subject-level)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--edf", required=True, help="Path to a single EC EDF file")
    parser.add_argument("--explain_epochs", type=int, default=20, help="How many epochs to explain with SHAP")
    args = parser.parse_args()

    ensure_dir(OUT_DIR)

    # Load model + background
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    if not os.path.exists(BG_PATH):
        raise FileNotFoundError(f"SHAP background not found: {BG_PATH}")

    model = tf.keras.models.load_model(MODEL_PATH, compile=False)
    X_bg = np.load(BG_PATH).astype(np.float32)

    # Preprocess EDF -> model input
    X_subject = infer_one_edf(args.edf, verbose=False)  # (n_epochs,1280,19)
    if X_subject.ndim != 3 or X_subject.shape[-1] != 19:
        raise ValueError(f"Unexpected X_subject shape: {X_subject.shape}")

    # Predict
    subject_prob, epoch_probs = subject_predict(model, X_subject)
    pred_label = "High likelihood (MDD)" if subject_prob >= 0.5 else "Low likelihood (Healthy)"
    print(f"\nEDF: {os.path.basename(args.edf)}")
    print(f"Epochs: {len(epoch_probs)}")
    print(f"Subject mean prob: {subject_prob:.4f} -> {pred_label}")

    # Save epoch probs
    epoch_df = pd.DataFrame({"epoch": np.arange(len(epoch_probs)), "prob_mdd": epoch_probs})
    epoch_csv = os.path.join(OUT_DIR, "epoch_probs.csv")
    epoch_df.to_csv(epoch_csv, index=False)
    print(f"Saved: {epoch_csv}")

    # SHAP (use subset of epochs for speed)
    E = min(args.explain_epochs, X_subject.shape[0])
    X_explain = X_subject[:E].astype(np.float32)

    channel_abs, channel_signed = compute_shap_channel_importance(model, X_bg, X_explain)

    # Save channel importance CSV
    ch_df = pd.DataFrame({
        "channel": CHANNELS_19,
        "mean_abs_shap": channel_abs,
        "mean_signed_shap": channel_signed,
    }).sort_values("mean_abs_shap", ascending=False)

    ch_csv = os.path.join(OUT_DIR, "channel_importance_abs.csv")
    ch_df.to_csv(ch_csv, index=False)
    print(f"Saved: {ch_csv}")

    # Plot bar chart
    fig_path = os.path.join(OUT_DIR, "channel_importance_abs.png")
    plot_channel_importance(channel_abs, fig_path)
    print(f"Saved: {fig_path}")

    # Print top channels
    print("\nTop 8 channels by mean |SHAP|:")
    for _, row in ch_df.head(8).iterrows():
        print(f"{row['channel']:>3s}  |SHAP|={row['mean_abs_shap']:.6f}  signed={row['mean_signed_shap']:.6f}")


if __name__ == "__main__":
    # Reduce TF log spam
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
    main()
