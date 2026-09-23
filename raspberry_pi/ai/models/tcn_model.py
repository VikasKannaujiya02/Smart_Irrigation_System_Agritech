"""TCN (Temporal Convolutional Network) model for time series prediction."""

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
        Tensor = Any

        class keras:
            class Model:
                pass

        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("TensorFlow is required for TCN model operations")

    class _MissingLayers:
        class Layer:
            pass

        def __getattr__(self, name: str) -> Any:
            raise RuntimeError("TensorFlow is required for TCN model operations")

    def _missing_tensorflow(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("TensorFlow is required for TCN model operations")

    tf = _MissingTensorFlow()
    layers = _MissingLayers()
    Model = _MissingTensorFlow.keras.Model
    Input = Adam = EarlyStopping = ModelCheckpoint = ReduceLROnPlateau = _missing_tensorflow

logger = logging.getLogger(__name__)


class TCNBlock(layers.Layer):
    """TCN residual block with dilated causal convolutions."""

    def __init__(
        self,
        filters: int,
        kernel_size: int,
        dilation_rate: int,
        dropout_rate: float = 0.2,
        activation: str = "relu",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.filters = filters
        self.kernel_size = kernel_size
        self.dilation_rate = dilation_rate
        self.dropout_rate = dropout_rate
        self.activation = activation

        self.conv1 = layers.Conv1D(
            filters=filters,
            kernel_size=kernel_size,
            dilation_rate=dilation_rate,
            padding="causal",
            activation=activation,
        )
        self.batch_norm1 = layers.BatchNormalization()
        self.dropout1 = layers.SpatialDropout1D(dropout_rate)

        self.conv2 = layers.Conv1D(
            filters=filters,
            kernel_size=kernel_size,
            dilation_rate=dilation_rate,
            padding="causal",
            activation=activation,
        )
        self.batch_norm2 = layers.BatchNormalization()
        self.dropout2 = layers.SpatialDropout1D(dropout_rate)

        self.conv_residual = None

    def build(self, input_shape: Tuple[int, ...]) -> None:
        if input_shape[-1] != self.filters:
            self.conv_residual = layers.Conv1D(
                filters=self.filters,
                kernel_size=1,
                padding="same",
            )

    def call(self, inputs: tf.Tensor, training: bool = False) -> tf.Tensor:
        x = self.conv1(inputs)
        x = self.batch_norm1(x, training=training)
        x = self.dropout1(x, training=training)
        x = self.conv2(x)
        x = self.batch_norm2(x, training=training)
        x = self.dropout2(x, training=training)

        if self.conv_residual is not None:
            residual = self.conv_residual(inputs)
        else:
            residual = inputs

        x = layers.Add()([x, residual])
        x = layers.Activation(self.activation)(x)
        return x

    def get_config(self) -> Dict[str, Any]:
        config = super().get_config()
        config.update({
            "filters": self.filters,
            "kernel_size": self.kernel_size,
            "dilation_rate": self.dilation_rate,
            "dropout_rate": self.dropout_rate,
            "activation": self.activation,
        })
        return config


class TCNModel:
    """TCN model for irrigation prediction."""

    def __init__(
        self,
        input_shape: Tuple[int, int],
        output_shape: int,
        num_blocks: int = 4,
        filters: int = 64,
        kernel_size: int = 3,
        dilation_base: int = 2,
        dropout_rate: float = 0.2,
        learning_rate: float = 0.001,
        target_names: Optional[List[str]] = None,
        horizon: int = 1,
    ):
        """Initialize TCN model.

        Args:
            input_shape: Shape of input (window_size, n_features).
            output_shape: Number of output features.
            num_blocks: Number of TCN blocks.
            filters: Number of filters per block.
            kernel_size: Convolution kernel size.
            dilation_base: Base for dilation rate (dilation_rate = dilation_base^i).
            dropout_rate: Dropout rate.
            learning_rate: Learning rate for optimizer.
            target_names: Names of target features.
            horizon: Prediction horizon.
        """
        self.input_shape = input_shape
        self.output_shape = output_shape
        self.num_blocks = num_blocks
        self.filters = filters
        self.kernel_size = kernel_size
        self.dilation_base = dilation_base
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        self.target_names = target_names
        self.horizon = horizon
        self._model: Optional[Model] = None
        self._history: Optional[Dict[str, Any]] = None

    def build(self) -> Model:
        """Build and compile the TCN model.

        Returns:
            Compiled Keras model.
        """
        inputs = Input(shape=self.input_shape, name="tcn_input")
        x = inputs

        for i in range(self.num_blocks):
            dilation_rate = self.dilation_base ** i
            x = TCNBlock(
                filters=self.filters,
                kernel_size=self.kernel_size,
                dilation_rate=dilation_rate,
                dropout_rate=self.dropout_rate,
            )(x)

        x = layers.GlobalAveragePooling1D()(x)
        x = layers.Dense(128, activation="relu")(x)
        x = layers.Dropout(self.dropout_rate)(x)
        x = layers.Dense(64, activation="relu")(x)

        outputs = layers.Dense(self.output_shape * self.horizon, name="tcn_output")(x)
        if self.horizon > 1:
            outputs = layers.Reshape((self.horizon, self.output_shape))(outputs)

        model = Model(inputs=inputs, outputs=outputs, name="TCN_Prediction_Model")
        model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss="mse",
            metrics=["mae"],
        )

        self._model = model
        logger.info(f"TCN model built: {model.summary()}")
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
            "num_blocks": self.num_blocks,
            "filters": self.filters,
            "kernel_size": self.kernel_size,
            "dilation_base": self.dilation_base,
            "dropout_rate": self.dropout_rate,
            "learning_rate": self.learning_rate,
            "target_names": self.target_names,
            "horizon": self.horizon,
        }
