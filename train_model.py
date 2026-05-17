import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from sklearn.ensemble import RandomForestRegressor

# =========================================
# LOAD DATASET
# =========================================
data = pd.read_csv('models/train-chennai-sale.csv')

# =========================================
# REMOVE MISSING VALUES
# =========================================
data = data.dropna()

# =========================================
# AREA ENCODING
# =========================================
encoder = LabelEncoder()

data['AREA'] = encoder.fit_transform(data['AREA'])

# =========================================
# FEATURES
# =========================================
X = data[
    [
        'AREA',
        'INT_SQFT',
        'N_BEDROOM',
        'N_BATHROOM',
        'N_ROOM'
    ]
]

# =========================================
# TARGET
# =========================================
y = data['SALES_PRICE']

# =========================================
# SPLIT DATA
# =========================================
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# =========================================
# RANDOM FOREST MODEL
# =========================================
model = RandomForestRegressor(

    n_estimators=100,

    random_state=42
)

# =========================================
# TRAIN MODEL
# =========================================
model.fit(X_train, y_train)

# =========================================
# MODEL ACCURACY
# =========================================
score = model.score(X_test, y_test)

accuracy = round(score * 100, 2)

print("Model Accuracy:", accuracy, "%")
# =========================================
# SAVE MODEL
# =========================================
joblib.dump(
    model,
    'models/house_price_model.pkl'
)

# =========================================
# SAVE ENCODER
# =========================================
joblib.dump(
    encoder,
    'models/area_encoder.pkl'
)

print("Random Forest Model Trained Successfully")