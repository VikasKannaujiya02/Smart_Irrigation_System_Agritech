import pandas as pd
import numpy as npfrom google.colab import drive
drive.mount('/content/drive')from google.colab import drive
drive.mount('/content/drive')import os

BASE = "/content/drive/MyDrive/TCN_Irrigation_Project"

print(os.listdir(BASE))import os

print(os.listdir("/content/drive"))
print(os.listdir("/content/drive/MyDrive"))print(os.listdir(BASE + "/Data"))import pandas as pd

# Project Base Path
BASE = "/content/drive/MyDrive/TCN_Irrigation_Project"

# ==========================
# NASA Weather Dataset (2001–2025)
# ==========================
# Correctly parse the 'date' column from YYYYMMDD string format
weather = pd.read_csv(f"{BASE}/Data/india_weather_25yr.csv", parse_dates=['date'], date_format='%Y%m%d')

print("=" * 60)
print("NASA Weather Dataset")
print("=" * 60)
print("Shape :", weather.shape)
print("Columns:")
print(weather.columns.tolist())import requests
import pandas as pd
import time

cities = {
    "Lucknow": (26.8467, 80.9462),
    "Delhi": (28.7041, 77.1025),
    "Bhopal": (23.2599, 77.4126),
    "Indore": (22.7196, 75.8577),
    "Kanpur": (26.4499, 80.3319),
    "Ludhiana": (30.9010, 75.8573),
    "Patna": (25.5941, 85.1376),
    "Jaipur": (26.9124, 75.7873),
    "Pune": (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
    "Hyderabad": (17.3850, 78.4867),
    "Bengaluru": (12.9716, 77.5946),
    "Chennai": (13.0827, 80.2707),
    "Ahmedabad": (23.0225, 72.5714),
    "Guwahati": (26.1445, 91.7362),
    "Bhubaneswar": (20.2961, 85.8245),
    "Amritsar": (31.6340, 74.8723),
    "Varanasi": (25.3176, 82.9739),
}

all_dfs = []

for city, (lat, lon) in cities.items():

    url = "https://power.larc.nasa.gov/api/temporal/daily/point"

    params = {
        "parameters":
            "T2M,"
            "T2M_MAX,"
            "T2M_MIN,"
            "T2MDEW,"
            "RH2M,"
            "PRECTOTCORR,"
            "WS2M,"
            "PS,"
            "ALLSKY_SFC_SW_DWN,"
            "GWETTOP,"
            "GWETROOT,"
            "EVLAND",

        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": "20010101",
        "end": "20260630",
        "format": "JSON"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    pdata = response.json()["properties"]["parameter"]

    dfs = [
        pd.DataFrame.from_dict(v, orient="index", columns=[k])
        for k, v in pdata.items()
    ]

    df_city = pd.concat(dfs, axis=1)

    df_city["city"] = city
    df_city.index.name = "date"

    all_dfs.append(df_city.reset_index())

    print(f"Downloaded : {city}")

    time.sleep(1)

india_weather = pd.concat(all_dfs, ignore_index=True)

save_path = "/content/drive/MyDrive/TCN_Irrigation_Project/Data/india_weather_25yr.csv"

india_weather.to_csv(save_path, index=False)

print("\nDataset Saved Successfully!")
print("Shape :", india_weather.shape)
print("Saved At :", save_path)
print(india_weather.head())import pandas as pd

df = pd.read_csv("/content/drive/MyDrive/TCN_Irrigation_Project/Data/india_weather_25yr.csv")

print("="*60)
print("Dataset Shape")
print(df.shape)

print("\nColumns")
print(df.columns.tolist())

print("\nData Types")
print(df.dtypes)

print("\nFirst 5 Rows")
print(df.head())

print("\nLast 5 Rows")
print(df.tail())

print("\nMissing Values")
print(df.isnull().sum())

print("\nDuplicate Rows")
print(df.duplicated().sum())

print("\nStatistics")
print(df.describe())print(df["city"].unique())

print("\nNumber of Cities =", df["city"].nunique())print("Start Date :", df["date"].min())
print("End Date   :", df["date"].max())import pandas as pd
import numpy as np

# Load Dataset
df = pd.read_csv("/content/drive/MyDrive/TCN_Irrigation_Project/Data/india_weather_25yr.csv")

# Convert date
df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")

# Sort data
df = df.sort_values(["city", "date"]).reset_index(drop=True)

# Replace NASA missing values
df.replace(-999, np.nan, inplace=True)

print("Missing Values Before Filling")
print(df.isnull().sum())

# Fill missing values city-wise
numeric_cols = df.select_dtypes(include=["float64","int64"]).columns

df[numeric_cols] = df.groupby("city")[numeric_cols].transform(
    lambda x: x.interpolate(method="linear")
)

# Fill remaining missing values
df.fillna(method="bfill", inplace=True)
df.fillna(method="ffill", inplace=True)

print("\nMissing Values After Filling")
print(df.isnull().sum())

print("\nDataset Shape")
print(df.shape)save_path="/content/drive/MyDrive/TCN_Irrigation_Project/Data/india_weather_clean.csv"

df.to_csv(save_path,index=False)

print("Saved Successfully")
print(save_path)print(df.describe())

print(df.isnull().sum())import matplotlib.pyplot as plt
import seaborn as sns

numeric_df = df.select_dtypes(include=['float64', 'int64'])

plt.figure(figsize=(12,8))
sns.heatmap(numeric_df.corr(),
            annot=True,
            cmap='coolwarm',
            fmt=".2f")

plt.title("Correlation Matrix")
plt.show()numeric_df.hist(figsize=(18,15), bins=30)

plt.tight_layout()

plt.show()plt.figure(figsize=(14,5))

plt.plot(df["date"], df["PRECTOTCORR"])

plt.title("Daily Rainfall")

plt.xlabel("Date")

plt.ylabel("Rainfall (mm/day)")

plt.show()plt.figure(figsize=(14,5))

plt.plot(df["date"], df["T2M"])

plt.title("Temperature")

plt.xlabel("Date")

plt.ylabel("Temperature (°C)")

plt.show()plt.figure(figsize=(14,5))

plt.plot(df["date"], df["GWETROOT"], label="Root Zone")

plt.plot(df["date"], df["GWETTOP"], label="Surface")

plt.legend()

plt.title("Soil Wetness")

plt.show()plt.figure(figsize=(12,6))

df["city"].value_counts().plot(kind="bar")

plt.title("Samples per City")

plt.show()import numpy as np

# Temperature Range
df["TEMP_RANGE"] = df["T2M_MAX"] - df["T2M_MIN"]

# Day of Year
df["DAY_OF_YEAR"] = df["date"].dt.dayofyear

# Month
df["MONTH"] = df["date"].dt.month

# Year
df["YEAR"] = df["date"].dt.yeardf["RAIN_3D"] = df.groupby("city")["PRECTOTCORR"].transform(
    lambda x: x.rolling(3, min_periods=1).sum()
)

df["RAIN_7D"] = df.groupby("city")["PRECTOTCORR"].transform(
    lambda x: x.rolling(7, min_periods=1).sum()
)

df["TEMP_7D"] = df.groupby("city")["T2M"].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)

df["RH_7D"] = df.groupby("city")["RH2M"].transform(
    lambda x: x.rolling(7, min_periods=1).mean()
)df["GWETROOT_LAG1"] = df.groupby("city")["GWETROOT"].shift(1)

df["GWETTOP_LAG1"] = df.groupby("city")["GWETTOP"].shift(1)

df["RAIN_LAG1"] = df.groupby("city")["PRECTOTCORR"].shift(1)df.fillna(method="bfill", inplace=True)
df.fillna(method="ffill", inplace=True)print(df.head())

print(df.shape)

print(df.columns)lucknow = df[df["city"]=="Lucknow"]

plt.figure(figsize=(15,5))
plt.plot(lucknow["date"],lucknow["T2M"])
plt.show()from sklearn.preprocessing import LabelEncoder

# City ko numeric me convert karenge
le = LabelEncoder()

df["CITY_ID"] = le.fit_transform(df["city"])FEATURES = [

    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "T2MDEW",
    "RH2M",
    "PRECTOTCORR",
    "WS2M",
    "PS",
    "ALLSKY_SFC_SW_DWN",
    "EVLAND",

    "TEMP_RANGE",
    "DAY_OF_YEAR",
    "MONTH",
    "YEAR",

    "RAIN_3D",
    "RAIN_7D",

    "TEMP_7D",
    "RH_7D",

    "GWETROOT_LAG1",
    "GWETTOP_LAG1",
    "RAIN_LAG1",

    "CITY_ID"

]

TARGET = [

    "GWETTOP",
    "GWETROOT"

]

X = df[FEATURES]

Y = df[TARGET]print("Input Shape :", X.shape)

print("Target Shape :", Y.shape)

print()

print("Input Features")

print(X.columns.tolist())

print()

print("Targets")

print(Y.columns.tolist())print("Input Shape :", X.shape)

print("Target Shape :", Y.shape)

print()

print("Input Features")

print(X.columns.tolist())

print()

print("Targets")

print(Y.columns.tolist())split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]

X_test = X.iloc[split_index:]

Y_train = Y.iloc[:split_index]

