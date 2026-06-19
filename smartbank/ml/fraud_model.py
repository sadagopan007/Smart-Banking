"""
SmartBank – Fraud Detection Module
Uses a Random Forest classifier trained on synthetic transaction data.
On first run the model is trained and cached; subsequent calls use the cache.
"""

import os
import pickle
import numpy as np

# Optional heavy imports — gracefully degrade if sklearn not installed
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

MODEL_PATH  = os.path.join(os.path.dirname(__file__), "fraud_model.pkl")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.pkl")


# ── Training data generation ───────────────────────────────────────────────────

def _generate_training_data():
    """
    Generate synthetic labelled transaction data.
    Features: [amount, hour_of_day, tx_count_last_hour, avg_tx_amount]
    Label   : 0 = Normal, 1 = Suspicious
    """
    np.random.seed(42)
    n = 3000

    # Normal transactions
    normal_amount      = np.random.lognormal(mean=7, sigma=1, size=n)      # ₹100 – ₹50k typical
    normal_hour        = np.random.randint(8, 22, size=n)                  # business hours
    normal_freq        = np.random.randint(1, 5, size=n)
    normal_avg         = normal_amount * np.random.uniform(0.8, 1.2, size=n)
    normal_labels      = np.zeros(n)

    # Suspicious transactions
    sus_amount  = np.random.lognormal(mean=11, sigma=1.5, size=n // 5)    # unusually large
    sus_hour    = np.concatenate([
        np.random.randint(0, 6, size=n // 10),     # late night
        np.random.randint(22, 24, size=n // 10),
    ])
    sus_freq    = np.random.randint(10, 30, size=n // 5)                   # rapid fire
    sus_avg     = sus_amount * np.random.uniform(0.5, 3.0, size=n // 5)
    sus_labels  = np.ones(n // 5)

    X = np.vstack([
        np.column_stack([normal_amount, normal_hour, normal_freq, normal_avg]),
        np.column_stack([sus_amount,    sus_hour[:n // 5], sus_freq, sus_avg]),
    ])
    y = np.concatenate([normal_labels, sus_labels])
    return X, y


# ── Model loading / training ───────────────────────────────────────────────────

def _load_or_train():
    if not SKLEARN_AVAILABLE:
        return None, None

    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(SCALER_PATH, "rb") as f:
            scaler = pickle.load(f)
        return model, scaler

    # Train fresh
    X, y = _generate_training_data()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_scaled, y)

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(scaler, f)

    print("[SmartBank ML] ✅ Fraud model trained and saved.")
    return model, scaler


_model, _scaler = _load_or_train()


# ── Public API ─────────────────────────────────────────────────────────────────

def predict_fraud(amount: float, hour_of_day: int,
                  tx_count_last_hour: int, avg_tx_amount: float) -> dict:
    """
    Predict whether a transaction is fraudulent.

    Returns:
        {
            "label"      : "Normal" | "Suspicious",
            "probability": float (0–1, probability of being suspicious),
            "flagged"    : bool
        }
    """
    if not SKLEARN_AVAILABLE or _model is None:
        return {"label": "Normal", "probability": 0.0, "flagged": False}

    features = np.array([[amount, hour_of_day, tx_count_last_hour, avg_tx_amount]])
    features_scaled = _scaler.transform(features)

    proba   = _model.predict_proba(features_scaled)[0][1]   # P(suspicious)
    flagged = proba >= 0.55                                  # threshold

    return {
        "label":       "Suspicious" if flagged else "Normal",
        "probability": round(float(proba) * 100, 1),
        "flagged":     flagged,
    }
