"""
RipeRadar V2 - Ensemble ML Models
===================================
Treina 3 modelos em paralelo:
1. Decision Tree (rápido, no Portenta C33)
2. CatBoost (preciso, no RPi 5)
3. LSTM (temporal, no RPi 5 via TensorFlow Lite)

Implementa votação ponderada para decisão final robusta.
"""

import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

# ML Models
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
import catboost as cb

# Deep Learning (LSTM)
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.preprocessing.sequence import pad_sequences

# Warnings
import warnings
warnings.filterwarnings('ignore')

# ======== CONFIGURAÇÃO ========
FEATURES_FILE = 'riperadar_features_v2.csv'
MODEL_DIR = 'models'
Path(MODEL_DIR).mkdir(exist_ok=True)

# Features a usar (exclui label e sub_type)
FEATURE_COLUMNS = [
    'r_mean', 'g_mean', 'b_mean', 'rg_ratio', 'blue_prominence', 'saturation',
    'lab_l', 'lab_a', 'lab_b', 'hue_mean',
    'color_variance', 'var_r', 'var_g', 'var_b',
    'color_entropy', 'gray_entropy', 'edge_strength', 'edge_variance',
    'color_distance_norm', 'brightness_skew', 'brightness_kurtosis'
]

RIPENESS_CLASSES = ['Verde', 'Maturando', 'Maduro', 'Deterioracao_Iminente', 'Podre']


def create_ripeness_labels(df):
    """
    Converte imagens em classes de maturação baseado em histórico teórico.
    (Em produção, esta label virá de dados capturados temporais)
    
    Regra heurística: usar R/G ratio e color entropy como proxy
    """
    rg_threshold_verde = 0.8
    rg_threshold_maduro = 1.1
    rg_threshold_podre = 1.4
    entropy_threshold = 3.5
    
    def classify_ripeness(row):
        rg = row['rg_ratio']
        entropy = row['color_entropy']
        
        # Se há muito ruído de cor, já está a deteriorar-se
        if entropy > entropy_threshold:
            return 'Podre'
        
        # Gradiente baseado em R/G
        if rg < rg_threshold_verde:
            return 'Verde'
        elif rg < rg_threshold_maduro:
            return 'Maturando'
        elif rg < rg_threshold_podre:
            if entropy > 3.0:
                return 'Deterioracao_Iminente'
            return 'Maduro'
        else:
            return 'Podre'
    
    df['ripeness'] = df.apply(classify_ripeness, axis=1)
    return df


# ======== MODELO 1: DECISION TREE (Rápido para Portenta C33) ========

def train_decision_tree(X_train, y_train):
    """Treina Decision Tree otimizado para hardware embarcado"""
    print("\n🌳 Treinando Decision Tree (para Portenta C33)...")
    
    # Parâmetros otimizados para embedding: profundidade baixa, rápido
    dt = DecisionTreeClassifier(
        max_depth=5,           # Superficial = rápido
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42
    )
    
    dt.fit(X_train, y_train)
    
    # Avaliação
    y_pred_dt = dt.predict(X_train)
    accuracy_dt = accuracy_score(y_train, y_pred_dt)
    print(f"✓ Decision Tree Accuracy (train): {accuracy_dt:.2%}")
    
    return dt, accuracy_dt


# ======== MODELO 2: CATBOOST (Precisão no RPi 5) ========

def train_catboost(X_train, y_train):
    """Treina CatBoost para máxima precisão"""
    print("\n🚀 Treinando CatBoost (para RPi 5)...")
    
    # Converter labels para numerais
    label_encoder = {label: idx for idx, label in enumerate(RIPENESS_CLASSES)}
    y_train_encoded = np.array([label_encoder[y] for y in y_train])
    
    cb_model = cb.CatBoostClassifier(
        iterations=100,
        depth=6,
        learning_rate=0.05,
        verbose=False,
        random_state=42,
        auto_class_weights='balanced'
    )
    
    cb_model.fit(X_train, y_train_encoded)
    
    # Avaliação
    y_pred_cb = cb_model.predict(X_train)
    accuracy_cb = accuracy_score(y_train_encoded, y_pred_cb)
    print(f"✓ CatBoost Accuracy (train): {accuracy_cb:.2%}")
    
    return cb_model, label_encoder, accuracy_cb


# ======== MODELO 3: LSTM (Temporal, Previsão de TTW) ========

