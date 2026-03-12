# SHAP Explainability Implementation

> **Project:** DepreSense — EEG-based MDD Detection  
> **Model:** CNN-Souping (EC-condition, 19 channels)  
> **Last Updated:** 2026-03-04

---

## Overview

DepreSense uses **SHAP GradientExplainer** to generate channel-level feature importance for each depression prediction. The explanation shows which of the 19 EEG channels contributed most (and in which direction) to the model's output.

| Property | Value |
|----------|-------|
| SHAP explainer | `shap.GradientExplainer` |
| Input shape | `(n_epochs, 1280, 19)` float32 |
| Output granularity | Channel-level (19 channels) |
| Background data | `output/assets/shap_bg_ec.npy` (pre-saved representative EEG epochs) |
| Epochs explained | Up to 20 (configurable via `max_explain_epochs`) |
| Computation time | ~30-120 seconds depending on hardware |

---

## Pipeline

```
.edf file
    ↓ preprocessing_ec.infer_one_edf()          (exact training pipeline)
(n_epochs, 1280, 19) float32
    ↓ shap.GradientExplainer(model, X_bg)
SHAP values: (n_epochs, 1280, 19)
    ↓ mean(|shap|, axis=(epoch, time))
channel_abs: (19,)                              ← absolute importance per channel
    ↓ mean(shap, axis=(epoch, time))
channel_signed: (19,)                           ← signed importance per channel
    ↓ format & return
{ feature_importance: {ch: {abs, signed}}, top_features: [ch1..ch5],
  base_value: float, explanation_summary: str, shap_status: "success"|"error" }
```

---

## EEG Channels

The 19 channels used (aligned to the 10-20 international system):

```
Fp1  Fp2  F7   F8   F3   F4   T3   T4
C3   C4   Fz   Cz   Pz   P3   P4   T5
T6   O1   O2
```

These channel names appear directly in `feature_importance` and `top_features` in every API response.

---

## API Response Structure

`POST /predictions/predict` → `PredictionResponse`:

```json
{
  "result": {
    "prediction_id": "abc123",
    "depression_probability": 0.72,
    "risk_level": "high",
    "confidence": 0.44,
    "timestamp": "2026-03-04T07:15:00Z"
  },
  "explanation": {
    "feature_importance": {
      "Fp1": { "abs_importance": 0.000421, "signed_importance": -0.000312 },
      "F3":  { "abs_importance": 0.000389, "signed_importance":  0.000289 },
      "..."
    },
    "top_features": ["Fp1", "F3", "Cz", "P3", "O1"],
    "base_value": 0.72,
    "explanation_summary": "The model predicts a high risk of depression. The most influential EEG channels are Fp1, F3, Cz, which contributed most to the prediction.",
    "shap_status": "success"
  },
  "message": "Prediction completed successfully"
}
```

### `shap_status` Values

| Value | Meaning | Frontend Behaviour |
|-------|---------|-------------------|
| `"success"` | SHAP computed normally | Show bar chart + top features |
| `"error"` | SHAP raised an exception | Show yellow warning banner, hide chart |
| `"unavailable"` | No SHAP data (e.g., historic record) | Show grey info banner |

> [!IMPORTANT]
> The frontier separates SHAP failure from prediction failure. Even when `shap_status = "error"`, the `result` block (probability, risk level) is always valid and returned to the client.

---

## Configuration

Set in `backend/.env`:

```env
# Path to the trained model (relative to backend/)
MODEL_PATH=../output/model

# Path to pre-saved SHAP background data
SHAP_BG_PATH=../output/assets/shap_bg_ec.npy
```

Set in `backend/app/config.py` (defaults):

```python
MODEL_PATH: str = "../output/model"
SHAP_BG_PATH: str = "../output/assets/shap_bg_ec.npy"
```

---

## Background Data (`shap_bg_ec.npy`)

- **Shape:** `(N, 1280, 19)` float32 where N is the number of representative background epochs
- **File size:** ~9.7 MB (current)
- **Location:** `output/assets/shap_bg_ec.npy`
- **Purpose:** Provides the baseline distribution GradientExplainer uses to compute SHAP values. It represents "average" EEG activity.

