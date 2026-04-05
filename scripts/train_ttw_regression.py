"""
RipeRadar V2 - Time-to-Waste (TTW) Regression Model
===================================================
Prevê quantas HORAS uma fruta tem até estar completamente invendável.

Este é um modelo de REGRESSÃO (não classificação) que fornece:
"Em condições atuais, esta prateleira está economicamente viável por 47 horas"

Entrada:
- Features atuais (RGB, gases, textura)
- Timestamp da última manipulação
- Histórico de temperatura/humidade

Saída:
- TTW (horas) com intervalo de confiança
- Trend (horas/dia): está a piorar rápido ou lento?
"""

import numpy as np
import pandas as pd
from pathlib import Path
import joblib
import json
from datetime import datetime, timedelta

# ML Models
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb


# ======== SIMULAÇÃO DE DADOS TEMPORAIS ========

def generate_synthetic_temporal_dataset(n_fruits=50, days_duration=14):
    """
    Simula ciclo de vida completo de frutas com medições a cada 30min.
    
    Output: DataFrame com timestamp, features, e TTW ground truth
    """
    
    records = []
    
    for fruit_id in range(n_fruits):
        # Random fruta type
        fruit_type = np.random.choice(['Apple', 'Banana', 'Pear', 'Tomato'])
        
        # Trajectory parameters (cada fruta tem velocidade diferente de deterioração)
        ripeness_speed = np.random.uniform(0.3, 1.5)  # dias para passar de verde a podre
        base_temp = np.random.uniform(15, 22)  # temperatura base
        
        # Ciclo de vida (30min samples)
        samples_per_day = 48
        total_samples = days_duration * samples_per_day
        
        for sample_idx in range(total_samples):
            hours_elapsed = sample_idx * 0.5
            days_elapsed = hours_elapsed / 24.0
            
            # Ground truth: TTW (diminui com o tempo)
            # Modelo: Exponencial (deterioração acelera)
            ttw_hours = max(0, (ripeness_speed * 14 - days_elapsed) * 24 * (1.1 ** days_elapsed))
            
            # Features que mudam ao longo do tempo
            # R/G ratio aumenta conforme a fruta fica mais madura
            rg_baseline = 0.85
            rg_ratio = rg_baseline + (days_elapsed / ripeness_speed) * 0.6
            
            # Entropia aumenta quando fruta começa a deteriorar-se
            entropy_baseline = 2.5
            entropy = entropy_baseline + np.maximum(0, (days_elapsed - ripeness_speed*0.7)) * 1.5
            
            # VOC Index (gás) dispara quando fruta está a apodrecer (últimas 48h)
            voc_baseline = 50
            if ttw_hours < 48:
                voc_index = voc_baseline + (2000 * (1 - ttw_hours/48))  # Exponencial
            else:
                voc_index = voc_baseline
            
            # Temperatura local (respiração celular aumenta com maturação)
            temp_local = base_temp + (days_elapsed / ripeness_speed) * 3  # +3°C durante ciclo
            
            # RGB
            r_mean = 120 + (days_elapsed / ripeness_speed) * 80
            g_mean = 110 - (days_elapsed / ripeness_speed) * 30
            b_mean = 80 - (days_elapsed / ripeness_speed) * 20
            
            # Ruído
            r_mean += np.random.normal(0, 5)
            g_mean += np.random.normal(0, 5)
            b_mean += np.random.normal(0, 5)
            
            record = {
                'fruit_id': fruit_id,
                'fruit_type': fruit_type,
                'hours_elapsed': hours_elapsed,
                'days_elapsed': days_elapsed,
                'ttw_ground_truth': ttw_hours,  # TARGET
                
                # Features
                'r_mean': r_mean,
                'g_mean': g_mean,
                'b_mean': b_mean,
                'rg_ratio': r_mean / (g_mean + 1e-6),
                'color_entropy': entropy,
                'voc_index': voc_index,
                'temperature_local': temp_local,
            }
            
            records.append(record)
    
    return pd.DataFrame(records)


# ======== TTW REGRESSION MODEL ========

def train_ttw_regressor(X_train, y_train):
    """
    Treina modelo de regressão para prever Time-to-Waste.
    
    Usa XGBoost (excelente para regressor em dados tabulares com padrões complexos)
    """
    
    print("\n🎯 Treinando XGBoost Regressor (TTW)...")
    
    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=7,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        objective='reg:squarederror',
        eval_metric='mae'
    )
    
    model.fit(X_train, y_train, verbose=False)
    
    return model


