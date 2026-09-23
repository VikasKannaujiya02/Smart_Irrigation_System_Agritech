"""LSTM model for time series prediction."""

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
            raise RuntimeError("TensorFlow is required for LSTM model operations")

    def _missing_tensorflow(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("TensorFlow is required for LSTM model operations")

    tf = _MissingTensorFlow()
    layers = _MissingLayers()
    Model = _MissingTensorFlow.keras.Model
    Input = Adam = EarlyStopping = ModelCheckpoint = ReduceLROnPlateau = _missing_tensorflow

logger = logging.getLogger(__name__)


class LSTMModel:
    """LSTM model for irrigation prediction."""

    def __init__(
        self,
        input_shape: Tuple[int, int],
        output_shape: int,
        lstm_units: List[int] = [128, 64],
        dropout_rate: float = 0.3,
        recurrent_dropout: float = 0.1,
        learning_rate: float = 0.001,
        bidirectional: bool = False,
        target_names: Optional[List[str]] = None,
        horizon: int = 1,
    ):
        """Initialize LSTM model.

        Args:
            input_shape: Shape of input (window_size, n_features).
            output_shape: Number of output features.
            lstm_units: List of units per LSTM layer.
            dropout_rate: Dropout rate.
            recurrent_dropout: Recurrent dropout rate.
            learning_rate: Learning rate for optimizer.
            bidirectional: Whether to use bidirectional LSTM.
            target_names: Names of target features.
            horizon: Prediction horizon.
        """
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.lstm_units = lstm_units
        self.dropout_rate = dropout_rate
        self.recurrent_dropout = recurrent_dropout
        self.learning_rate = learning_rate
        self.bidirectional = bidirectional
        self.target_names = target_names
        self.horizon = horizon
        self._model: Optional[Model] = None
        self._history: Optional[Dict[str, Any]] = None

    def build(self) -> Model:
        """Build and compile the LSTM model.

        Returns:
            Compiled Keras model.
        """
        inputs = Input(shape=self.input_shape, name="lstm_input")
        x = inputs

        for i, units in enumerate(self.lstm_units):
            return_sequences = (i < len(self.lstm_units) - 1)

            if self.bidirectional:
                x = layers.Bidirectional(
                    layers.LSTM(
                        units=units,
                        return_sequences=return_sequences,
                        recurrent_dropout=self.recurrent_dropout,
                    )
                )(x)
            else:
                x = layers.LSTM(
                    units=units,
                    return_sequences=return_sequences,
                    recurrent_dropout=self.recurrent_dropout,
                )(x)

            x = layers.Dropout(self.dropout_rate)(x)
            x = layers.BatchNormalization()(x)

        x = layers.Dense(128, activation="relu")(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(64, activation="relu")(x)

        outputs = layers.Dense(self.output_shape * self.horizon, name="lstm_output")(x)
        if self.horizon > 1:
            outputs = layers.Reshape((self.horizon, self.output_shape))(outputs)

        model = Model(inputs=inputs, outputs=outputs, name="LSTM_Prediction_Model")
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss="mse",
            metrics=["mae"],
        )

        self._model = model
        logger.info(f"LSTM model built: {model.summary()}")
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

        # Early stopping
        callbacks.append(
            EarlyStopping(
                monitor="val_loss",
                patience=early_stopping_patience,
                restore_best_weights=True,
                verbose=1,
            )
        )

        # Reduce learning rate on plateau
        callbacks.append(
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=reduce_lr_patience,
                min_lr=1e-7,
                verbose=1,
            )
        )

        # Model checkpoint
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
            "lstm_units": self.lstm_units,
            "dropout_rate": self.dropout_rate,
            "recurrent_dropout": self.recurrent_dropout,
            "learning_rate": self.learning_rate,
            "bidirectional": self.bidirectional,
            "target_names": self.target_names,
            "horizon": self.horizon,
        }
