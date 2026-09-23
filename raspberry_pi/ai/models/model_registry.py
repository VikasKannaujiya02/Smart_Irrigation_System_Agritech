"""Model registry for managing and versioning models."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PyTorchArtifactModel:
    """Adapter for .pth PyTorch artifacts."""

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        self._model = None

    def _load(self) -> None:
        if self._model is None:
            try:
                import torch
                from raspberry_pi.ai.models.gat_tcn_lstm import GAT_TCN_LSTM
            except ImportError as exc:
                raise RuntimeError("PyTorch is required to load the PyTorch artifact") from exc

            self._model = GAT_TCN_LSTM()
            ckpt = torch.load(self.model_path, map_location="cpu", weights_only=False)
            
            # The checkpoint might have 'model_state_dict' inside it
            if "model_state_dict" in ckpt:
                sd = ckpt["model_state_dict"]
                # Map ModuleDict keys appropriately if necessary
                if "gat.W.weight" in sd:
                    sd["gat.W.weight"] = sd.pop("gat.W.weight")
                self._model.load_state_dict(sd, strict=False)
            else:
                self._model.load_state_dict(ckpt)
                
            self._model.eval()

    def predict(self, x):
        """Expects numpy array. Returns numpy array."""
        self._load()
        import torch
        import numpy as np
        
        # x is (batch, 24, 7). Convert to tensor.
        if isinstance(x, np.ndarray):
            x_tensor = torch.tensor(x, dtype=torch.float32)
        else:
            x_tensor = x
            
        with torch.no_grad():
            out = self._model(x_tensor)
            
        return out.cpu().numpy()


class KerasArtifactModel:
    """Adapter for full `.keras` artifacts registered from the reference model repository."""

    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        self._model = None

    def _load(self) -> None:
        if self._model is None:
            try:
                import tensorflow as tf  # type: ignore
            except ImportError as exc:
                raise RuntimeError("TensorFlow is required to load the Hybrid TCN + LSTM artifact") from exc

            custom_objects = {}
            try:
                # The saved artifact was trained using the third-party
                # keras-tcn package's TCN layer (module 'tcn.tcn'), not
                # this project's own TCNBlock in ai/models/tcn_model.py.
                # It must be registered as a custom_object or Keras cannot
                # deserialize the saved model config.
                from tcn import TCN  # type: ignore
                custom_objects["TCN"] = TCN
            except ImportError as exc:
                raise RuntimeError(
                    "The 'keras-tcn' package is required to load this model artifact "
                    "(it uses the TCN layer from that library). Install it with: "
                    "pip install keras-tcn"
                ) from exc

            self._model = tf.keras.models.load_model(self.model_path, custom_objects=custom_objects)

    def predict(self, x):
        self._load()
        return self._model.predict(x, verbose=0)


class ModelVersion:
    """Represents a model version with metadata."""

    def __init__(
        self,
        version: str,
        model_type: str,
        target: str,
        horizon: int,
        created_at: str,
        metrics: Dict[str, Any],
        config: Dict[str, Any],
        model_path: str,
        is_active: bool = False,
    ):
        self.version = version
        self.model_type = model_type
        self.target = target
        self.horizon = horizon
        self.created_at = created_at
        self.metrics = metrics
        self.config = config
        self.model_path = model_path
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "version": self.version,
            "model_type": self.model_type,
            "target": self.target,
            "horizon": self.horizon,
            "created_at": self.created_at,
            "metrics": self.metrics,
            "config": self.config,
            "model_path": self.model_path,
            "is_active": self.is_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModelVersion:
        """Create from dictionary."""
        return cls(
            version=data["version"],
            model_type=data["model_type"],
            target=data["target"],
            horizon=data["horizon"],
            created_at=data["created_at"],
            metrics=data["metrics"],
            config=data["config"],
            model_path=data["model_path"],
            is_active=data.get("is_active", False),
        )


class ModelRegistry:
    """Registry for managing models and versions."""

    def __init__(self, registry_dir: str | Path):
        """Initialize model registry.

        Args:
            registry_dir: Directory to store models and metadata.
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        # registry_dir is always raspberry_pi/ai/models, so 3 levels up is the
        # project root that "HYBRID TCN + LSTM MODEL/..." style relative
        # artifact_path values in registry_metadata.json are anchored to.
        # Without this, relative paths were resolved against the process's
        # current working directory, which broke depending on which
        # directory the script was launched from.
        self._project_root = self.registry_dir.parent.parent.parent
        self._versions: Dict[str, List[ModelVersion]] = {}
        # Cache loaded model adapters so get_model() doesn't re-load from disk on every call
        self._model_cache: Dict[str, Any] = {}
        self._load_versions()

    def _load_versions(self) -> None:
        """Load existing versions from disk."""
        metadata_path = self.registry_dir / "registry_metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                self._versions = {
                    key: [ModelVersion.from_dict(v) for v in versions]
                    for key, versions in data.items()
                }

    def _save_versions(self) -> None:
        """Save versions to disk."""
        data = {
            key: [v.to_dict() for v in versions]
            for key, versions in self._versions.items()
        }
        with open(self.registry_dir / "registry_metadata.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _get_model_key(self, target: str, horizon: int) -> str:
        """Get key for a model type.

        Args:
            target: Prediction target.
            horizon: Prediction horizon.

        Returns:
            Model key.
        """
        return f"{target}_horizon_{horizon}"

    def register_model(
        self,
        model: Any,
        model_type: str,
        target: str,
        horizon: int,
        metrics: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
        set_active: bool = True,
    ) -> str:
        """Register a new model version.

        Args:
            model: Trained model instance.
            model_type: Type of model ('hybrid', 'hybrid_keras', 'keras').
            target: Prediction target.
            horizon: Prediction horizon.
            metrics: Evaluation metrics.
            config: Optional model configuration.
            set_active: Whether to set this version as active.

        Returns:
            Version string.
        """
        version = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = self._get_model_key(target, horizon)
        model_dir = self.registry_dir / key / version
        model_dir.mkdir(parents=True, exist_ok=True)

        # Save model
        model_path = str(model_dir / "model")
        if model_type == "hybrid":
            model.save_weights(model_path + ".h5")

        # Create version
        model_version = ModelVersion(
            version=version,
            model_type=model_type,
            target=target,
            horizon=horizon,
            created_at=datetime.now().isoformat(),
            metrics=metrics,
            config=config or model.get_config(),
            model_path=str(model_dir),
            is_active=set_active,
        )

        # Update registry
        if key not in self._versions:
            self._versions[key] = []

        if set_active:
            for v in self._versions[key]:
                v.is_active = False

        self._versions[key].append(model_version)
        self._save_versions()

        logger.info(f"Registered model {model_type} version {version} for {target} horizon {horizon}")
        return version

    def get_model(
        self,
        target: str,
        horizon: int,
        version: Optional[str] = None,
        model_type: Optional[str] = None,
    ) -> Optional[Any]:
        """Load a model from registry.

        Args:
            target: Prediction target.
            horizon: Prediction horizon.
            version: Optional version (latest active if None).
            model_type: Optional model type filter (e.g. "hybrid", "hybrid_keras",
                "keras"). When provided, only versions of that type are considered,
                so callers that need a specific model type (e.g. a fallback model
                distinct from the primary model) never get handed a different type's
                active version by accident.

        Returns:
            Loaded model instance.
        """
        key = self._get_model_key(target, horizon)
        versions = self._versions.get(key, [])

        if model_type is not None:
            versions = [v for v in versions if v.model_type == model_type]

        if not versions:
            logger.warning(f"No models found for {target} horizon {horizon} model_type {model_type}")
            return None

        if version:
            model_version = next((v for v in versions if v.version == version), None)
        else:
            active = [v for v in versions if v.is_active]
            model_version = active[0] if active else versions[-1]

        if not model_version:
            return None

        # Return cached adapter if available (avoids re-loading .pth/.keras from disk every call)
        cache_key = f"{key}_{model_version.version}_{model_version.model_type}"
        if cache_key in self._model_cache:
            return self._model_cache[cache_key]

        # Load model
        model_path = Path(model_version.model_path)
        if model_version.model_type == "hybrid":
            from .hybrid_model import HybridTCNLSTMModel

            config = model_version.config
            model = HybridTCNLSTMModel(**config)
            model.load_weights(str(model_path / "model.h5"))
        elif model_version.model_type in {"keras", "hybrid_keras"}:
            artifact_path = model_version.config.get("artifact_path") or model_version.model_path
            artifact_path = Path(artifact_path)
            if not artifact_path.is_absolute():
                artifact_path = self._project_root / artifact_path
            model = KerasArtifactModel(artifact_path)
        elif model_version.model_type == "pytorch":
            artifact_path = model_version.config.get("artifact_path") or model_version.model_path
            artifact_path = Path(artifact_path)
            if not artifact_path.is_absolute():
                artifact_path = self._project_root / artifact_path
            model = PyTorchArtifactModel(artifact_path)
        else:
            raise ValueError(f"Unknown model_type: {model_version.model_type!r}")

        logger.info(f"Loaded model {model_version.model_type} version {model_version.version}")
        self._model_cache[cache_key] = model
        return model

    def get_active_version(self, target: str, horizon: int) -> Optional[ModelVersion]:
        """Get active model version.

        Args:
            target: Prediction target.
            horizon: Prediction horizon.

        Returns:
            Active model version.
        """
        key = self._get_model_key(target, horizon)
        versions = self._versions.get(key, [])
        active = [v for v in versions if v.is_active]
        return active[0] if active else None

    def list_versions(self, target: str, horizon: int) -> List[ModelVersion]:
        """List all versions for a model.

        Args:
            target: Prediction target.
            horizon: Prediction horizon.

        Returns:
            List of model versions.
        """
        key = self._get_model_key(target, horizon)
        return self._versions.get(key, [])

    def set_active_version(self, target: str, horizon: int, version: str) -> bool:
        """Set active model version.

        Args:
            target: Prediction target.
            horizon: Prediction horizon.
            version: Version to set as active.

        Returns:
            True if successful.
        """
        key = self._get_model_key(target, horizon)
        versions = self._versions.get(key, [])

        target_version = None
        for v in versions:
            if v.version == version:
                target_version = v
            v.is_active = False

        if target_version:
            target_version.is_active = True
            self._save_versions()
            logger.info(f"Set active version {version} for {target} horizon {horizon}")
            return True

        return False