def train_ttw_confidence_model(predictions, y_test):
    """
    Treina modelo secundário para estimar intervalo de confiança.
    
    Usa resíduos para aprender quando o modelo é incerto.
    """
    
    print("📊 Treinando modelo de confiança...")
    
    residuals = np.abs(predictions - y_test.values)
    
    # Modelo simples: Random Forest para prever magnitude do erro
    rf_confidence = RandomForestRegressor(
        n_estimators=50,
        max_depth=5,
        random_state=42
    )
    
    # Feature: quanto maior prediction, maior pode ser o erro
    X_conf = predictions.reshape(-1, 1)
    rf_confidence.fit(X_conf, residuals)
    
    return rf_confidence


# ======== CLASSE PARA INFERÊNCIA ========

class TTWPredictor:
    """
    Preditor de Time-to-Waste com intervalo de confiança.
    Pronto para deployar no RPi 5.
    """
    
    def __init__(self, ttw_model, confidence_model=None):
        self.ttw_model = ttw_model
        self.confidence_model = confidence_model
        
        # Thresholds de ação
        self.ttw_critical = 6        # < 6h: Reduce price 50%
        self.ttw_urgent = 24        # < 24h: Reduce price 30%
        self.ttw_monitor = 72       # < 72h: Mark for reordering
    
    def predict(self, features_dict):
        """
        Prediz TTW e retorna recomendação de ação.
        
        Input: dict com features atuais
        Output: {ttw_hours, confidence, action, trend}
        """
        
        # Preparar features em ordem
        X = np.array([[
            features_dict.get('r_mean', 0),
            features_dict.get('g_mean', 0),
            features_dict.get('b_mean', 0),
            features_dict.get('rg_ratio', 0),
            features_dict.get('color_entropy', 0),
            features_dict.get('voc_index', 0),
            features_dict.get('temperature_local', 0),
        ]])
        
        # Predição
        ttw_pred = self.ttw_model.predict(X)[0]
        ttw_hours = max(0, ttw_pred)  # Não pode ser negativo
        
        # Intervalo de confiança
        confidence_margin = 0
        if self.confidence_model:
            confidence_margin = self.confidence_model.predict(X.reshape(-1, 1))[0]
        
        ttw_low = max(0, ttw_hours - confidence_margin)
        ttw_high = ttw_hours + confidence_margin
        
        # Determinação de ação
        action = "MONITOR"
        urgency_level = 0  # 0=green, 1=yellow, 2=red
        
        if ttw_hours < self.ttw_critical:
            action = "DISCARD"
            urgency_level = 3
        elif ttw_hours < self.ttw_urgent:
            action = "REDUCE_PRICE_50"
            urgency_level = 2
        elif ttw_hours < self.ttw_monitor:
            action = "REDUCE_PRICE_30"
            urgency_level = 1
        else:
            action = "MONITOR"
            urgency_level = 0
        
        # Estimação de trend (simulado; em produção usar histórico temporal)
        trend_hours_per_day = -24 / max(ttw_hours, 1)  # Horas por dia que TTW diminui
        
        return {
            'ttw_predicted': round(ttw_hours, 1),
            'ttw_low': round(ttw_low, 1),
            'ttw_high': round(ttw_high, 1),
            'confidence': round(1 - (confidence_margin / max(ttw_hours, 1)), 2),
            'action': action,
            'urgency_level': urgency_level,  # 0-3, para cor no dashboard
            'trend_hours_per_day': round(trend_hours_per_day, 2),
        }


# ======== MAIN ========