Y_test = Y.iloc[split_index:]

print(X_train.shape)
print(X_test.shape)
print(Y_train.shape)
print(Y_test.shape)from sklearn.preprocessing import MinMaxScaler

feature_scaler = MinMaxScaler()

target_scaler = MinMaxScaler()

X_train_scaled = feature_scaler.fit_transform(X_train)

X_test_scaled = feature_scaler.transform(X_test)

Y_train_scaled = target_scaler.fit_transform(Y_train)

Y_test_scaled = target_scaler.transform(Y_test)print("X Train :", X_train_scaled.shape)

print("X Test  :", X_test_scaled.shape)

print("Y Train :", Y_train_scaled.shape)

print("Y Test  :", Y_test_scaled.shape)import numpy as np

TIME_STEPS = 30

def create_sequences(X, Y, time_steps):

    Xs = []

    Ys = []

    for i in range(len(X) - time_steps):

        Xs.append(X[i:i+time_steps])

        Ys.append(Y[i+time_steps])

    return np.array(Xs), np.array(Ys)X_train_seq, Y_train_seq = create_sequences(
    X_train_scaled,
    Y_train_scaled,
    TIME_STEPS
)

X_test_seq, Y_test_seq = create_sequences(
    X_test_scaled,
    Y_test_scaled,
    TIME_STEPS
)

print(X_train_seq.shape)

print(Y_train_seq.shape)

print(X_test_seq.shape)

print(Y_test_seq.shape)import tensorflow as tf

from tensorflow.keras.models import Sequential

from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Dropout

from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.callbacks import ModelCheckpointprint("TensorFlow Version :", tf.__version__)

print()

print("GPU Available :", tf.config.list_physical_devices('GPU'))model = Sequential([

    LSTM(
        128,
        return_sequences=True,
        input_shape=(X_train_seq.shape[1], X_train_seq.shape[2])
    ),

    Dropout(0.30),

    LSTM(
        64,
        return_sequences=False
    ),

    Dropout(0.30),

    Dense(32, activation="relu"),

    Dense(2)

])

model.summary()model.compile(

    optimizer="adam",

    loss="mse",

    metrics=["mae"]

)early_stop = EarlyStopping(

    monitor="val_loss",

    patience=10,

    restore_best_weights=True

)

reduce_lr = ReduceLROnPlateau(

    monitor="val_loss",

    factor=0.5,

    patience=5,

    verbose=1

)

checkpoint = ModelCheckpoint(

    "best_multi_output_lstm.keras",

    monitor="val_loss",

    save_best_only=True,

    verbose=1

)!nvidia-smi!nvidia-smiimport tensorflow as tf

print(tf.__version__)
print(tf.config.list_physical_devices('GPU'))from tensorflow.keras import Input

model = Sequential([

    Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),

    LSTM(128, return_sequences=True),

    Dropout(0.30),

    LSTM(64),

    Dropout(0.30),

    Dense(32, activation="relu"),

    Dense(2)

])import tensorflow as tf

from tensorflow.keras import Input

from tensorflow.keras.models import Sequential

from tensorflow.keras.layers import LSTM
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Dropout

from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.callbacks import ModelCheckpointmodel = Sequential([

    Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),

    LSTM(128, return_sequences=True),

    Dropout(0.30),

    LSTM(64),

    Dropout(0.30),

    Dense(32, activation="relu"),

    Dense(2)

])

model.summary()print(X_train_seq.shape)import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

# Redefine the LSTM model to ensure it's the one being trained
model = Sequential([
    Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),
    LSTM(128, return_sequences=True),
    Dropout(0.30),
    LSTM(64),
    Dropout(0.30),
    Dense(32, activation="relu"),
    Dense(2)
])

# Compile the model
model.compile(
    optimizer="adam",
    loss="mse",
    metrics=["mae"]
)

# Define the callbacks
early_stop = EarlyStopping(
    monitor="val_loss",
    patience=10,
    restore_best_weights=True
)

reduce_lr = ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.5,
    patience=5,
    verbose=1
)

checkpoint = ModelCheckpoint(
    "best_multi_output_lstm.keras",
    monitor="val_loss",
    save_best_only=True,
    verbose=1
)

history = model.fit(
    X_train_seq,
    Y_train_seq,
    validation_split=0.20,
    epochs=100,
    batch_size=128,
    callbacks=[
        early_stop,
        reduce_lr,
        checkpoint
    ],
    verbose=1
)model.compile(
    optimizer="adam",
    loss="mse",
    metrics=["mae"]
)early_stop = EarlyStopping(
    monitor="val_loss",
    patience=10,
    restore_best_weights=True
)

reduce_lr = ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.5,
    patience=5,
    verbose=1
)

checkpoint = ModelCheckpoint(
    "best_multi_output_lstm.keras",
    monitor="val_loss",
    save_best_only=True,
    verbose=1
)history = model.fit(
    X_train_seq,
    Y_train_seq,
    validation_split=0.20,
    epochs=100,
    batch_size=128,
    callbacks=[
        early_stop,
        reduce_lr,
        checkpoint
    ],
    verbose=1
)history.history.keys()len(history.history['loss'])import os

print(os.path.exists("best_multi_output_lstm.keras"))from tensorflow.keras.models import load_model

best_model = load_model("best_multi_output_lstm.keras")y_pred_scaled = best_model.predict(X_test_seq)y_pred = target_scaler.inverse_transform(y_pred_scaled)

y_true = target_scaler.inverse_transform(Y_test_seq)print("Prediction Shape :", y_pred.shape)
print("Actual Shape     :", y_true.shape)early_stop = EarlyStopping(
    monitor="val_loss",
    patience=20,
    restore_best_weights=True
)model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
    loss="mse",
    metrics=["mae"]
)from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

# GWETTOP
mae_top = mean_absolute_error(y_true[:,0], y_pred[:,0])
rmse_top = np.sqrt(mean_squared_error(y_true[:,0], y_pred[:,0]))
r2_top = r2_score(y_true[:,0], y_pred[:,0])
mape_top = np.mean(np.abs((y_true[:,0] - y_pred[:,0]) / (y_true[:,0] + 1e-8))) * 100

# GWETROOT
mae_root = mean_absolute_error(y_true[:,1], y_pred[:,1])
rmse_root = np.sqrt(mean_squared_error(y_true[:,1], y_pred[:,1]))
r2_root = r2_score(y_true[:,1], y_pred[:,1])
mape_root = np.mean(np.abs((y_true[:,1] - y_pred[:,1]) / (y_true[:,1] + 1e-8))) * 100

print("===== GWETTOP =====")
print(f"MAE  : {mae_top:.4f}")
print(f"RMSE : {rmse_top:.4f}")
print(f"R²   : {r2_top:.4f}")
print(f"MAPE : {mape_top:.2f}%")

print("\n===== GWETROOT =====")
print(f"MAE  : {mae_root:.4f}")
print(f"RMSE : {rmse_root:.4f}")
print(f"R²   : {r2_root:.4f}")
print(f"MAPE : {mape_root:.2f}%")import matplotlib.pyplot as plt

plt.figure(figsize=(8,5))

plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')

plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.title("Training vs Validation Loss")
plt.legend()
plt.grid(True)

plt.show()plt.figure(figsize=(15,5))

plt.plot(y_true[:500,0], label='Actual')
plt.plot(y_pred[:500,0], label='Predicted')

plt.title("GWETTOP Prediction")
plt.xlabel("Samples")
plt.ylabel("GWETTOP")

plt.legend()
plt.grid(True)

plt.show()plt.figure(figsize=(15,5))

plt.plot(y_true[:500,1], label='Actual')
plt.plot(y_pred[:500,1], label='Predicted')

plt.title("GWETROOT Prediction")
plt.xlabel("Samples")
plt.ylabel("GWETROOT")

plt.legend()
plt.grid(True)

plt.show()plt.figure(figsize=(6,6))

plt.scatter(y_true[:,0], y_pred[:,0], alpha=0.3)

plt.plot(
    [y_true[:,0].min(), y_true[:,0].max()],
    [y_true[:,0].min(), y_true[:,0].max()],
    'r--'
)

plt.xlabel("Actual")
plt.ylabel("Predicted")

plt.title("GWETTOP Scatter Plot")

plt.grid(True)

plt.show()plt.figure(figsize=(6,6))

plt.scatter(y_true[:,1], y_pred[:,1], alpha=0.3)

plt.plot(
    [y_true[:,1].min(), y_true[:,1].max()],
    [y_true[:,1].min(), y_true[:,1].max()],
    'r--'
)

plt.xlabel("Actual")
plt.ylabel("Predicted")

plt.title("GWETROOT Scatter Plot")

plt.grid(True)

plt.show()error_top = y_true[:,0] - y_pred[:,0]
error_root = y_true[:,1] - y_pred[:,1]

plt.figure(figsize=(12,5))

plt.subplot(1,2,1)
plt.hist(error_top, bins=50)
plt.title("GWETTOP Error Distribution")

plt.subplot(1,2,2)
plt.hist(error_root, bins=50)
plt.title("GWETROOT Error Distribution")