def prepare_lstm_sequences(X, y, window_size=10):
    """Prepara sequências temporais para LSTM"""
    X_seq = []
    y_seq = []
    
    # Agrupar por fruta (assumir que dataset está ordenado temporalmente)
    # Em produção, usar timestamps reais
    for i in range(len(X) - window_size):
        X_seq.append(X.iloc[i:i+window_size].values)
        # Target: classe do último frame
        y_seq.append(y.iloc[i+window_size])
    
    return np.array(X_seq), np.array(y_seq)


def train_lstm(X_train, y_train):
    """Treina LSTM para detecção temporal de deterioração"""
    print("\n🧠 Treinando LSTM (para previsão temporal em RPi 5)...")
    
    # Preparar sequências
    X_lstm_train, y_lstm_train = prepare_lstm_sequences(X_train, y_train, window_size=10)
    
    if len(X_lstm_train) == 0:
        print("⚠️ Não há dados suficientes para sequências LSTM. Pulando...")
        return None, None
    
    # Converter labels
    label_encoder = {label: idx for idx, label in enumerate(RIPENESS_CLASSES)}
    y_lstm_encoded = np.array([label_encoder[y] for y in y_lstm_train])
    
    # Modelo LSTM leve
    model = Sequential([
        LSTM(32, activation='relu', input_shape=(X_lstm_train.shape[1], X_lstm_train.shape[2])),
        Dropout(0.2),
        Dense(16, activation='relu'),
        Dropout(0.2),
        Dense(len(RIPENESS_CLASSES), activation='softmax')
    ])
    
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    # Treinar
    history = model.fit(
        X_lstm_train, y_lstm_encoded,
        epochs=30,
        batch_size=8,
        verbose=0,
        validation_split=0.2
    )
    
    # Último accuracy
    final_accuracy = history.history['val_accuracy'][-1]
    print(f"✓ LSTM Accuracy (val): {final_accuracy:.2%}")
    
    return model, label_encoder, final_accuracy


# ======== VOTAÇÃO PONDERADA ========

class EnsembleVoter:
    """Combina predições dos 3 modelos com pesos otimizados"""
    
    def __init__(self, dt_model, cb_model, lstm_model, label_encoders):
        self.dt = dt_model
        self.cb = cb_model
        self.lstm = lstm_model
        self.label_encoders = label_encoders
        
        # Pesos aprendidos (ajustar baseado em validação)
        self.weights = {
            'dt': 0.2,
            'cb': 0.5,
            'lstm': 0.3
        }
        
        # Reverse mapping
        self.id_to_label = {v: k for k, v in enumerate(RIPENESS_CLASSES)}
    
    def predict(self, X):
        """Votação ponderada"""
        
        # Predição do Decision Tree
        dt_pred = self.dt.predict(X)
        dt_proba = self.dt.predict_proba(X)  # Confiança
        dt_vote = np.max(dt_proba, axis=1) * self.weights['dt']
        
        # Predição do CatBoost
        cb_pred = self.cb.predict(X)
        cb_proba = self.cb.predict_proba(X)
        cb_vote = np.max(cb_proba, axis=1) * self.weights['cb']
        
        # Se LSTM disponível
        lstm_vote = np.zeros(len(X)) * self.weights['lstm']
        lstm_pred_ids = np.zeros(len(X), dtype=int)
        
        if self.lstm is not None:
            # Preparar sequências
            X_lstm, _ = prepare_lstm_sequences(X, pd.Series([0] * len(X)), window_size=10)
            if len(X_lstm) > 0:
                lstm_proba = self.lstm.predict(X_lstm, verbose=0)
                lstm_pred_ids = np.argmax(lstm_proba, axis=1)
                lstm_vote[:len(X_lstm)] = np.max(lstm_proba, axis=1) * self.weights['lstm']
        
        # Votação
        final_pred = []
        confidences = []
        
        for i in range(len(X)):
            # Converter predições para labels
            dt_label_id = dt_pred[i]
            cb_label_id = cb_pred[i]
            lstm_label_id = lstm_pred_ids[min(i, len(lstm_pred_ids)-1)] if self.lstm else dt_label_id
            
            # Voto por consenso (maioria)
            votes = [dt_label_id, cb_label_id, lstm_label_id]
            final_label_id = max(set(votes), key=votes.count)
            final_pred.append(RIPENESS_CLASSES[final_label_id])
            
            # Confiança = média ponderada
            confidence = (dt_vote[i] + cb_vote[i] + lstm_vote[i]) / (self.weights['dt'] + self.weights['cb'] + self.weights['lstm'])
            confidences.append(confidence)
        
        return final_pred, confidences