def main():
    print("=" * 70)
    print("⏱️  RipeRadar V2 - Time-to-Waste (TTW) Regression")
    print("=" * 70)
    
    # 1. Gerar dataset temporal simulado
    print("\n📊 Gerando dataset temporal simulado...")
    df = generate_synthetic_temporal_dataset(n_fruits=100, days_duration=14)
    print(f"   Dataset shape: {df.shape}")
    print(f"   TTW range: {df['ttw_ground_truth'].min():.1f}h to {df['ttw_ground_truth'].max():.1f}h")
    
    # 2. Preparar features
    feature_cols = [
        'r_mean', 'g_mean', 'b_mean', 'rg_ratio',
        'color_entropy', 'voc_index', 'temperature_local'
    ]
    
    X = df[feature_cols].values
    y = df['ttw_ground_truth'].values
    
    # Normalize
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_normalized = (X - X_mean) / (X_std + 1e-6)
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized, y, test_size=0.2, random_state=42
    )
    
    print(f"\n📈 Train set: {len(X_train)} samples, Test set: {len(X_test)} samples")
    
    # 3. Treinar modelo TTW
    ttw_model = train_ttw_regressor(X_train, y_train)
    
    # 4. Avaliação
    y_pred_train = ttw_model.predict(X_train)
    y_pred_test = ttw_model.predict(X_test)
    
    mae_test = mean_absolute_error(y_test, y_pred_test)
    rmse_test = np.sqrt(mean_squared_error(y_test, y_pred_test))
    r2_test = r2_score(y_test, y_pred_test)
    
    print(f"\n✅ Model Performance (Test Set):")
    print(f"   MAE:  {mae_test:.2f} hours")
    print(f"   RMSE: {rmse_test:.2f} hours")
    print(f"   R²:   {r2_test:.2%}")
    
    # 5. Treinar modelo de confiança
    confidence_model = train_ttw_confidence_model(y_pred_test, y_test)
    
    # 6. Demonstração de inferência
    print("\n" + "=" * 70)
    print("🎯 EXEMPLOS DE PREDIÇÃO (TTW)")
    print("=" * 70)
    
    predictor = TTWPredictor(ttw_model, confidence_model)
    
    # 3 exemplos
    examples_idx = [0, len(X_test)//2, -1]
    for idx in examples_idx:
        features_dict = {
            'r_mean': X_test[idx][0] * X_std[0] + X_mean[0],
            'g_mean': X_test[idx][1] * X_std[1] + X_mean[1],
            'b_mean': X_test[idx][2] * X_std[2] + X_mean[2],
            'rg_ratio': X_test[idx][3],
            'color_entropy': X_test[idx][4] * X_std[4] + X_mean[4],
            'voc_index': X_test[idx][5] * X_std[5] + X_mean[5],
            'temperature_local': X_test[idx][6] * X_std[6] + X_mean[6],
        }
        
        real_ttw = y_test.iloc[idx] if isinstance(y_test, pd.Series) else y_test[idx]
        result = predictor.predict(features_dict)
        
        print(f"\n📍 Exemplo {idx}:")
        print(f"   Real TTW:     {real_ttw:.1f}h")
        print(f"   Predicted:    {result['ttw_predicted']}h [{result['ttw_low']}-{result['ttw_high']}h]")
        print(f"   Confidence:   {result['confidence']:.0%}")
        print(f"   Action:       {result['action']} (urgency: {result['urgency_level']}/3)")
        print(f"   Trend:        {result['trend_hours_per_day']:.2f} hours/day")
    
    # 7. Salvar modelos
    print("\n" + "=" * 70)
    print("💾 Salvando modelos")
    print("=" * 70)
    
    Path('models').mkdir(exist_ok=True)
    
    ttw_model_path = 'models/ttw_xgboost.pkl'
    conf_model_path = 'models/ttw_confidence_rf.pkl'
    
    joblib.dump(ttw_model, ttw_model_path)
    joblib.dump(confidence_model, conf_model_path)
    
    print(f"✓ TTW Model: {ttw_model_path}")
    print(f"✓ Confidence Model: {conf_model_path}")
    
    # Metadata
    metadata = {
        'model_type': 'TTW_Regression',
        'algorithm': 'XGBoost',
        'features': feature_cols,
        'performance': {
            'mae_hours': float(mae_test),
            'rmse_hours': float(rmse_test),
            'r2_score': float(r2_test),
        },
        'thresholds': {
            'critical_hours': predictor.ttw_critical,
            'urgent_hours': predictor.ttw_urgent,
            'monitor_hours': predictor.ttw_monitor,
        },
        'deployment': {
            'location': 'RPi 5',
            'inference_latency_ms': '< 100',
        }
    }
    
    import json
    with open('models/ttw_metadata.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✓ Metadata: models/ttw_metadata.json")
    print("\n✅ TTW Training Complete!")


if __name__ == "__main__":
    main()