plt.show()model.save("/content/drive/MyDrive/TCN_Irrigation_Project/Models/LSTM_BASELINE.keras")!pip install keras-tcnfrom tcn import TCN
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
import tensorflow as tftcn_model = Sequential([

    Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),

    TCN(
        nb_filters=64,
        kernel_size=3,
        dilations=[1, 2, 4, 8],
        return_sequences=False
    ),

    Dropout(0.3),

    Dense(32, activation="relu"),

    Dense(2)

])tcn_model.summary()tcn_model.compile(

    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),

    loss="mse",

    metrics=["mae"]

)early_stop = EarlyStopping(
    monitor="val_loss",
    patience=10,
    restore_best_weights=True
)

reduce_lr = ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.5,
    patience=5,
    verbose=1
)

checkpoint = ModelCheckpoint(
    "best_tcn.keras",
    monitor="val_loss",
    save_best_only=True,
    verbose=1
)history_tcn = tcn_model.fit(

    X_train_seq,

    Y_train_seq,

    validation_split=0.2,

    epochs=100,

    batch_size=128,

    callbacks=[
        early_stop,
        reduce_lr,
        checkpoint
    ],

    verbose=1

)from tensorflow.keras.models import load_model

best_tcn = load_model(
    "best_tcn.keras",
    custom_objects={"TCN": TCN}
)y_pred_scaled = best_tcn.predict(X_test_seq)

y_pred = target_scaler.inverse_transform(y_pred_scaled)
y_true = target_scaler.inverse_transform(Y_test_seq)

print("Prediction Shape :", y_pred.shape)
print("Actual Shape     :", y_true.shape)from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

# GWETTOP
mae_top = mean_absolute_error(y_true[:,0], y_pred[:,0])
rmse_top = np.sqrt(mean_squared_error(y_true[:,0], y_pred[:,0]))
r2_top = r2_score(y_true[:,0], y_pred[:,0])
mape_top = np.mean(np.abs((y_true[:,0]-y_pred[:,0])/(y_true[:,0]+1e-8)))*100

# GWETROOT
mae_root = mean_absolute_error(y_true[:,1], y_pred[:,1])
rmse_root = np.sqrt(mean_squared_error(y_true[:,1], y_pred[:,1]))
r2_root = r2_score(y_true[:,1], y_pred[:,1])
mape_root = np.mean(np.abs((y_true[:,1]-y_pred[:,1])/(y_true[:,1]+1e-8)))*100

print("===== GWETTOP =====")
print(f"MAE  : {mae_top:.4f}")
print(f"RMSE : {rmse_top:.4f}")
print(f"R²   : {r2_top:.4f}")
print(f"MAPE : {mape_top:.2f}%")

print("\n===== GWETROOT =====")
print(f"MAE  : {mae_root:.4f}")
print(f"RMSE : {rmse_root:.4f}")
print(f"R²   : {r2_root:.4f}")
print(f"MAPE : {mape_root:.2f}%")tcn_model.save(
    "/content/drive/MyDrive/TCN_Irrigation_Project/Models/TCN_V.keras"
)from tcn import TCN
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input, Dropout
import tensorflow as tf

tcn_model_v2 = Sequential([
    Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),

    TCN(
        nb_filters=128,          # Sirf ye change hai
        kernel_size=3,
        dilations=[1,2,4,8],
        return_sequences=False
    ),

    Dropout(0.3),

    Dense(32, activation="relu"),

    Dense(2)
])

tcn_model_v2.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
    loss="mse",
    metrics=["mae"]
)from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

early_stop = EarlyStopping(
    monitor="val_loss",
    patience=10,
    restore_best_weights=True
)

reduce_lr = ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.5,
    patience=5,
    verbose=1
)

checkpoint = ModelCheckpoint(
    "best_tcn_v2.keras",
    monitor="val_loss",
    save_best_only=True,
    verbose=1
)history_tcn_v2 = tcn_model_v2.fit(
    X_train_seq,
    Y_train_seq,
    validation_split=0.20,
    epochs=100,
    batch_size=128,
    callbacks=[early_stop, reduce_lr, checkpoint],
    verbose=1
)from tensorflow.keras.models import load_model

best_tcn_v2 = load_model(
    "best_tcn_v2.keras",
    custom_objects={"TCN": TCN}
)y_pred_scaled = best_tcn_v2.predict(X_test_seq)

y_pred = target_scaler.inverse_transform(y_pred_scaled)
y_true = target_scaler.inverse_transform(Y_test_seq)from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

# GWETTOP
mae_top = mean_absolute_error(y_true[:,0], y_pred[:,0])
rmse_top = np.sqrt(mean_squared_error(y_true[:,0], y_pred[:,0]))
r2_top = r2_score(y_true[:,0], y_pred[:,0])
mape_top = np.mean(np.abs((y_true[:,0]-y_pred[:,0])/(y_true[:,0]+1e-8)))*100

# GWETROOT
mae_root = mean_absolute_error(y_true[:,1], y_pred[:,1])
rmse_root = np.sqrt(mean_squared_error(y_true[:,1], y_pred[:,1]))
r2_root = r2_score(y_true[:,1], y_pred[:,1])
mape_root = np.mean(np.abs((y_true[:,1]-y_pred[:,1])/(y_true[:,1]+1e-8)))*100

print("===== GWETTOP =====")
print(f"MAE  : {mae_top:.4f}")
print(f"RMSE : {rmse_top:.4f}")
print(f"R²   : {r2_top:.4f}")
print(f"MAPE : {mape_top:.2f}%")

print("\n===== GWETROOT =====")
print(f"MAE  : {mae_root:.4f}")
print(f"RMSE : {rmse_root:.4f}")
print(f"R²   : {r2_root:.4f}")
print(f"MAPE : {mape_root:.2f}%")tcn_model_v2.save(
    "/content/drive/MyDrive/TCN_Irrigation_Project/Models/TCN_V2.keras"
)from tcn import TCN
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout, Input
import tensorflow as tf

tcn_model_v3 = Sequential([

    Input(shape=(X_train_seq.shape[1], X_train_seq.shape[2])),

    TCN(
        nb_filters=128,
        kernel_size=5,
        dilations=[1,2,4,8,16],
        nb_stacks=2,
        dropout_rate=0.2,
        activation="relu",
        use_skip_connections=True,
        return_sequences=False
    ),

    Dense(128, activation="relu"),
    Dropout(0.3),

    Dense(64, activation="relu"),
    Dropout(0.2),

    Dense(32, activation="relu"),

    Dense(2)
])

tcn_model_v3.compile(
    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.0005
    ),
    loss="mse",
    metrics=["mae"]
)

tcn_model_v3.summary()from tensorflow.keras.callbacks import (
    EarlyStopping,
    ReduceLROnPlateau,
    ModelCheckpoint
)

early_stop_v3 = EarlyStopping(
    monitor="val_loss",
    patience=20,
    restore_best_weights=True
)

reduce_lr_v3 = ReduceLROnPlateau(
    monitor="val_loss",
    factor=0.5,
    patience=5,
    verbose=1
)

checkpoint_v3 = ModelCheckpoint(
    "best_tcn_v3.keras",
    monitor="val_loss",
    save_best_only=True,
    verbose=1
)history_tcn_v3 = tcn_model_v3.fit(

    X_train_seq,
    Y_train_seq,

    validation_split=0.20,

    epochs=100,

    batch_size=64,

    callbacks=[
        early_stop_v3,
        reduce_lr_v3,
        checkpoint_v3
    ],

    verbose=1
)from tensorflow.keras.models import load_model

best_tcn_v3 = load_model(

    "best_tcn_v3.keras",

    custom_objects={
        "TCN": TCN
    }

)y_pred_scaled = best_tcn_v3.predict(
    X_test_seq
)

y_pred = target_scaler.inverse_transform(
    y_pred_scaled
)

y_true = target_scaler.inverse_transform(
    Y_test_seq
)from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

import numpy as np

# GWETTOP
mae_top = mean_absolute_error(
    y_true[:,0],
    y_pred[:,0]
)

rmse_top = np.sqrt(
    mean_squared_error(
        y_true[:,0],
        y_pred[:,0]
    )
)

r2_top = r2_score(
    y_true[:,0],
    y_pred[:,0]
)

mape_top = np.mean(
    np.abs(
        (y_true[:,0]-y_pred[:,0])/
        (y_true[:,0]+1e-8)
    )
)*100


# GWETROOT

mae_root = mean_absolute_error(
    y_true[:,1],
    y_pred[:,1]
)

rmse_root = np.sqrt(
    mean_squared_error(
        y_true[:,1],
        y_pred[:,1]
    )
)

r2_root = r2_score(
    y_true[:,1],
    y_pred[:,1]
)

mape_root = np.mean(
    np.abs(
        (y_true[:,1]-y_pred[:,1])/
        (y_true[:,1]+1e-8)
    )
)*100

print("===== GWETTOP =====")
print(f"MAE  : {mae_top:.4f}")
print(f"RMSE : {rmse_top:.4f}")
print(f"R²   : {r2_top:.4f}")
print(f"MAPE : {mape_top:.2f}%")

print("\n===== GWETROOT =====")
print(f"MAE  : {mae_root:.4f}")
print(f"RMSE : {rmse_root:.4f}")
print(f"R²   : {r2_root:.4f}")
print(f"MAPE : {mape_root:.2f}%")tcn_model_v3.save(
    "/content/drive/MyDrive/TCN_Irrigation_Project/Models/TCN_V3.keras"
)from tcn import TCN