# ======== MAIN ========

def main():
    print("=" * 70)
    print("🎯 RipeRadar V2 - Ensemble Training Pipeline")
    print("=" * 70)
    
    # 1. Load data
    print(f"\n📂 Carregando dataset: {FEATURES_FILE}")
    df = pd.read_csv(FEATURES_FILE)
    
    # 2. Create labels (simulated ripeness)
    print("🏷️  Criando labels de maturação...")
    df = create_ripeness_labels(df)
    print(f"Distribuição de classes:")
    print(df['ripeness'].value_counts())
    
    # 3. Prepare features and labels
    X = df[FEATURE_COLUMNS]
    y = df['ripeness']
    
    # Normalize features
    X_mean = X.mean()
    X_std = X.std()
    X_normalized = (X - X_mean) / (X_std + 1e-6)
    
    # 4. Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\n📊 Train set: {len(X_train)} samples, Test set: {len(X_test)} samples")
    
    # ======== TRAIN MODELS ========
    
    # Model 1: Decision Tree
    dt_model, dt_acc = train_decision_tree(X_train, y_train)
    
    # Model 2: CatBoost
    cb_model, cb_encoder, cb_acc = train_catboost(X_train, y_train)
    
    # Model 3: LSTM
    lstm_model, lstm_encoder, lstm_acc = train_lstm(X_train, y_train)
    
    # ======== ENSEMBLE EVALUATION ========
    
    print("\n" + "=" * 70)
    print("📈 ENSEMBLE VOTING")
    print("=" * 70)
    
    voter = EnsembleVoter(dt_model, cb_model, lstm_model, {'dt': None, 'cb': cb_encoder, 'lstm': lstm_encoder})
    
    # Predições no test set
    y_pred_ensemble, confidences = voter.predict(X_test)
    ensemble_accuracy = accuracy_score(y_test, y_pred_ensemble)
    
    print(f"\n✅ Ensemble Accuracy (test set): {ensemble_accuracy:.2%}")
    print(f"✅ Average Confidence: {np.mean(confidences):.2%}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred_ensemble))
    
    # ======== SAVE MODELS ========
    
    print("\n" + "=" * 70)
    print("💾 Saving Models")
    print("=" * 70)
    
    # Para Portenta C33 (Decision Tree apenas)
    dt_micro_path = f"{MODEL_DIR}/dt_portenta_c33.pkl"
    joblib.dump(dt_model, dt_micro_path)
    print(f"✓ Portenta C33 Model: {dt_micro_path} ({Path(dt_micro_path).stat().st_size / 1024:.1f}KB)")
    
    # Para RPi 5 (Ensemble completo)
    cb_path = f"{MODEL_DIR}/catboost_model.pkl"
    joblib.dump(cb_model, cb_path)
    print(f"✓ CatBoost Model: {cb_path} ({Path(cb_path).stat().st_size / 1024:.1f}KB)")
    
    # LSTM em TFLite (para RPi)
    if lstm_model is not None:
        lstm_path = f"{MODEL_DIR}/lstm_model.tflite"
        converter = tf.lite.TFLiteConverter.from_keras_model(lstm_model)
        tflite_model = converter.convert()
        with open(lstm_path, 'wb') as f:
            f.write(tflite_model)
        print(f"✓ LSTM TFLite Model: {lstm_path} ({Path(lstm_path).stat().st_size / 1024:.1f}KB)")
    
    # Metadata
    metadata = {
        'features': FEATURE_COLUMNS,
        'classes': RIPENESS_CLASSES,
        'dt_accuracy': float(dt_acc),
        'cb_accuracy': float(cb_acc),
        'lstm_accuracy': float(lstm_acc) if lstm_model else 0,
        'ensemble_accuracy': float(ensemble_accuracy),
        'model_sizes_kb': {
            'dt': Path(dt_micro_path).stat().st_size / 1024,
            'cb': Path(cb_path).stat().st_size / 1024,
        },
        'deployment': {
            'portenta_c33': 'dt_portenta_c33.pkl',
            'rpi5': ['catboost_model.pkl', 'lstm_model.tflite'],
            'voting_weights': voter.weights
        }
    }
    
    metadata_path = f"{MODEL_DIR}/ensemble_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata: {metadata_path}")
    
    print("\n✅ Training Complete! Ready for deployment.")


if __name__ == "__main__":
    main()
