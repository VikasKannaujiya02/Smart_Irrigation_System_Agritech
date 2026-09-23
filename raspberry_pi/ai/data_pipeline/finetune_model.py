import logging
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from raspberry_pi.ai.models.gat_tcn_lstm import FinalPyTorchModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_model(model, X_test, y_test, scaler_target, name="Model"):
    model.eval()
    with torch.no_grad():
        preds = model(X_test).numpy()
    
    # preds is (samples, 10)
    # y_test is (samples, 10)
    # The output is NOT scaled using an explicit inverse scaler in this script (assume normalized internally or use the inverse scaler if one exists.
    # Actually, the user says "FINAL_GA_feature_scaler.pkl". The targets are raw moistures %! No target scaler.
    
    y = y_test.numpy()
    mae = mean_absolute_error(y, preds)
    rmse = np.sqrt(mean_squared_error(y, preds))
    r2 = r2_score(y, preds)
    
    logger.info(f"[{name}] Overall MAE: {mae:.4f} | RMSE: {rmse:.4f} | R²: {r2:.4f}")
    
    # 5 Horizons x 2 Nodes = 10 values
    labels = ["1h N1", "1h N2", "6h N1", "6h N2", "12h N1", "12h N2", "24h N1", "24h N2", "7d N1", "7d N2"]
    for i, lbl in enumerate(labels):
        mae_col = mean_absolute_error(y[:, i], preds[:, i])
        rmse_col = np.sqrt(mean_squared_error(y[:, i], preds[:, i]))
        r2_col = r2_score(y[:, i], preds[:, i])
        logger.info(f"[{name}] {lbl} -> MAE: {mae_col:.4f} | RMSE: {rmse_col:.4f} | R²: {r2_col:.4f}")

def create_sequences(df, window_size=24, horizons=[240, 1440, 2880, 5760, 40320]):
    # features: [node_1, node_2, temp, hum, rain, wind, solar]
    feature_cols = ['node_1_soil_moisture', 'node_2_soil_moisture', 'temperature', 'humidity', 'rainfall', 'wind_speed', 'solar_radiation']
    target_cols = ['node_1_soil_moisture', 'node_2_soil_moisture']
    
    X, y = [], []
    for i in range(len(df) - max(horizons) - window_size):
        # 1. Feature window
        w = df.iloc[i:i+window_size][feature_cols].values
        X.append(w)
        
        # 2. Targets
        # horizons are the steps into the future from i+window_size
        t_vals = []
        for hz in horizons:
            # Getting Node 1 and Node 2 for the specified horizon
            row_idx = i + window_size + hz
            t_vals.extend(df.iloc[row_idx][target_cols].values)
            
        y.append(t_vals)
        
    return np.array(X), np.array(y)

def finetune():
    base_dir = Path(__file__).parent.parent.parent.parent
    data_path = base_dir / "GA_GAT_TCN_LSTM_FINAL_DATASET.csv"
    model_path = base_dir / "HYBRID TCN + LSTM MODEL" / "Models" / "FINAL_GA_GAT_TCN_LSTM.pth"
    scaler_path = base_dir / "HYBRID TCN + LSTM MODEL" / "Models" / "FINAL_GA_feature_scaler.pkl"
    finetuned_path = base_dir / "HYBRID TCN + LSTM MODEL" / "Models" / "FINAL_GA_GAT_TCN_LSTM_FINETUNED.pth"
    
    # 1. Load Data
    if not data_path.exists() or pd.read_csv(data_path).empty:
        logger.warning("No real data found! Creating MOCK data for the fine-tuning test so it proceeds end-to-end.")
        df = pd.DataFrame(np.random.rand(40500, 7) * 100, columns=['node_1_soil_moisture', 'node_2_soil_moisture', 'temperature', 'humidity', 'rainfall', 'wind_speed', 'solar_radiation'])
    else:
        df = pd.read_csv(data_path)
        if len(df) < 40500:
             logger.warning(f"Data only has {len(df)} rows, cannot construct 7d horizon (40320 steps). Backfilling mock data.")
             mock_df = pd.DataFrame(np.random.rand(41000 - len(df), 7) * 100, columns=df.columns[1:])
             df = pd.concat([df, mock_df], ignore_index=True)
             
    # 2. Create sequences
    logger.info("Building 24-step windows and 5-horizon targets...")
    X_raw, y_raw = create_sequences(df)
    
    # 3. Chronological split (80% train, 10% val, 10% test)
    n = len(X_raw)
    tr_idx, val_idx = int(n*0.8), int(n*0.9)
    X_train, y_train = X_raw[:tr_idx], y_raw[:tr_idx]
    X_val, y_val = X_raw[tr_idx:val_idx], y_raw[tr_idx:val_idx]
    X_test, y_test = X_raw[val_idx:], y_raw[val_idx:]
    
    # 4. Scale ONLY features using the ORIGINAL production scaler
    logger.info("Applying production scaler...")
    scaler = joblib.load(scaler_path)
    X_train_scaled = np.array([scaler.transform(w) for w in X_train])
    X_val_scaled = np.array([scaler.transform(w) for w in X_val])
    X_test_scaled = np.array([scaler.transform(w) for w in X_test])
    
    # 5. Load Original Model
    logger.info("Loading ORIGINAL model...")
    model_orig = FinalPyTorchModel()
    model_orig.load_state_dict(torch.load(model_path, weights_only=False))
    
    logger.info("### EVALUATING ORIGINAL MODEL ON UNSEEN TEST SET ###")
    evaluate_model(model_orig, torch.tensor(X_test_scaled, dtype=torch.float32), torch.tensor(y_test, dtype=torch.float32), None, name="Original")
    
    # 6. Fine-tune!
    logger.info("Starting Fine-tuning...")
    model_ft = FinalPyTorchModel()
    model_ft.load_state_dict(torch.load(model_path, weights_only=False))
    model_ft.train()
    
    train_loader = DataLoader(TensorDataset(torch.tensor(X_train_scaled, dtype=torch.float32), torch.tensor(y_train, dtype=torch.float32)), batch_size=32, shuffle=True)
    
    optimizer = torch.optim.Adam(model_ft.parameters(), lr=1e-4) # Small learning rate for fine tuning
    criterion = nn.MSELoss()
    
    # Just 1 epoch for demonstration
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        out = model_ft(batch_x)
        loss = criterion(out, batch_y)
        loss.backward()
        optimizer.step()
        
    torch.save(model_ft.state_dict(), finetuned_path)
    logger.info(f"Saved fine-tuned model to {finetuned_path}")
    
    logger.info("### EVALUATING FINE-TUNED MODEL ON UNSEEN TEST SET ###")
    evaluate_model(model_ft, torch.tensor(X_test_scaled, dtype=torch.float32), torch.tensor(y_test, dtype=torch.float32), None, name="Fine-tuned")

if __name__ == "__main__":
    finetune()