import tensorflow as tf

from tensorflow.keras.models import Sequential

from tensorflow.keras.layers import (
    Input,
    Dense,
    Dropout,
    LSTM
)

from tensorflow.keras.callbacks import (
    EarlyStopping,
    ReduceLROnPlateau,
    ModelCheckpoint
)hybrid_model = Sequential([

    Input(shape=(X_train_seq.shape[1],
                 X_train_seq.shape[2])),

    # TCN Layer
    TCN(
        nb_filters=128,
        kernel_size=5,
        dilations=[1,2,4,8,16],
        nb_stacks=2,
        dropout_rate=0.2,
        activation="relu",
        use_skip_connections=True,
        return_sequences=True
    ),

    # LSTM Layer
    LSTM(
        64,
        return_sequences=False
    ),

    Dropout(0.3),

    Dense(
        128,
        activation="relu"
    ),

    Dropout(0.2),

    Dense(
        64,
        activation="relu"
    ),

    Dense(
        32,
        activation="relu"
    ),

    Dense(2)

])

hybrid_model.summary()hybrid_model.compile(

    optimizer=tf.keras.optimizers.Adam(
        learning_rate=0.0005
    ),

    loss="mse",

    metrics=["mae"]

)early_stop_hybrid = EarlyStopping(

    monitor="val_loss",

    patience=20,

    restore_best_weights=True

)

reduce_lr_hybrid = ReduceLROnPlateau(

    monitor="val_loss",

    factor=0.5,

    patience=5,

    verbose=1

)

checkpoint_hybrid = ModelCheckpoint(

    "best_hybrid.keras",

    monitor="val_loss",

    save_best_only=True,

    verbose=1

)history_hybrid = hybrid_model.fit(

    X_train_seq,

    Y_train_seq,

    validation_split=0.20,

    epochs=100,

    batch_size=64,

    callbacks=[

        early_stop_hybrid,

        reduce_lr_hybrid,

        checkpoint_hybrid

    ],

    verbose=1

)from tensorflow.keras.models import load_model

best_hybrid = load_model(
    "best_hybrid.keras",
    custom_objects={"TCN": TCN}
)y_pred_scaled = best_hybrid.predict(X_test_seq)

y_pred = target_scaler.inverse_transform(y_pred_scaled)

y_true = target_scaler.inverse_transform(Y_test_seq)

print(y_pred.shape)
print(y_true.shape)from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score

import numpy as np

# GWETTOP

mae_top = mean_absolute_error(y_true[:,0], y_pred[:,0])

rmse_top = np.sqrt(mean_squared_error(y_true[:,0], y_pred[:,0]))

r2_top = r2_score(y_true[:,0], y_pred[:,0])

mape_top = np.mean(
    np.abs(
        (y_true[:,0]-y_pred[:,0])/
        (y_true[:,0]+1e-8)
    )
)*100


# GWETROOT

mae_root = mean_absolute_error(y_true[:,1], y_pred[:,1])

rmse_root = np.sqrt(mean_squared_error(y_true[:,1], y_pred[:,1]))

r2_root = r2_score(y_true[:,1], y_pred[:,1])

mape_root = np.mean(
    np.abs(
        (y_true[:,1]-y_pred[:,1])/
        (y_true[:,1]+1e-8)
    )
)*100


print("===== GWETTOP =====")
print(f"MAE  : {mae_top:.4f}")
print(f"RMSE : {rmse_top:.4f}")
print(f"R²   : {r2_top:.4f}")
print(f"MAPE : {mape_top:.2f}%")

print()

print("===== GWETROOT =====")
print(f"MAE  : {mae_root:.4f}")
print(f"RMSE : {rmse_root:.4f}")
print(f"R²   : {r2_root:.4f}")
print(f"MAPE : {mape_root:.2f}%")hybrid_model.save(
    "/content/drive/MyDrive/TCN_Irrigation_Project/Models/HYBRID_TCN_LSTM_BASELINE.keras"
)!pip install deapimport random
import numpy as np

from deap import base
from deap import creator
from deap import tools
from deap import algorithms

import tensorflow as tf

from tensorflow.keras.models import Sequential

from tensorflow.keras.layers import (
    Dense,
    Dropout,
    LSTM,
    Input
)

from tensorflow.keras.callbacks import EarlyStopping

from tcn import TCNFILTERS = [64,128,256]

KERNELS = [3,5,7]

LSTM_UNITS = [32,64,128]

DROPOUTS = [0.1,0.2,0.3,0.4]

DENSES = [32,64,128]

LRS = [
0.001,
0.0005,
0.0001
]

BATCHES = [
32,
64,
128
]def build_model(filters,
                kernel,
                lstm_units,
                dropout,
                dense_units,
                lr):

    model = Sequential([

        Input(
            shape=(
                X_train_seq.shape[1],
                X_train_seq.shape[2]
            )
        ),

        TCN(

            nb_filters=filters,

            kernel_size=kernel,

            dilations=[1,2,4,8,16],

            nb_stacks=2,

            dropout_rate=dropout,

            activation="relu",

            use_skip_connections=True,

            return_sequences=True

        ),

        LSTM(
            lstm_units
        ),

        Dropout(dropout),

        Dense(
            dense_units,
            activation="relu"
        ),

        Dense(32,activation="relu"),

        Dense(2)

    ])

    model.compile(

        optimizer=tf.keras.optimizers.Adam(
            learning_rate=lr
        ),

        loss="mse",

        metrics=["mae"]

    )

    return modeldef evaluate(individual):

    filters = FILTERS[individual[0]]

    kernel = KERNELS[individual[1]]

    lstm_units = LSTM_UNITS[individual[2]]

    dropout = DROPOUTS[individual[3]]

    dense_units = DENSES[individual[4]]

    lr = LRS[individual[5]]

    batch = BATCHES[individual[6]]

    model = build_model(

        filters,

        kernel,

        lstm_units,

        dropout,

        dense_units,

        lr

    )

    history = model.fit(

        X_train_seq,

        Y_train_seq,

        validation_split=0.20,

        epochs=5,

        batch_size=batch,

        verbose=0,

        callbacks=[

            EarlyStopping(

                monitor="val_loss",

                patience=2,

                restore_best_weights=True

            )

        ]

    )

    loss = min(history.history["val_loss"])

    return (loss,)# Minimize validation loss

creator.create(
    "FitnessMin",
    base.Fitness,
    weights=(-1.0,)
)

creator.create(
    "Individual",
    list,
    fitness=creator.FitnessMin
)toolbox = base.Toolbox()

toolbox.register(
    "attr_filters",
    random.randint,
    0,
    len(FILTERS)-1
)

toolbox.register(
    "attr_kernel",
    random.randint,
    0,
    len(KERNELS)-1
)

toolbox.register(
    "attr_lstm",
    random.randint,
    0,
    len(LSTM_UNITS)-1
)

toolbox.register(
    "attr_dropout",
    random.randint,
    0,
    len(DROPOUTS)-1
)

toolbox.register(
    "attr_dense",
    random.randint,
    0,
    len(DENSES)-1
)

toolbox.register(
    "attr_lr",
    random.randint,
    0,
    len(LRS)-1
)

toolbox.register(
    "attr_batch",
    random.randint,
    0,
    len(BATCHES)-1
)toolbox.register(

    "individual",

    tools.initCycle,

    creator.Individual,

    (

        toolbox.attr_filters,

        toolbox.attr_kernel,

        toolbox.attr_lstm,

        toolbox.attr_dropout,

        toolbox.attr_dense,

        toolbox.attr_lr,

        toolbox.attr_batch

    ),

    n=1

)

toolbox.register(

    "population",

    tools.initRepeat,

    list,

    toolbox.individual

)toolbox.register(
    "mate",
    tools.cxTwoPoint
)

toolbox.register(
    "mutate",
    tools.mutShuffleIndexes,
    indpb=0.20
)

toolbox.register(
    "select",
    tools.selTournament,
    tournsize=3
)

toolbox.register(
    "evaluate",
    evaluate
)POP_SIZE = 8

GENERATIONS = 5

CXPB = 0.8

MUTPB = 0.2

ELITE_SIZE = 2population = toolbox.population(n=POP_SIZE)

hof = tools.HallOfFame(1)

stats = tools.Statistics(lambda ind: ind.fitness.values)

stats.register("avg", np.mean)

stats.register("min", np.min)

stats.register("max", np.max)population, logbook = algorithms.eaSimple(

    population,

    toolbox,

    cxpb=CXPB,

    mutpb=MUTPB,

    ngen=GENERATIONS,

    stats=stats,

    halloffame=hof,

    verbose=True

)from sklearn.model_selection import train_test_split

# 15% subset for GA optimization
X_ga, _, y_ga, _ = train_test_split(
    X_train_seq,
    Y_train_seq,
    train_size=0.15,
    random_state=42,
    shuffle=True
)

