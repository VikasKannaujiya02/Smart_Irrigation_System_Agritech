"""TCN + LSTM Hybrid model for time series prediction."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
try:
    import tensorflow as tf
    from tensorflow.keras import layers, Model, Input
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
except ImportError:
    tf = None

    class _MissingTensorFlow:
        class keras:
            class Model:
                pass

    class _MissingLayers:
        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("TensorFlow is required for hybrid model operations")

    def _missing_tensorflow(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("TensorFlow is required for hybrid model operations")

    tf = _MissingTensorFlow()
    layers = _MissingLayers()
    Model = _MissingTensorFlow.keras.Model
    Input = Adam = EarlyStopping = ModelCheckpoint = ReduceLROnPlateau = _missing_tensorflow

from .tcn_model import TCNBlock

logger = logging.getLogger(__name__)


class HybridTCNLSTMModel:
    """Hybrid TCN + LSTM model for irrigation prediction."""

    def __init__(
        self,
        input_shape: Tuple[int, int],
        output_shape: int,
        num_tcn_blocks: int = 3,
        tcn_filters: int = 64,
        kernel_size: int = 3,
        dilation_base: int = 2,
        lstm_units: List[int] = [64],
        dropout_rate: float = 0.2,
        recurrent_dropout: float = 0.1,
        learning_rate: float = 0.001,
        target_names: Optional[List[str]] = None,
        horizon: int = 1,
    ):
        """Initialize hybrid TCN+LSTM model.

        Args:
            input_shape: Shape of input (window_size, n_features).
            output_shape: Number of output features.
            num_tcn_blocks: Number of TCN blocks.
            tcn_filters: Number of filters per TCN block.
            kernel_size: Convolution kernel size.
            dilation_base: Base for dilation rate.
            lstm_units: List of units per LSTM layer.
            dropout_rate: Dropout rate.
            recurrent_dropout: Recurrent dropout rate.
            learning_rate: Learning rate for optimizer.
            target_names: Names of target features.
            horizon: Prediction horizon.
        """
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.num_tcn_blocks = num_tcn_blocks
        self.tcn_filters = tcn_filters
        self.kernel_size = kernel_size
        self.dilation_base = dilation_base
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.recurrent_dropout = recurrent_dropout
        self.learning_rate = learning_rate
        self.target_names = target_names
        self.horizon = horizon
        self._model: Optional[Model] = None
        self._history: Optional[Dict[str, Any]] = None

    def build(self) -> Model:
        """Build and compile the hybrid model.

        Returns:
            Compiled Keras model.
        """
        inputs = Input(shape=self.input_shape, name="hybrid_input")
        x = inputs

        # TCN branch
        tcn_branch = inputs
        for i in range(self.num_tcn_blocks):
            dilation_rate = self.dilation_base ** i
            tcn_branch = TCNBlock(
                filters=self.tcn_filters,
                kernel_size=self.kernel_size,
                dilation_rate=dilation_rate,
                dropout_rate=self.dropout_rate,
            )(tcn_branch)
        tcn_branch = layers.GlobalAveragePooling1D()(tcn_branch)

        # LSTM branch
        lstm_branch = inputs
        for i, units in enumerate(self.lstm_units):
            return_sequences = (i < len(self.lstm_units) - 1)
            lstm_branch = layers.LSTM(
                units=units,
                return_sequences=return_sequences,
                recurrent_dropout=self.recurrent_dropout,
            )(lstm_branch)
            lstm_branch = layers.Dropout(self.dropout_rate)(lstm_branch)
            lstm_branch = layers.BatchNormalization()(lstm_branch)

        # Concatenate branches
        combined = layers.Concatenate()([tcn_branch, lstm_branch])

        # Fully connected layers
        x = layers.Dense(128, activation="relu")(combined)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.BatchNormalization()(x)
        x = layers.Dense(64, activation="relu")(x)
        x = layers.Dropout(self.dropout_rate)(x)

        outputs = layers.Dense(self.output_shape * self.horizon, name="hybrid_output")(x)
        if self.horizon > 1:
            outputs = layers.Reshape((self.horizon, self.output_shape))(outputs)

        model = Model(inputs=inputs, outputs=outputs, name="Hybrid_TCN_LSTM_Prediction_Model")
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss="mse",
            metrics=["mae"],
        )

        self._model = model
        logger.info(f"Hybrid model built: {model.summary()}")
        return model

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        early_stopping_patience: int = 15,
        reduce_lr_patience: int = 8,
        checkpoint_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Train the model.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            epochs: Number of training epochs.
            batch_size: Batch size.
            early_stopping_patience: Patience for early stopping.
            reduce_lr_patience: Patience for learning rate reduction.
            checkpoint_path: Path to save best model.

        Returns:
            Training history.
        """
        if self._model is None:
            self.build()

        callbacks = []

        callbacks.append(
            EarlyStopping(
                monitor="val_loss",
                patience=early_stopping_patience,
                restore_best_weights=True,
                verbose=1,
            )
        )

        callbacks.append(
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=reduce_lr_patience,
                min_lr=1e-7,
                verbose=1,
            )
        )

        if checkpoint_path:
            callbacks.append(
                ModelCheckpoint(
                    checkpoint_path,
                    monitor="val_loss",
                    save_best_only=True,
                    save_weights_only=True,
                    verbose=1,
                )
            )

        history = self._model.fit(
            X_train,
            y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1,
        )

        self._history = history.history
        return self._history

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions.

        Args:
            X: Input features.

        Returns:
            Predictions.
        """
        if self._model is None:
            raise ValueError("Model not built or loaded")

        return self._model.predict(X, verbose=0)

    def save_weights(self, path: str) -> None:
        """Save model weights.

        Args:
            path: Path to save weights.
        """
        if self._model is not None:
            self._model.save_weights(path)

    def load_weights(self, path: str) -> None:
        """Load model weights.

        Args:
            path: Path to weights file.
        """
        if self._model is None:
            self.build()
        self._model.load_weights(path)

    def get_config(self) -> Dict[str, Any]:
        """Get model configuration.

        Returns:
            Configuration dictionary.
        """
        return {
            "input_shape": self.input_shape,
            "output_shape": self.output_shape,
            "num_tcn_blocks": self.num_tcn_blocks,
            "tcn_filters": self.tcn_filters,
            "kernel_size": self.kernel_size,
            "dilation_base": self.dilation_base,
            "lstm_units": self.lstm_units,
            "dropout_rate": self.dropout_rate,
            "recurrent_dropout": self.recurrent_dropout,
            "learning_rate": self.learning_rate,
            "target_names": self.target_names,
            "horizon": self.horizon,
        }
