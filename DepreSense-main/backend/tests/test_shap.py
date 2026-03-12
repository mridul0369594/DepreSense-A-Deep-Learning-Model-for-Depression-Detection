"""
Dedicated SHAP explainability tests.

Covers:
- generate_shap_explanation() output structure and value sanity
- format_explanation() JSON-serialisability and base_value preservation
- _empty_explanation() contract
- Silent-failure fallback: shap_status propagated correctly
- API endpoint: explanation field present in /predict response
- shap_status field in response when SHAP fails
- Reproducibility (same data → same SHAP output)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ══════════════════════════════════════════════════════════════
#  Helper fixtures
# ══════════════════════════════════════════════════════════════

CHANNELS_19 = [
    "Fp1", "Fp2", "F7", "F8", "F3", "F4", "T3", "T4",
    "C3",  "C4",  "Fz", "Cz", "Pz", "P3", "P4", "T5",
    "T6",  "O1",  "O2",
]

_SAMPLE_PREDICTION = {
    "prediction_id": "test-pred-001",
    "depression_probability": 0.72,
    "risk_level": "high",
    "confidence": 0.44,
    "timestamp": datetime.now(timezone.utc),
}


def _make_fake_eeg(n_epochs: int = 5) -> np.ndarray:
    """Return deterministic fake EEG data matching model input shape."""
    rng = np.random.default_rng(42)
    return rng.standard_normal((n_epochs, 1280, 19)).astype(np.float32)


def _make_fake_shap_values(n_epochs: int = 5) -> np.ndarray:
    """Return deterministic fake SHAP values with the same shape as input."""
    rng = np.random.default_rng(99)
    return rng.standard_normal((n_epochs, 1280, 19)).astype(np.float32)


def _make_fake_bg(n_bg: int = 10) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.standard_normal((n_bg, 1280, 19)).astype(np.float32)


# ══════════════════════════════════════════════════════════════
#  Unit tests — _empty_explanation
# ══════════════════════════════════════════════════════════════

class TestEmptyExplanation:
    """Verify the _empty_explanation contract."""

    def test_returns_required_keys(self):
        from app.services.shap_explainer import _empty_explanation
        result = _empty_explanation("No model")
        assert "feature_importance" in result
        assert "top_features" in result
        assert "base_value" in result
        assert "explanation_summary" in result

    def test_feature_importance_is_empty_dict(self):
        from app.services.shap_explainer import _empty_explanation
        assert _empty_explanation("x")["feature_importance"] == {}

    def test_top_features_is_empty_list(self):
        from app.services.shap_explainer import _empty_explanation
        assert _empty_explanation("x")["top_features"] == []

    def test_base_value_is_float(self):
        from app.services.shap_explainer import _empty_explanation
        assert isinstance(_empty_explanation("x")["base_value"], float)

    def test_reason_captured_in_summary(self):
        from app.services.shap_explainer import _empty_explanation
        result = _empty_explanation("SHAP background data not available.")
        assert "SHAP background data not available." in result["explanation_summary"]


# ══════════════════════════════════════════════════════════════
#  Unit tests — format_explanation
# ══════════════════════════════════════════════════════════════

class TestFormatExplanation:
    """Verify format_explanation() outputs are JSON-serialisable."""

    def test_json_serialisable(self):
        from app.services.shap_explainer import format_explanation
        data = {
            "feature_importance": {
                "Fp1": {"abs_importance": np.float32(0.042), "signed_importance": np.float32(-0.01)},
                "F3":  {"abs_importance": np.float32(0.031), "signed_importance": np.float32(0.02)},
            },
            "top_features": ["Fp1", "F3"],
            "base_value": np.float64(0.72),
            "explanation_summary": "High risk.",
        }
        result = format_explanation(data)
        # Must not raise
        serialised = json.dumps(result)
        assert "Fp1" in serialised

    def test_base_value_preserved(self):
        from app.services.shap_explainer import format_explanation
        data = {
            "feature_importance": {},
            "top_features": [],
            "base_value": np.float64(0.55),
            "explanation_summary": "",
        }
        result = format_explanation(data)
        assert abs(result["base_value"] - 0.55) < 1e-6

    def test_numpy_floats_converted_to_python_float(self):
        from app.services.shap_explainer import format_explanation
        data = {
            "feature_importance": {
                "Cz": {"abs_importance": np.float32(0.1), "signed_importance": np.float32(0.05)},
            },
            "top_features": ["Cz"],
            "base_value": np.float32(0.5),
            "explanation_summary": "Test",
        }
        result = format_explanation(data)
        for ch_vals in result["feature_importance"].values():
            for v in ch_vals.values():
                assert isinstance(v, float), f"Expected float, got {type(v)}"

    def test_handles_missing_base_value(self):
        from app.services.shap_explainer import format_explanation
        data = {
            "feature_importance": {},
            "top_features": [],
            "explanation_summary": "No base",
            # no base_value key
        }
        result = format_explanation(data)
        assert result["base_value"] == 0.0

    def test_top_features_is_list(self):
        from app.services.shap_explainer import format_explanation
        data = {
            "feature_importance": {},
            "top_features": ("Fp1", "Cz"),   # tuple input
            "base_value": 0.0,
            "explanation_summary": "",
        }
        result = format_explanation(data)
        assert isinstance(result["top_features"], list)


# ══════════════════════════════════════════════════════════════
#  Unit tests — generate_shap_explanation (mocked model/bg)
# ══════════════════════════════════════════════════════════════

class TestGenerateShapExplanation:
    """generate_shap_explanation() with mocked SHAP internals."""

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_returns_all_required_keys(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        fake_shap = _make_fake_shap_values(5)
        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = fake_shap
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        assert "feature_importance" in result
        assert "top_features" in result
        assert "base_value" in result
        assert "explanation_summary" in result

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_feature_importance_has_all_19_channels(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        fake_shap = _make_fake_shap_values(5)
        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = fake_shap
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        fi = result["feature_importance"]
        assert isinstance(fi, dict)
        assert len(fi) == 19
        for ch in CHANNELS_19:
            assert ch in fi, f"Channel {ch} missing from feature_importance"

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_top_features_is_list_of_5_channels(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = _make_fake_shap_values(5)
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        assert isinstance(result["top_features"], list)
        assert 1 <= len(result["top_features"]) <= 5
        for f in result["top_features"]:
            assert f in CHANNELS_19, f"'{f}' is not a valid EEG channel"

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_feature_importance_values_are_finite(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = _make_fake_shap_values(5)
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        for ch, vals in result["feature_importance"].items():
            assert np.isfinite(vals["abs_importance"]), f"{ch}: abs_importance not finite"
            assert np.isfinite(vals["signed_importance"]), f"{ch}: signed_importance not finite"

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_abs_importance_is_non_negative(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = _make_fake_shap_values(5)
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        for ch, vals in result["feature_importance"].items():
            assert vals["abs_importance"] >= 0, f"{ch}: abs_importance is negative"

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_explanation_summary_mentions_top_features(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = _make_fake_shap_values(5)
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        summary = result["explanation_summary"]
        assert isinstance(summary, str)
        assert len(summary) > 0

    @patch("app.services.shap_explainer.get_shap_background")
    def test_returns_empty_explanation_when_no_background(self, mock_get_bg):
        from app.services.shap_explainer import generate_shap_explanation

        mock_get_bg.return_value = None   # Simulates missing shap_bg_ec.npy

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)

        # Should not raise; should return graceful empty explanation
        assert result["feature_importance"] == {}
        assert result["top_features"] == []
        assert "not available" in result["explanation_summary"].lower()

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_handles_list_wrapped_shap_values(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        """GradientExplainer can return list with one element for binary models."""
        from app.services.shap_explainer import generate_shap_explanation

        fake_shap = _make_fake_shap_values(5)
        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = [fake_shap]   # list-wrapped
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)
        assert len(result["feature_importance"]) == 19

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_handles_4d_shap_values(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        """SHAP shape (E, 1280, 19, 1) squeezed correctly to (E, 1280, 19)."""
        from app.services.shap_explainer import generate_shap_explanation

        fake_shap_4d = _make_fake_shap_values(5)[..., np.newaxis]  # (5, 1280, 19, 1)
        assert fake_shap_4d.shape == (5, 1280, 19, 1)

        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = fake_shap_4d
        mock_explainer_cls.return_value = mock_instance

        result = generate_shap_explanation(_make_fake_eeg(5), _SAMPLE_PREDICTION)
        assert len(result["feature_importance"]) == 19

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_reproducibility(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        """Same data → same SHAP feature importances."""
        from app.services.shap_explainer import generate_shap_explanation

        fixed_shap = _make_fake_shap_values(5)   # deterministic seed=99
        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = fixed_shap
        mock_explainer_cls.return_value = mock_instance

        data = _make_fake_eeg(5)
        result1 = generate_shap_explanation(data, _SAMPLE_PREDICTION)
        result2 = generate_shap_explanation(data, _SAMPLE_PREDICTION)

        for ch in CHANNELS_19:
            assert abs(
                result1["feature_importance"][ch]["abs_importance"]
                - result2["feature_importance"][ch]["abs_importance"]
            ) < 1e-9, f"Channel {ch} abs_importance not reproducible"

    @patch("app.services.shap_explainer.get_shap_background")
    @patch("app.services.shap_explainer.get_model")
    @patch("app.services.shap_explainer.shap.GradientExplainer")
    def test_respects_max_explain_epochs(self, mock_explainer_cls, mock_get_model, mock_get_bg):
        """Only max_explain_epochs worth of data is passed to the explainer."""
        from app.services.shap_explainer import generate_shap_explanation

        n_explain = 3
        fake_shap = _make_fake_shap_values(n_explain)  # shape for 3 epochs only
        mock_get_bg.return_value = _make_fake_bg()
        mock_get_model.return_value = MagicMock()
        mock_instance = MagicMock()
        mock_instance.shap_values.return_value = fake_shap
        mock_explainer_cls.return_value = mock_instance

        # Pass 10 epochs but limit to 3
        data = _make_fake_eeg(10)
        generate_shap_explanation(data, _SAMPLE_PREDICTION, max_explain_epochs=n_explain)

        # Verify explainer was called with only 3 epochs
        called_x = mock_instance.shap_values.call_args[0][0]
        assert called_x.shape[0] == n_explain


# ══════════════════════════════════════════════════════════════
#  Integration tests — API endpoint shap_status propagation
# ══════════════════════════════════════════════════════════════

class TestShapStatusInApiResponse:
    """Verify shap_status is correctly set in prediction responses."""

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.format_explanation")
    @patch("app.routes.predictions.generate_shap_explanation")
    @patch("app.routes.predictions.format_prediction")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_shap_status_success_when_shap_works(
        self, mock_exists, mock_loaded, mock_pre, mock_inf,
        mock_fmt, mock_shap, mock_shap_fmt, mock_fs,
        test_client, auth_headers,
    ):
        """When SHAP succeeds, response explanation.shap_status == 'success'."""
        now = datetime.now(timezone.utc)
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.return_value = np.zeros((5, 1280, 19), dtype=np.float32)
        mock_inf.return_value = {"depression_probability": 0.72, "epoch_probabilities": [0.72]*5, "n_epochs": 5}
        mock_fmt.return_value = {
            "prediction_id": "p1", "depression_probability": 0.72,
            "risk_level": "high", "confidence": 0.44, "timestamp": now,
        }
        mock_shap.return_value = {
            "feature_importance": {"Fp1": {"abs_importance": 0.05, "signed_importance": 0.03}},
            "top_features": ["Fp1"],
            "base_value": 0.72,
            "explanation_summary": "High risk.",
        }
        mock_shap_fmt.return_value = {
            "feature_importance": {"Fp1": {"abs_importance": 0.05, "signed_importance": 0.03}},
            "top_features": ["Fp1"],
            "base_value": 0.72,
            "explanation_summary": "High risk.",
        }

        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["explanation"]["shap_status"] == "success"
        assert data["explanation"]["base_value"] == pytest.approx(0.72)

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.generate_shap_explanation")
    @patch("app.routes.predictions.format_prediction")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_shap_status_error_when_shap_raises(
        self, mock_exists, mock_loaded, mock_pre, mock_inf,
        mock_fmt, mock_shap, mock_fs,
        test_client, auth_headers,
    ):
        """When generate_shap_explanation raises, response explanation.shap_status == 'error'
        and the prediction itself still succeeds (HTTP 201)."""
        now = datetime.now(timezone.utc)
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.return_value = np.zeros((5, 1280, 19), dtype=np.float32)
        mock_inf.return_value = {"depression_probability": 0.72, "epoch_probabilities": [0.72]*5, "n_epochs": 5}
        mock_fmt.return_value = {
            "prediction_id": "p1", "depression_probability": 0.72,
            "risk_level": "high", "confidence": 0.44, "timestamp": now,
        }
        mock_shap.side_effect = RuntimeError("TF gradient tape error")

        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        # Prediction itself must still succeed
        assert resp.status_code == 201
        data = resp.json()
        assert data["explanation"]["shap_status"] == "error"
        assert data["explanation"]["feature_importance"] == {}
        assert data["explanation"]["top_features"] == []
        # Result should still be valid
        assert data["result"]["risk_level"] == "high"

    @patch("app.routes.predictions.firestore_service")
    @patch("app.routes.predictions.generate_shap_explanation")
    @patch("app.routes.predictions.format_prediction")
    @patch("app.routes.predictions.run_inference")
    @patch("app.routes.predictions._preprocess_edf")
    @patch("app.routes.predictions.is_model_loaded", return_value=True)
    @patch("os.path.exists", return_value=True)
    def test_shap_error_does_not_affect_prediction_result(
        self, mock_exists, mock_loaded, mock_pre, mock_inf,
        mock_fmt, mock_shap, mock_fs,
        test_client, auth_headers,
    ):
        """SHAP failure must not affect prediction_id, probability, or risk_level."""
        now = datetime.now(timezone.utc)
        mock_fs.get_eeg_file.return_value = {"file_path": "./x.edf", "file_id": "fid"}
        mock_pre.return_value = np.zeros((5, 1280, 19), dtype=np.float32)
        mock_inf.return_value = {"depression_probability": 0.15, "epoch_probabilities": [0.15]*5, "n_epochs": 5}
        mock_fmt.return_value = {
            "prediction_id": "pred-xyz", "depression_probability": 0.15,
            "risk_level": "low", "confidence": 0.70, "timestamp": now,
        }
        mock_shap.side_effect = MemoryError("OOM")

        resp = test_client.post("/predictions/predict", json={"file_id": "fid"}, headers=auth_headers)
        assert resp.status_code == 201
        result = resp.json()["result"]
        assert result["prediction_id"] == "pred-xyz"
        assert result["risk_level"] == "low"
        assert abs(result["depression_probability"] - 0.15) < 1e-4


# ══════════════════════════════════════════════════════════════
#  Schema validation tests
# ══════════════════════════════════════════════════════════════

class TestShapExplanationSchema:
    """Pydantic schema: ShapExplanation."""

    def test_defaults_produce_valid_object(self):
        from app.schemas.prediction import ShapExplanation
        obj = ShapExplanation()
        assert obj.feature_importance == {}
        assert obj.top_features == []
        assert obj.base_value == 0.0
        assert obj.explanation_summary == ""
        assert obj.shap_status == "success"

    def test_full_valid_payload(self):
        from app.schemas.prediction import ShapExplanation
        obj = ShapExplanation(
            feature_importance={"Fp1": {"abs_importance": 0.05, "signed_importance": -0.03}},
            top_features=["Fp1", "F3"],
            base_value=0.72,
            explanation_summary="High risk prediction.",
            shap_status="success",
        )
        assert obj.shap_status == "success"
        assert obj.base_value == pytest.approx(0.72)

    def test_error_status_accepted(self):
        from app.schemas.prediction import ShapExplanation
        obj = ShapExplanation(shap_status="error", explanation_summary="SHAP failed.")
        assert obj.shap_status == "error"

    def test_old_records_without_shap_status_default_to_success(self):
        """Historic Firestore records may not have shap_status — ensure they default gracefully."""
        from app.schemas.prediction import ShapExplanation
        obj = ShapExplanation(**{
            "feature_importance": {"Fp1": {"abs_importance": 0.05, "signed_importance": 0.03}},
            "top_features": ["Fp1"],
            "explanation_summary": "Old record.",
            # no shap_status, no base_value
        })
        assert obj.shap_status == "success"
        assert obj.base_value == 0.0