print("GA Training Shape :", X_ga.shape)
print("GA Target Shape   :", y_ga.shape)def evaluate(individual):

    filters = FILTERS[individual[0]]
    kernel = KERNELS[individual[1]]
    lstm_units = LSTM_UNITS[individual[2]]
    dropout = DROPOUTS[individual[3]]
    dense_units = DENSES[individual[4]]
    lr = LRS[individual[5]]
    batch = BATCHES[individual[6]]

    model = build_model(
        filters,
        kernel,
        lstm_units,
        dropout,
        dense_units,
        lr
    )

    history = model.fit(

        X_ga,
        y_ga,

        validation_split=0.20,

        epochs=3,

        batch_size=batch,

        verbose=0,

        callbacks=[
            EarlyStopping(
                monitor="val_loss",
                patience=1,
                restore_best_weights=True
            )
        ]
    )

    return (min(history.history["val_loss"]),)POP_SIZE = 6

GENERATIONS = 4

CXPB = 0.8

MUTPB = 0.2population = toolbox.population(n=POP_SIZE)

hof = tools.HallOfFame(1)

stats = tools.Statistics(lambda ind: ind.fitness.values)

stats.register("avg", np.mean)
stats.register("min", np.min)
stats.register("max", np.max)

population, logbook = algorithms.eaSimple(
    population,
    toolbox,
    cxpb=CXPB,
    mutpb=MUTPB,
    ngen=GENERATIONS,
    stats=stats,
    halloffame=hof,
    verbose=True
)best = hof[0]

print("="*50)
print("Best Chromosome :", best)
print("="*50)

print("Filters       :", FILTERS[best[0]])
print("Kernel Size   :", KERNELS[best[1]])
print("LSTM Units    :", LSTM_UNITS[best[2]])
print("Dropout       :", DROPOUTS[best[3]])
print("Dense Units   :", DENSES[best[4]])
print("Learning Rate :", LRS[best[5]])
print("Batch Size    :", BATCHES[best[6]])import joblib

joblib.dump(feature_scaler, "/content/drive/MyDrive/TCN_Irrigation_Project/Models/feature_scaler.pkl")
joblib.dump(target_scaler, "/content/drive/MyDrive/TCN_Irrigation_Project/Models/target_scaler.pkl")
joblib.dump(le, "/content/drive/MyDrive/TCN_Irrigation_Project/Models/label_encoder.pkl")

print("Saved Successfully")import json

best_config = {
    "filters":128,
    "kernel":3,
    "lstm_units":128,
    "dropout":0.2,
    "dense_units":32,
    "learning_rate":0.001,
    "batch_size":128
}

with open("/content/drive/MyDrive/TCN_Irrigation_Project/Models/best_ga_parameters.json","w") as f:
    json.dump(best_config,f,indent=4)

print("GA Parameters Saved")from tensorflow.keras.models import load_model

model = load_model(
    "/content/drive/MyDrive/TCN_Irrigation_Project/Models/LSTM_BASELINE.keras",
    compile=False
)

model.summary()# ==========================================
# Build Final GA Optimized Hybrid Model
# ==========================================

final_model = build_model(
    filters=128,
    kernel=3,
    lstm_units=128,
    dropout=0.2,
    dense_units=32,
    lr=0.001
)

final_model.summary()from tensorflow.keras.callbacks import (
    EarlyStopping,
    ReduceLROnPlateau,
    ModelCheckpoint
)

checkpoint_path = "/content/drive/.shortcut-targets-by-id/YOUR_FOLDER_ID/TCN_Irrigation_Project/Models/GA_Optimized_Hybrid.keras"import os

for root, dirs, files in os.walk("/content/drive/.shortcut-targets-by-id"):
    if "Models" in dirs:
        print(root)# ==========================================
# Build Final GA Optimized Hybrid Model
# ==========================================

final_model = build_model(
    filters=128,
    kernel=3,
    lstm_units=128,
    dropout=0.2,
    dense_units=32,
    lr=0.001
)

final_model.summary()from tensorflow.keras.callbacks import (
    EarlyStopping,
    ReduceLROnPlateau,
    ModelCheckpoint
)

MODEL_PATH = "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Models/GA_Optimized_Hybrid.keras"

history = final_model.fit(

    X_train_seq,
    Y_train_seq,

    validation_split=0.20,

    epochs=60,

    batch_size=128,

    verbose=1,

    callbacks=[

        EarlyStopping(
            monitor="val_loss",
            patience=10,
            restore_best_weights=True
        ),

        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            verbose=1
        ),

        ModelCheckpoint(
            MODEL_PATH,
            monitor="val_loss",
            save_best_only=True,
            verbose=1
        )
    ]
)import pandas as pd

history_df = pd.DataFrame(history.history)

history_df.to_csv(
    "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/GA_Training_History.csv",
    index=False
)

print("Training History Saved Successfully")from tensorflow.keras.models import load_model
from tcn import TCN

MODEL_PATH = "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Models/GA_Optimized_Hybrid.keras"

best_model = load_model(
    MODEL_PATH,
    custom_objects={"TCN": TCN},
    compile=False
)

print("✅ Best Model Loaded Successfully")import numpy as np

pred_scaled = best_model.predict(X_test_seq)

pred = target_scaler.inverse_transform(pred_scaled)
actual = target_scaler.inverse_transform(Y_test_seq)

print(pred.shape)
print(actual.shape)from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

import numpy as np

target_names = ["GWETTOP", "GWETROOT"]

for i in range(2):

    mae = mean_absolute_error(actual[:, i], pred[:, i])

    rmse = np.sqrt(mean_squared_error(actual[:, i], pred[:, i]))

    r2 = r2_score(actual[:, i], pred[:, i])

    mape = np.mean(
        np.abs((actual[:, i] - pred[:, i]) / actual[:, i])
    ) * 100

    print("=" * 50)
    print(target_names[i])
    print("=" * 50)

    print(f"MAE  : {mae:.4f}")
    print(f"RMSE : {rmse:.4f}")
    print(f"R²   : {r2:.4f}")
    print(f"MAPE : {mape:.2f}%")import matplotlib.pyplot as plt

plt.figure(figsize=(10,6))

plt.plot(history.history["loss"], linewidth=2, label="Training Loss")
plt.plot(history.history["val_loss"], linewidth=2, label="Validation Loss")

plt.xlabel("Epoch", fontsize=12)
plt.ylabel("Loss", fontsize=12)
plt.title("GA Optimized Hybrid Training History", fontsize=14)

plt.grid(True)
plt.legend()

plt.savefig(
"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/Training_Validation_Loss.png",
dpi=300,
bbox_inches="tight"
)

plt.show()import matplotlib.pyplot as plt

plt.figure(figsize=(15,6))

plt.plot(actual[:500,0], label="Actual", linewidth=2)
plt.plot(pred[:500,0], label="Predicted", linewidth=2)

plt.xlabel("Samples")
plt.ylabel("GWETTOP")

plt.title("Actual vs Predicted (GWETTOP)")
plt.legend()
plt.grid(True)

plt.savefig(
"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/GWETTOP_Actual_vs_Predicted.png",
dpi=300,
bbox_inches="tight"
)

plt.show()plt.figure(figsize=(15,6))

plt.plot(actual[:500,1], label="Actual", linewidth=2)
plt.plot(pred[:500,1], label="Predicted", linewidth=2)

plt.xlabel("Samples")
plt.ylabel("GWETROOT")

plt.title("Actual vs Predicted (GWETROOT)")
plt.legend()
plt.grid(True)

plt.savefig(
"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/GWETROOT_Actual_vs_Predicted.png",
dpi=300,
bbox_inches="tight"
)

plt.show()plt.figure(figsize=(8,8))

plt.scatter(actual[:,0], pred[:,0], alpha=0.25)

plt.plot(
[actual[:,0].min(), actual[:,0].max()],
[actual[:,0].min(), actual[:,0].max()],
'k--',
linewidth=2
)

plt.xlabel("Actual")
plt.ylabel("Predicted")

plt.title("Scatter Plot - GWETTOP")

plt.grid(True)

plt.savefig(
"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/GWETTOP_Scatter.png",
dpi=300,
bbox_inches="tight"
)

plt.show()errors = actual[:,0] - pred[:,0]

plt.figure(figsize=(10,6))

plt.hist(errors, bins=60)

plt.title("Prediction Error Distribution")
plt.xlabel("Prediction Error")
plt.ylabel("Frequency")

plt.grid(True)

plt.savefig(
"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/Error_Distribution.png",
dpi=300,
bbox_inches="tight"
)

plt.show()import os
import numpy as np
import pandas as pd

from tensorflow.keras.models import load_model
from tensorflow.keras.metrics import MeanSquaredError
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from tcn import TCN

MODEL_DIR = "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Models"

models = {

    "LSTM Baseline":
        "LSTM_BASELINE.keras",

    "Hybrid TCN-LSTM":
        "HYBRID_TCN_LSTM_BASELINE.keras",

    "GA Optimized Hybrid":
        "GA_Optimized_Hybrid.keras"

}

results = []

