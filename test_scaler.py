import joblib

try:
    d1 = joblib.load(r'C:\Users\admin\Downloads\Smart_irrigation_system_Agritech\AI-Smart-Irrigation-Digital-Twin\raspberry_pi\ai\models\target_scaler.pkl')
    print('Target features expecting:', d1.n_features_in_)
except Exception as e:
    print('Target scale error:', e)

try:
    d2 = joblib.load(r'C:\Users\admin\Downloads\Smart_irrigation_system_Agritech\AI-Smart-Irrigation-Digital-Twin\raspberry_pi\ai\models\feature_scaler.pkl')
    print('Feature features expecting:', d2.n_features_in_)
except Exception as e:
    print('Feature scaler error:', e)
    
try:
    d3 = joblib.load(r'C:\Users\admin\Downloads\Smart_irrigation_system_Agritech\AI-Smart-Irrigation-Digital-Twin\HYBRID TCN + LSTM MODEL\Models\FINAL_GA_feature_scaler.pkl')
    print('GA features expecting:', d3.n_features_in_)
except Exception as e:
    print('GA scaler error:', e)
