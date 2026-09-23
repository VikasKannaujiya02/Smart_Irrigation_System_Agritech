import pandas as pd
import sqlite3
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_dataset(db_path="c:/Users/admin/Downloads/Smart_irrigation_system_Agritech/AI-Smart-Irrigation-Digital-Twin/data/sqlite/irrigation.db",
                     output_csv="c:/Users/admin/Downloads/Smart_irrigation_system_Agritech/AI-Smart-Irrigation-Digital-Twin/GA_GAT_TCN_LSTM_FINAL_DATASET.csv"):
    
    logger.info(f"Connecting to database at {db_path}")
    conn = sqlite3.connect(db_path)
    
    # Load Sensor Data
    sensor_df = pd.read_sql_query("SELECT recorded_at, device_id, soil_moisture_percent, temperature_c, humidity_percent FROM SensorData", conn)
    sensor_df["recorded_at"] = pd.to_datetime(sensor_df["recorded_at"])
    
    # Load Weather Data
    weather_df = pd.read_sql_query("SELECT recorded_at, temperature_c as weather_temp, humidity_percent as weather_hum, rainfall_mm, wind_speed_mps FROM WeatherHistory", conn)
    weather_df["recorded_at"] = pd.to_datetime(weather_df["recorded_at"])
    
    # We will simulate solar_radiation since it is not in the db
    weather_df["solar_radiation"] = 400.0
    
    conn.close()
    
    if sensor_df.empty:
        logger.warning("No sensor data found! Output will be empty.")
        return
        
    logger.info("Processing sensor data nodes")
    # Device ID 3 is Node 2. Others are Node 1.
    node1_df = sensor_df[sensor_df['device_id'] != 3].copy()
    node2_df = sensor_df[sensor_df['device_id'] == 3].copy()
    
    # Round timestamps to nearest 15 seconds to align them perfectly
    node1_df['timestamp'] = node1_df['recorded_at'].dt.round('15S')
    node2_df['timestamp'] = node2_df['recorded_at'].dt.round('15S')
    
    # Aggregate in case of multiple packets in the same 15s window
    node1_agg = node1_df.groupby('timestamp').agg({
        'soil_moisture_percent': 'mean',
        'temperature_c': 'mean',
        'humidity_percent': 'mean'
    }).rename(columns={'soil_moisture_percent': 'node_1_soil_moisture',
                      'temperature_c': 'temperature',
                      'humidity_percent': 'humidity'})
                      
    node2_agg = node2_df.groupby('timestamp').agg({
        'soil_moisture_percent': 'mean'
    }).rename(columns={'soil_moisture_percent': 'node_2_soil_moisture'})
    
    # Merge Node 1 and Node 2 on the exact 15-second timestamp
    merged_sensor = pd.merge(node1_agg, node2_agg, left_index=True, right_index=True, how='outer')
    
    # Forward fill gaps inside the sensor data so we don't have NaNs if one node misses a packet
    merged_sensor = merged_sensor.ffill().bfill()
    
    logger.info("Processing weather data")
    if not weather_df.empty:
        # Round weather to nearest 15S just in case it aligns, but weather usually comes hourly/daily
        weather_df['timestamp'] = weather_df['recorded_at'].dt.round('15S')
        weather_agg = weather_df.groupby('timestamp').agg({
            'rainfall_mm': 'mean',
            'wind_speed_mps': 'mean',
            'solar_radiation': 'mean',
            # We can also backfill missing temp/humidity from weather if needed, 
            # but usually sensor DHT temp/hum is preferred.
        }).rename(columns={
            'rainfall_mm': 'rainfall',
            'wind_speed_mps': 'wind_speed',
            'solar_radiation': 'solar_radiation'
        })
        
        # Merge weather with the sensor data using an asof merge or outer merge then forward fill
        final_df = pd.merge(merged_sensor, weather_agg, left_index=True, right_index=True, how='left')
        
    else:
        # If no weather in DB, inject zeros/means for weather features
        final_df = merged_sensor
        final_df['rainfall'] = 0.0
        final_df['wind_speed'] = 5.0
        final_df['solar_radiation'] = 400.0
        
    # Forward fill weather elements
    final_df = final_df.ffill().bfill()
    
    # If the user has just started the system, missing columns might exist
    expected_cols = [
        "node_1_soil_moisture",
        "node_2_soil_moisture",
        "temperature",
        "humidity",
        "rainfall",
        "wind_speed",
        "solar_radiation"
    ]
    for col in expected_cols:
        if col not in final_df.columns:
            final_df[col] = 0.0
    
    # Ensure exact 7 feature ordering the model expects
    final_df = final_df[expected_cols]
    final_df.reset_index(inplace=True)
    
    logger.info(f"Saving dataset with {len(final_df)} rows to {output_csv}")
    final_df.to_csv(output_csv, index=False)
    logger.info("Done.")

if __name__ == "__main__":
    generate_dataset()