for model_name, filename in models.items():

    path = os.path.join(MODEL_DIR, filename)

    print("="*70)
    print(model_name)

    model = load_model(
        path,
        custom_objects={
            "TCN": TCN,
            "mse": MeanSquaredError()
        },
        compile=False
    )

    pred_scaled = model.predict(X_test_seq, verbose=0)

    pred = target_scaler.inverse_transform(pred_scaled)

    actual = target_scaler.inverse_transform(Y_test_seq)

    for i, target in enumerate(["GWETTOP","GWETROOT"]):

        mae = mean_absolute_error(actual[:,i], pred[:,i])

        rmse = np.sqrt(
            mean_squared_error(actual[:,i], pred[:,i])
        )

        r2 = r2_score(actual[:,i], pred[:,i])

        mape = np.mean(
            np.abs(
                (actual[:,i]-pred[:,i])/actual[:,i]
            )
        )*100

        results.append([
            model_name,
            target,
            mae,
            rmse,
            r2,
            mape
        ])

results_df = pd.DataFrame(
    results,
    columns=[
        "Model",
        "Target",
        "MAE",
        "RMSE",
        "R2",
        "MAPE"
    ]
)

results_dfmodels = {

    "LSTM Baseline":
        "LSTM_BASELINE.keras",

    "Best TCN (V3)":
        "TCN_V3.keras",

    "Hybrid TCN-LSTM":
        "HYBRID_TCN_LSTM_BASELINE.keras",

    "GA Optimized Hybrid":
        "GA_Optimized_Hybrid.keras"

}# ==========================================
# Best Model for Each Target
# ==========================================

import pandas as pd

print("\n==============================")
print("BEST MODEL (Lowest MAE)")
print("==============================")

best_mae = results_df.loc[
    results_df.groupby("Target")["MAE"].idxmin()
]

print(best_mae)

print("\n==============================")
print("BEST MODEL (Highest R2)")
print("==============================")

best_r2 = results_df.loc[
    results_df.groupby("Target")["R2"].idxmax()
]

print(best_r2)# ==========================================
# Publication Table
# ==========================================

publication_table = results_df.copy()

publication_table["MAE"] = publication_table["MAE"].round(4)
publication_table["RMSE"] = publication_table["RMSE"].round(4)
publication_table["R2"] = publication_table["R2"].round(4)
publication_table["MAPE"] = publication_table["MAPE"].round(2)

publication_tablepublication_table.to_csv(

"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/Publication_Table.csv",

index=False

)

print("Publication Table Saved Successfully.")pivot_table = publication_table.pivot(

index="Model",
columns="Target",
values=["MAE","RMSE","R2","MAPE"]

)

pivot_tablepivot_table.to_csv(

"/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Results/Research_Paper_Table.csv"

)

print("Research Paper Table Saved Successfully.")import os

MODEL_DIR = "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Models"

for file in sorted(os.listdir(MODEL_DIR)):
    print(file)models = {

    "LSTM Baseline":
        "LSTM_BASELINE.keras",

    "Single TCN":
        "TCN_V3.keras",

    "Hybrid TCN-LSTM":
        "HYBRID_TCN_LSTM_BASELINE.keras",

    "GA Optimized Hybrid":
        "GA_Optimized_Hybrid.keras"

}import os
import numpy as np
import pandas as pd

from tensorflow.keras.models import load_model
from tensorflow.keras.metrics import MeanSquaredError
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from tcn import TCN

MODEL_DIR="/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Models"

models={

"LSTM Baseline":"LSTM_BASELINE.keras",

"Single TCN":"TCN_V3.keras",

"Hybrid TCN-LSTM":"HYBRID_TCN_LSTM_BASELINE.keras",

"GA Optimized Hybrid":"GA_Optimized_Hybrid.keras"

}

results=[]

for model_name,file in models.items():

    print("="*70)
    print(model_name)

    try:

        model=load_model(
            os.path.join(MODEL_DIR,file),
            custom_objects={
                "TCN":TCN,
                "mse":MeanSquaredError()
            },
            compile=False
        )

        pred_scaled=model.predict(X_test_seq,verbose=0)

        pred=target_scaler.inverse_transform(pred_scaled)

        actual=target_scaler.inverse_transform(Y_test_seq)

        for i,target in enumerate(["GWETTOP","GWETROOT"]):

            mae=mean_absolute_error(actual[:,i],pred[:,i])

            rmse=np.sqrt(mean_squared_error(actual[:,i],pred[:,i]))

            r2=r2_score(actual[:,i],pred[:,i])

            mape=np.mean(np.abs((actual[:,i]-pred[:,i])/actual[:,i]))*100

            results.append([
                model_name,
                target,
                mae,
                rmse,
                r2,
                mape
            ])

    except Exception as e:

        print(f"❌ Error : {e}")

results_df=pd.DataFrame(

results,

columns=[
"Model",
"Target",
"MAE",
"RMSE",
"R2",
"MAPE"
]

)

results_dffrom tensorflow.keras.models import load_model
from tensorflow.keras.metrics import MeanSquaredError
from tcn import TCN
import os

MODEL_DIR="/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project/Models"

files=[
"LSTM_BASELINE.keras",
"TCN_V3.keras",
"HYBRID_TCN_LSTM_BASELINE.keras",
"GA_Optimized_Hybrid.keras"
]

for f in files:

    print("="*80)
    print(f)

    model=load_model(
        os.path.join(MODEL_DIR,f),
        custom_objects={
            "TCN":TCN,
            "mse":MeanSquaredError()
        },
        compile=False
    )

    model.summary()import os
import numpy as np
import pandas as pd

from tensorflow.keras.models import load_model
from tensorflow.keras.metrics import MeanSquaredError
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

from tcn import TCN

# ==============================
# PATHS
# ==============================

BASE_DIR = "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project"

MODEL_DIR = os.path.join(BASE_DIR, "Models")
RESULT_DIR = os.path.join(BASE_DIR, "Results")

os.makedirs(RESULT_DIR, exist_ok=True)

# ==============================
# MODELS
# ==============================

models = {

    "LSTM Baseline":
        "LSTM_BASELINE.keras",

    "TCN V2":
        "TCN_V2.keras",

    "TCN V3":
        "TCN_V3.keras",

    "Hybrid TCN-LSTM":
        "HYBRID_TCN_LSTM_BASELINE.keras",

    "GA Optimized Hybrid":
        "GA_Optimized_Hybrid.keras"

}

# ==============================
# EVALUATION
# ==============================

results = []

predictions = {}

actual = target_scaler.inverse_transform(Y_test_seq)

for model_name, file_name in models.items():

    print("=" * 80)
    print(model_name)

    model = load_model(
        os.path.join(MODEL_DIR, file_name),
        custom_objects={
            "TCN": TCN,
            "mse": MeanSquaredError()
        },
        compile=False
    )

    pred_scaled = model.predict(X_test_seq, verbose=0)

    pred = target_scaler.inverse_transform(pred_scaled)

    predictions[model_name] = pred

    for i, target in enumerate(["GWETTOP", "GWETROOT"]):

        mae = mean_absolute_error(actual[:, i], pred[:, i])

        rmse = np.sqrt(mean_squared_error(actual[:, i], pred[:, i]))

        r2 = r2_score(actual[:, i], pred[:, i])

        mape = np.mean(
            np.abs((actual[:, i] - pred[:, i]) / actual[:, i])
        ) * 100

        results.append([
            model_name,
            target,
            mae,
            rmse,
            r2,
            mape
        ])

# ==============================
# RESULTS DATAFRAME
# ==============================

results_df = pd.DataFrame(

    results,

    columns=[
        "Model",
        "Target",
        "MAE",
        "RMSE",
        "R2",
        "MAPE"
    ]

)

# ==============================
# PUBLICATION TABLE
# ==============================

publication_table = results_df.pivot(

    index="Model",
    columns="Target",
    values=["MAE", "RMSE", "R2", "MAPE"]

)

publication_table.columns = [

    f"{metric}_{target}"

    for metric, target in publication_table.columns

]

publication_table = publication_table.round(4)

# ==============================
# SAVE
# ==============================

results_df.to_csv(

    os.path.join(
        RESULT_DIR,
        "Evaluation_Results.csv"
    ),

    index=False

)

publication_table.to_csv(

    os.path.join(
        RESULT_DIR,
        "Publication_Table.csv"
    )

)

publication_table.to_excel(

    os.path.join(
        RESULT_DIR,
        "Publication_Table.xlsx"
    )

)

print("\n")
print("="*80)
print("Evaluation Completed Successfully")
print("="*80)

display(results_df)

print("\nPublication Table\n")

display(publication_table)# Keep only best models for paper

paper_models = [
    "LSTM Baseline",
    "TCN V2",
    "Hybrid TCN-LSTM",
    "GA Optimized Hybrid"
]

paper_results = results_df[
    results_df["Model"].isin(paper_models)
]

paper_table = paper_results.pivot(
    index="Model",
    columns="Target",
    values=["MAE","RMSE","R2","MAPE"]
)

paper_table.columns = [
    f"{m}_{t}" for m, t in paper_table.columns
]

paper_table = paper_table.round(4)

display(paper_table)

paper_table.to_csv(
    os.path.join(RESULT_DIR, "Final_Publication_Table.csv")
)

paper_table.to_excel(
    os.path.join(RESULT_DIR, "Final_Publication_Table.xlsx")
)

print("Final publication table saved.")import matplotlib.pyplot as plt
import os

RESULT_DIR = os.path.join(BASE_DIR, "Results")
os.makedirs(RESULT_DIR, exist_ok=True)

