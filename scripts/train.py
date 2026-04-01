import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

# 1. Load the data
print("📂 Loading dataset...")
df = pd.read_csv('riperadar_synthetic_dataset.csv')

# 2. Prepare Features (X) and Labels (y)
# We use R, G, B and the R/G Ratio as our features
X = df[['r', 'g', 'b', 'rg_ratio']]
y = df['label']

# 3. Split into Training and Testing sets (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 4. Train the "Brain"
print("🧠 Training the RipeRadar model... This may take a minute.")
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# 5. Evaluate
y_pred = model.predict(X_test)
print("\n✅ Training Complete!")
print(f"Accuracy Score: {accuracy_score(y_test, y_pred):.2%}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# 6. Save the model for real-time use
joblib.dump(model, 'riperadar_model.pkl')
print("💾 Model saved as 'riperadar_model.pkl'")