> [!WARNING]
> If this file is missing, SHAP will return an empty explanation with `shap_status: "error"`. The prediction itself still works. Check the startup log for `"SHAP background file not found"` if SHAP is consistently failing.

---

## Clinical Interpretation

| Feature | Clinical Significance |
|---------|----------------------|
| Frontal channels (Fp1, Fp2, F3, F4, Fz) | Linked to prefrontal cortex activity, strongly associated with mood regulation |
| Alpha-band activity (reflected in temporal) | Reduced alpha power is a known biomarker of depression |
| Posterior channels (O1, O2, P3, P4) | Occipital/parietal involvement in sensory processing |

**Direction of bars in the UI:**
- 🔴 **Red (positive)** → channel activity pushed the model **toward** MDD classification
- 🔵 **Blue (negative)** → channel activity pushed the model **away from** MDD classification

---

## Limitations

1. **Temporal aggregation:** SHAP values are averaged over time (1280 time-steps), so temporal dynamics within segments are not visible in the current UI. Only channel-level importance is shown.
2. **Epoch sub-sampling:** For speed, only the first `max_explain_epochs=20` epochs are explained. For very long recordings this may not represent the entire file.
3. **GradientExplainer approximation:** GradientExplainer uses gradient-based attribution (integrated gradients variant), which is an approximation — not exact Shapley values. It is faster than KernelExplainer and consistent with how the model was originally validated.
4. **Background dependency:** Explanation quality depends on the representativeness of the background data. Background was saved from the training set.
5. **Not a diagnosis:** SHAP output shows model attribution, not neurological causality.

---

## Maintenance

### If the model is updated:
1. Retrain or fine-tune the model
2. Re-save background data from the new training set: `np.save("shap_bg_ec.npy", X_background)`
3. Update `SHAP_BG_PATH` in `.env` if the file moves
4. Run `pytest tests/test_shap.py` to verify the SHAP pipeline still functions

### If SHAP is consistently returning errors:
1. Check backend startup logs for `"SHAP background file not found"` or `"SHAP explanation failed"`
2. Verify `shap_bg_ec.npy` exists at the path in `SHAP_BG_PATH`
3. Verify the SHAP shape matches — must be `(n_epochs, 1280, 19)` after preprocessing
4. Try running `data/predict_one_edf_shap.py` directly to isolate backend vs. API issues

### Adding new SHAP tests:
- All SHAP tests are in `backend/tests/test_shap.py`
- Mock `shap.GradientExplainer`, `get_model`, and `get_shap_background` to avoid running real TF during CI/CD
- Always verify all 19 channels appear in `feature_importance`

---

## Testing

```bash
# Run all SHAP tests
cd backend
py -m pytest tests/test_shap.py -v

# Run all prediction + SHAP tests together
py -m pytest tests/test_shap.py tests/test_predictions.py tests/test_services.py -v
```

**Test coverage:**
- `_empty_explanation()` contract (5 tests)
- `format_explanation()` JSON safety, base_value, numpy conversion (5 tests)
- `generate_shap_explanation()` structure, channels, values, edge cases (10 tests)
- API `shap_status` propagation (3 integration tests)
- `ShapExplanation` Pydantic schema (4 tests)

---

## Files Changed (Fix Summary)

| File | Change |
|------|--------|
| `backend/app/schemas/prediction.py` | Added `base_value: float` and `shap_status: str` to `ShapExplanation` |
| `backend/app/routes/predictions.py` | Sets `shap_status: "success"` on success; `"error"` in fallback with error message |
| `backend/app/services/shap_explainer.py` | No changes — logic was already correct |
| `frontend/src/services/api.ts` | Added `base_value` and `shap_status` to `ShapExplanation` interface |
| `frontend/src/components/SHAPVisualization.tsx` | **Removed fake fallback data**; added proper error/unavailable states |
| `backend/tests/test_shap.py` | New — 27 dedicated SHAP tests |
| `backend/tests/test_predictions.py` | Updated mocks to include `base_value` |
| `backend/tests/conftest.py` | Updated `sample_prediction_data` fixture with `base_value` + `shap_status` |