history_dict = {
    # "LSTM_Baseline": history_lstm, # history_lstm was not defined and its content was overwritten by subsequent training runs
    "Best_TCN": history_tcn_v2,
    "Hybrid_TCN_LSTM": history_hybrid,
    "GA_Optimized_Hybrid": history # 'history' now holds the GA Optimized Hybrid training history
}

for name, hist in history_dict.items():

    plt.figure(figsize=(8,5))

    plt.plot(hist.history["loss"], label="Training Loss", linewidth=2)

    plt.plot(hist.history["val_loss"], label="Validation Loss", linewidth=2)

    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title(f"{name} Training History")

    plt.legend()

    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        os.path.join(RESULT_DIR,f"{name}_Loss.png"),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    plt.close()

print("All loss graphs saved.")import matplotlib.pyplot as plt
import os

paper_models = [
    "LSTM Baseline",
    "TCN V2",
    "Hybrid TCN-LSTM",
    "GA Optimized Hybrid"
]

for model_name in paper_models:

    pred = predictions[model_name]

    # GWETTOP
    plt.figure(figsize=(10,5))
    plt.plot(actual[:,0],label="Actual",linewidth=2)
    plt.plot(pred[:,0],label="Predicted",linewidth=2)
    plt.title(f"{model_name} : GWETTOP")
    plt.xlabel("Samples")
    plt.ylabel("GWETTOP")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            RESULT_DIR,
            f"{model_name.replace(' ','_')}_GWETTOP.png"
        ),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()
    plt.close()

    # GWETROOT

    plt.figure(figsize=(10,5))
    plt.plot(actual[:,1],label="Actual",linewidth=2)
    plt.plot(pred[:,1],label="Predicted",linewidth=2)
    plt.title(f"{model_name} : GWETROOT")
    plt.xlabel("Samples")
    plt.ylabel("GWETROOT")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        os.path.join(
            RESULT_DIR,
            f"{model_name.replace(' ','_')}_GWETROOT.png"
        ),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()
    plt.close()

print("Actual vs Predicted graphs saved.")import numpy as np
import matplotlib.pyplot as plt

for model_name in paper_models:

    pred = predictions[model_name]

    for i,target in enumerate(["GWETTOP","GWETROOT"]):

        # Scatter

        plt.figure(figsize=(6,6))

        plt.scatter(actual[:,i],pred[:,i],alpha=0.5)

        plt.plot(
            [actual[:,i].min(),actual[:,i].max()],
            [actual[:,i].min(),actual[:,i].max()],
            'r--'
        )

        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        plt.title(f"{model_name} Scatter ({target})")
        plt.grid(True)
        plt.tight_layout()

        plt.savefig(
            os.path.join(
                RESULT_DIR,
                f"{model_name.replace(' ','_')}_{target}_Scatter.png"
            ),
            dpi=300,
            bbox_inches="tight"
        )

        plt.show()
        plt.close()

        # Residual

        residual = actual[:,i]-pred[:,i]

        plt.figure(figsize=(8,5))

        plt.scatter(pred[:,i],residual,alpha=0.5)

        plt.axhline(0,color="red",linestyle="--")

        plt.xlabel("Predicted")
        plt.ylabel("Residual")
        plt.title(f"{model_name} Residual ({target})")
        plt.grid(True)
        plt.tight_layout()

        plt.savefig(
            os.path.join(
                RESULT_DIR,
                f"{model_name.replace(' ','_')}_{target}_Residual.png"
            ),
            dpi=300,
            bbox_inches="tight"
        )

        plt.show()
        plt.close()

print("Scatter & Residual plots saved.")import matplotlib.pyplot as plt

# Error Distribution

for model_name in paper_models:

    pred = predictions[model_name]

    for i,target in enumerate(["GWETTOP","GWETROOT"]):

        error = actual[:,i]-pred[:,i]

        plt.figure(figsize=(8,5))

        plt.hist(error,bins=30)

        plt.title(f"{model_name} Error Distribution ({target})")

        plt.xlabel("Prediction Error")

        plt.ylabel("Frequency")

        plt.grid(True)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                RESULT_DIR,
                f"{model_name.replace(' ','_')}_{target}_Error_Distribution.png"
            ),
            dpi=300,
            bbox_inches="tight"
        )

        plt.show()
        plt.close()

# ===============================
# Comparison Bar Graphs
# ===============================

metrics=["MAE","RMSE","R2","MAPE"]

for metric in metrics:

    fig,ax=plt.subplots(figsize=(9,5))

    pivot=paper_results.pivot(
        index="Model",
        columns="Target",
        values=metric
    )

    pivot.plot(kind="bar",ax=ax)

    plt.title(f"{metric} Comparison")

    plt.ylabel(metric)

    plt.grid(True)

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            RESULT_DIR,
            f"{metric}_Comparison.png"
        ),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()
    plt.close()

print("All comparison graphs saved.")with pd.ExcelWriter(
    os.path.join(
        RESULT_DIR,
        "Complete_Results.xlsx"
    )
) as writer:

    results_df.to_excel(
        writer,
        sheet_name="All Results",
        index=False
    )

    paper_table.to_excel(
        writer,
        sheet_name="Publication Table"
    )

print("="*70)
print("ALL RESULTS EXPORTED")
print("="*70)

print("Folder :", RESULT_DIR)import numpy as np
import matplotlib.pyplot as plt
import os

paper_models = [
    "LSTM Baseline",
    "TCN V2",
    "Hybrid TCN-LSTM",
    "GA Optimized Hybrid"
]

metrics = ["MAE","RMSE","R2","MAPE"]

paper_df = results_df[results_df["Model"].isin(paper_models)]

summary = paper_df.groupby("Model")[metrics].mean()

# Normalize
norm = summary.copy()

for col in metrics:
    if col=="R2":
        norm[col]=(norm[col]-norm[col].min())/(norm[col].max()-norm[col].min())
    else:
        norm[col]=1-(norm[col]-norm[col].min())/(norm[col].max()-norm[col].min())

labels=metrics
num_vars=len(labels)

angles=np.linspace(0,2*np.pi,num_vars,endpoint=False).tolist()
angles+=angles[:1]

fig,ax=plt.subplots(figsize=(8,8),subplot_kw=dict(polar=True))

for model in norm.index:

    values=norm.loc[model].tolist()
    values+=values[:1]

    ax.plot(angles,values,linewidth=2,label=model)
    ax.fill(angles,values,alpha=0.10)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(labels,fontsize=11)

plt.title("Model Performance Radar Chart",fontsize=14)

plt.legend(loc="upper right",bbox_to_anchor=(1.35,1.10))

plt.tight_layout()

plt.savefig(
    os.path.join(RESULT_DIR,"Radar_Chart.png"),
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Radar Chart Saved")import matplotlib.pyplot as plt

corr=df.corr(numeric_only=True)

plt.figure(figsize=(14,10))

plt.imshow(corr,cmap="coolwarm",aspect="auto")

plt.colorbar()

plt.xticks(
    range(len(corr.columns)),
    corr.columns,
    rotation=90
)

plt.yticks(
    range(len(corr.columns)),
    corr.columns
)

plt.title("Feature Correlation Heatmap")

plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULT_DIR,
        "Correlation_Heatmap.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()

corr.to_csv(
    os.path.join(
        RESULT_DIR,
        "Correlation_Matrix.csv"
    )
)

print("Heatmap Saved")import matplotlib.pyplot as plt

plt.figure(figsize=(12,6))

# Removed history_lstm as it is not defined in the current state
plt.plot(history_tcn_v2.history["val_loss"],label="Best TCN")

plt.plot(history_hybrid.history["val_loss"],label="Hybrid")

# 'history' variable currently holds the GA Optimized Hybrid training history
plt.plot(history.history["val_loss"],label="GA Optimized Hybrid")

plt.xlabel("Epoch")

plt.ylabel("Validation Loss")

plt.title("Validation Loss Comparison")

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULT_DIR,
        "Combined_Learning_Curve.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()

print("Combined Learning Curve Saved")for model in paper_models:

    pred=predictions[model]

    for i,target in enumerate(["GWETTOP","GWETROOT"]):

        plt.figure(figsize=(6,6))

        plt.scatter(actual[:,i],pred[:,i],alpha=0.5)

        m,b=np.polyfit(actual[:,i],pred[:,i],1)

        plt.plot(
            actual[:,i],
            m*actual[:,i]+b,
            linewidth=2
        )

        plt.xlabel("Actual")

        plt.ylabel("Prediction")

        plt.title(f"{model} Regression ({target})")

        plt.grid(True)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                RESULT_DIR,
                f"{model.replace(' ','_')}_{target}_Regression.png"
            ),
            dpi=300,
            bbox_inches="tight"
        )

        plt.show()

        plt.close()

print("Regression Plots Saved")for model in paper_models:

    pred=predictions[model]

    for i,target in enumerate(["GWETTOP","GWETROOT"]):

        mean=(actual[:,i]+pred[:,i])/2

        diff=actual[:,i]-pred[:,i]

        md=np.mean(diff)

        sd=np.std(diff)

        plt.figure(figsize=(7,5))

        plt.scatter(mean,diff,alpha=0.5)

        plt.axhline(md,linestyle="--")

        plt.axhline(md+1.96*sd,linestyle="--")

        plt.axhline(md-1.96*sd,linestyle="--")

        plt.xlabel("Mean")

        plt.ylabel("Difference")

        plt.title(f"{model} Bland-Altman ({target})")

        plt.grid(True)

        plt.tight_layout()

        plt.savefig(
            os.path.join(
                RESULT_DIR,
                f"{model.replace(' ','_')}_{target}_BlandAltman.png"
            ),
            dpi=300,
            bbox_inches="tight"
        )

        plt.show()

        plt.close()

print("Bland-Altman Plots Saved")import os
import numpy as np
import matplotlib.pyplot as plt

try:
    import shap

    print("SHAP Found")

    sample = X_test[:200]

    explainer = shap.Explainer(models["GA Optimized Hybrid"], sample)

    shap_values = explainer(sample)

    plt.figure(figsize=(10,6))

    shap.plots.bar(shap_values,show=False)

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            RESULT_DIR,
            "SHAP_Feature_Importance.png"
        ),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    plt.close()

except Exception as e:

    print("SHAP not available")

    print(e)!pip install skill_metricstry:

    import skill_metrics as sm

    import numpy as np

    ref=actual[:,0]

    plt.figure(figsize=(8,8))

    for model in paper_models:

        pred=predictions[model][:,0]

        sm.taylor_diagram(
            np.std(pred),
            np.corrcoef(ref,pred)[0,1],
            np.sqrt(np.mean((pred-ref)**2)),
            markerLabel=model
        )

    plt.savefig(
        os.path.join(
            RESULT_DIR,
            "Taylor_Diagram.png"
        ),
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()

    plt.close()

except Exception as e:

    print("Install skill_metrics")

    print(e)from graphviz import Digraph
import os

BASE_DIR = "/content/drive/.shortcut-targets-by-id/1adYf6Uu5YJvCx5ZkHlUYg8OX4d_KflEw/TCN_Irrigation_Project"
RESULT_DIR = os.path.join(BASE_DIR, "Results")

dot = Digraph('GA_Hybrid_Model', format='png')

dot.attr(rankdir='LR', fontsize='12')

dot.node('A','Input\n(30 Time Steps)')
dot.node('B','TCN Layers')
dot.node('C','LSTM Layer')
dot.node('D','Dropout')
dot.node('E','Dense Layer')
dot.node('F','Output\nGWETTOP & GWETROOT')

dot.edges([
    ('A','B'),
    ('B','C'),
    ('C','D'),
    ('D','E'),
    ('E','F')
])

save_path=os.path.join(RESULT_DIR,"Model_Architecture")

dot.render(save_path,cleanup=True)

print("Model Architecture Saved")from scipy.stats import ttest_rel
from scipy.stats import wilcoxon

stat_results=[]

reference=predictions["GA Optimized Hybrid"][:,0]

for model in paper_models:

    if model=="GA Optimized Hybrid":

        continue

    pred=predictions[model][:,0]

    t,p1=ttest_rel(reference,pred)

    try:

        w,p2=wilcoxon(reference,pred)

    except:

        w,p2=np.nan,np.nan

    stat_results.append({

        "Model":model,

        "Paired_t_pvalue":p1,

        "Wilcoxon_pvalue":p2

    })

stat_df=pd.DataFrame(stat_results)

display(stat_df)

stat_df.to_csv(

    os.path.join(

        RESULT_DIR,

        "Statistical_Test.csv"

    ),

    index=False

)

stat_df.to_excel(

    os.path.join(

        RESULT_DIR,

        "Statistical_Test.xlsx"

    ),

    index=False

)

print("Statistical Tests Saved")ablation=paper_table.copy()

ablation["Rank_GWETTOP_R2"] = ablation["R2_GWETTOP"].rank(
    ascending=False,
    method="dense"
)
ablation["Rank_GWETROOT_R2"] = ablation["R2_GWETROOT"].rank(
    ascending=False,
    method="dense"
)

display(ablation)

ablation.to_csv(

    os.path.join(

        RESULT_DIR,

        "Ablation_Study.csv"

    ),

    index=False

)

ablation.to_excel(

    os.path.join(

        RESULT_DIR,

        "Ablation_Study.xlsx"

    ),

    index=False

)

print("Ablation Study Saved")import time
import os
from tensorflow.keras.models import load_model
from tensorflow.keras.metrics import MeanSquaredError
from tcn import TCN # Ensure TCN is imported if needed for custom_objects

summary = []

for model_name_key in paper_models: # Iterate through the display names of the models
    filename = models[model_name_key] # Get the corresponding filename from the 'models' dict
    model_path = os.path.join(MODEL_DIR, filename)

    # Load the model with custom objects if necessary
    mdl = load_model(
        model_path,
        custom_objects={
            "TCN": TCN,
            "mse": MeanSquaredError()
        },
        compile=False # Set compile=False if only using for prediction
    )

    start = time.time()

    # Predict using the sequence data
    mdl.predict(
        X_test_seq[:100], # Use X_test_seq for prediction
        verbose=0
    )

    end = time.time()

    inference = (end - start) / 100

    params = mdl.count_params()

    summary.append({
        "Model": model_name_key,
        "Inference_Time(sec/sample)": inference,
        "Parameters": params
    })

speed = pd.DataFrame(summary)

display(speed)

speed.to_csv(
    os.path.join(
        RESULT_DIR,
        "Model_Speed.csv"
    ),
    index=False
)

speed.to_excel(
    os.path.join(
        RESULT_DIR,
        "Model_Speed.xlsx"
    ),
    index=False
)

plt.figure(figsize=(8,5))

plt.bar(
    speed["Model"],
    speed["Inference_Time(sec/sample)"]
)

plt.xticks(rotation=15)

plt.ylabel("Seconds / Sample")

plt.title("Inference Time Comparison")

plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULT_DIR,
        "Inference_Time.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()

print("Inference Analysis Saved")from graphviz import Digraph
import os

flow=Digraph('System',format='png')

flow.attr(rankdir='TB')

flow.node('A','NASA POWER\nWeather Data')

flow.node('B','Preprocessing')

flow.node('C','Feature Engineering')

flow.node('D','TCN-LSTM Model')

flow.node('E','GA Optimization')

flow.node('F','Soil Moisture Prediction')

flow.node('G','Decision Engine')

flow.node('H','LoRa Gateway')

flow.node('I','Raspberry Pi')

flow.node('J','Motor Controller')

flow.node('K','Dashboard')

flow.edges([
('A','B'),
('B','C'),
('C','D'),
('D','E'),
('E','F'),
('F','G'),
('G','H'),
('H','I'),
('I','J'),
('I','K')
])

flow.render(
    os.path.join(
        RESULT_DIR,
        "System_Flowchart"
    ),
    cleanup=True
)

print("Flowchart Saved")import matplotlib.pyplot as plt
import numpy as np
import os

# Redefine paper_models and paper_results for this cell's scope
paper_models = [
    "LSTM Baseline",
    "TCN V2",
    "Hybrid TCN-LSTM",
    "GA Optimized Hybrid"
]

paper_results = results_df[
    results_df["Model"].isin(paper_models)
]

metrics=["MAE","RMSE","R2","MAPE"]

fig,axs=plt.subplots(2,2,figsize=(14,10))

axs=axs.flatten()

for ax,metric in zip(axs,metrics):

    pivot=paper_results.pivot(
        index="Model",
        columns="Target",
        values=metric
    )

    pivot.plot(
        kind="bar",
        ax=ax
    )

    ax.set_title(metric)

    ax.grid(True)

plt.tight_layout()

plt.savefig(
    os.path.join(
        RESULT_DIR,
        "Final_Performance_Summary.png"
    ),
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()

print("Final Summary Figure Saved")import shutil
import os

zip_path=shutil.make_archive(

    os.path.join(BASE_DIR,"Complete_Results"),

    'zip',

    RESULT_DIR

)

print("="*60)

print("ZIP FILE CREATED")

print(zip_path)

print("="*60)from datetime import datetime
import os

# Assuming BASE_DIR and RESULT_DIR are defined in a preceding cell
# If not, they would need to be included here as well
# Example: BASE_DIR = "/content/drive/.shortcut-targets-by-id/YOUR_FOLDER_ID/TCN_Irrigation_Project"
# Example: RESULT_DIR = os.path.join(BASE_DIR, "Results")

# Redefine paper_models for this cell
paper_models = [
    "LSTM Baseline",
    "TCN V2",
    "Hybrid TCN-LSTM",
    "GA Optimized Hybrid"
]

report=open(

    os.path.join(
        RESULT_DIR,
        "Publication_Report.txt"
    ),

    "w"
)

report.write("AI Smart Irrigation Digital Twin\n")

report.write("="*60+"\n")

report.write("Generated : "+str(datetime.now())+"\n\n")

report.write("Models Compared:\n")

for m in paper_models:

    report.write("- "+m+"\n")

report.write("\nEvaluation Metrics:\n")

report.write("- MAE\n")

report.write("- RMSE\n")

report.write("- R2\n")

report.write("- MAPE\n")

report.write("\nFigures Generated:\n")

for file in sorted(os.listdir(RESULT_DIR)):

    if file.endswith(".png"):

        report.write(file+"\n")

report.close()

print("Publication Report Saved")