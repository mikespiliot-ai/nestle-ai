import yfinance as yf
import pandas as pd
import numpy as np
import ta
import requests
import os
import json
import warnings
from datetime import datetime
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from sklearn.svm import SVC
import gspread
from google.oauth2.service_account import Credentials
warnings.filterwarnings('ignore')

# ============================================================
# ΡΥΘΜΙΣΕΙΣ
# ============================================================
SYMBOL = "NESN.SW"
SHEET_ID = "1pzz7SPf-sE0DXyVXxZ0g2YTEZ2BtwGt8bHxEnCBnKrw"
CREDENTIALS_FILE = "aerobic-gift-489323-p3-383bccfec0b1.json"
TRAINING_PERIOD = "4y"
TODAY = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = "nestle_log.txt"

# ============================================================
# LOGGING
# ============================================================
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# ΣΥΝΔΕΣΗ ΜΕ GOOGLE SHEETS
# ============================================================
def connect_to_sheets():
    log("Σύνδεση με Google Sheets...")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)

    # Δημιουργία sheets αν δεν υπάρχουν
    existing = [ws.title for ws in sheet.worksheets()]

    if "Προβλέψεις" not in existing:
        ws = sheet.add_worksheet(title="Προβλέψεις", rows=100, cols=15)
        headers = [
            "Ημερομηνία", "Σήμα", "Εμπιστοσύνη (%)", "Πιθανότητα Ανόδου (%)",
            "Τιμή Αγοράς (CHF)", "RSI", "VIX", "Fear & Greed",
            "Ακρίβεια Μοντέλου (%)", "Τιμή Επόμενης Μέρας", "Μεταβολή (%)", "Αποτέλεσμα"
        ]
        ws.append_row(headers)
        log("  -> Sheet 'Προβλέψεις' δημιουργήθηκε")
    
    if "Στατιστικά" not in existing:
        ws2 = sheet.add_worksheet(title="Στατιστικά", rows=10, cols=6)
        headers2 = ["Συνολικές Προβλέψεις", "Σωστές", "Λάθος", "Ποσοστό Επιτυχίας (%)", "Τελευταία Ενημέρωση"]
        ws2.append_row(headers2)
        log("  -> Sheet 'Στατιστικά' δημιουργήθηκε")

    log("  -> Σύνδεση επιτυχής!")
    return sheet

# ============================================================
# ΒΗΜΑ 1: ΣΥΛΛΟΓΗ ΔΕΔΟΜΕΝΩΝ
# ============================================================
def fetch_all_data():
    log("Συλλογή δεδομένων...")

    nestle = yf.download(SYMBOL, period=TRAINING_PERIOD, interval="1d", progress=False)
    nestle.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    extras = yf.download(
        ['^GSPC', '^VIX', 'EURCHF=X', 'CL=F'],
        period=TRAINING_PERIOD, interval="1d", progress=False
    )['Close']
    extras.columns = ['SP500', 'VIX', 'EURCHF', 'OIL']

    try:
        r = requests.get("https://api.alternative.me/fng/?limit=0", timeout=10)
        fng_data = r.json()['data']
        fng_df = pd.DataFrame(fng_data)
        fng_df['timestamp'] = pd.to_datetime(fng_df['timestamp'].astype(int), unit='s')
        fng_df.set_index('timestamp', inplace=True)
        fng_df['FNG'] = fng_df['value'].astype(float)
        fng_df = fng_df[['FNG']]
        fng_df.index = fng_df.index.tz_localize(None)
        log("  -> Fear & Greed: OK")
    except Exception as e:
        log(f"  -> Fear & Greed απέτυχε: {e}")
        fng_df = pd.DataFrame()

    nestle['SMA_20'] = ta.trend.sma_indicator(nestle['Close'], window=20)
    nestle['SMA_50'] = ta.trend.sma_indicator(nestle['Close'], window=50)
    nestle['RSI_14'] = ta.momentum.rsi(nestle['Close'], window=14)
    nestle['MACD'] = ta.trend.macd(nestle['Close'])
    nestle['BB_HIGH'] = ta.volatility.bollinger_hband(nestle['Close'])
    nestle['BB_LOW'] = ta.volatility.bollinger_lband(nestle['Close'])
    nestle['Volatility'] = nestle['Close'].rolling(20).std()

    nestle.index = nestle.index.tz_localize(None)
    extras.index = extras.index.tz_localize(None)
    df = nestle.join(extras, how='inner')

    if not fng_df.empty:
        df = df.join(fng_df, how='left')
        df['FNG'] = df['FNG'].fillna(method='ffill')
    else:
        df['FNG'] = 50

    df.dropna(inplace=True)
    log(f"  -> Δεδομένα έτοιμα: {len(df)} ημέρες")
    return df

# ============================================================
# ΒΗΜΑ 2: ΕΚΠΑΙΔΕΥΣΗ AI
# ============================================================
def train_model(df):
    log("Εκπαίδευση AI...")

    df['Target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)

    features = [
        'Close', 'Volume', 'SMA_20', 'SMA_50', 'RSI_14', 'MACD',
        'BB_HIGH', 'BB_LOW', 'Volatility', 'SP500', 'VIX', 'EURCHF', 'OIL', 'FNG'
    ]

    X = df[features]
    y = df['Target']

    split = int(len(df) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    m1 = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    m2 = lgb.LGBMClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, verbose=-1, random_state=42)
    m3 = CatBoostClassifier(iterations=100, depth=3, learning_rate=0.05, verbose=0, random_state=42)
    m4 = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
    m5 = SVC(probability=True, kernel='rbf', random_state=42)

    council = VotingClassifier(
        estimators=[('xgb', m1), ('lgb', m2), ('cat', m3), ('rf', m4), ('svm', m5)],
        voting='soft'
    )

    council.fit(X_train_scaled, y_train)
    y_pred = council.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    log(f"  -> Ακρίβεια: {acc*100:.2f}%")

    return council, scaler, features, round(acc*100, 2)

# ============================================================
# ΒΗΜΑ 3: ΠΡΟΒΛΕΨΗ
# ============================================================
def make_prediction(df, model, scaler, features):
    log("Πρόβλεψη για αύριο...")

    last_row = df[features].iloc[-1].values.reshape(1, -1)
    last_scaled = scaler.transform(last_row)

    prediction = model.predict(last_scaled)[0]
    probability = model.predict_proba(last_scaled)[0]
    confidence = round(probability[prediction] * 100, 2)
    prob_up = round(probability[1] * 100, 2)

    if confidence < 58:
        signal = "ΑΝΑΜΟΝΗ"
    elif prediction == 1:
        signal = "ΑΓΟΡΑ"
    else:
        signal = "ΠΩΛΗΣΗ"

    current_price = round(float(df['Close'].iloc[-1]), 2)
    rsi = round(float(df['RSI_14'].iloc[-1]), 2)
    vix = round(float(df['VIX'].iloc[-1]), 2)
    fng = round(float(df['FNG'].iloc[-1]), 2)

    log(f"  -> Σήμα: {signal} | Εμπιστοσύνη: {confidence}% | Τιμή: {current_price} CHF")

    return {
        'date': TODAY,
        'signal': signal,
        'confidence': confidence,
        'prob_up': prob_up,
        'price': current_price,
        'rsi': rsi,
        'vix': vix,
        'fng': fng,
    }

# ============================================================
# ΒΗΜΑ 4: ΕΛΕΓΧΟΣ ΧΘΕΣΙΝΗΣ ΠΡΟΒΛΕΨΗΣ
# ============================================================
def check_yesterday(sheet, df):
    try:
        ws = sheet.worksheet("Προβλέψεις")
        all_rows = ws.get_all_values()

        if len(all_rows) < 2:
            return None

        last_row = all_rows[-1]
        yesterday_signal = last_row[1]
        yesterday_price = float(last_row[4])
        today_price = float(df['Close'].iloc[-1])

        price_change = round(today_price - yesterday_price, 4)
        pct_change = round((price_change / yesterday_price) * 100, 2)

        if yesterday_signal == "ΑΓΟΡΑ":
            result = "✅ ΣΩΣΤΟ" if today_price > yesterday_price else "❌ ΛΑΘΟΣ"
        elif yesterday_signal == "ΠΩΛΗΣΗ":
            result = "✅ ΣΩΣΤΟ" if today_price < yesterday_price else "❌ ΛΑΘΟΣ"
        else:
            result = "➖ ΟΥΔΕΤΕΡΟ"

        # Ενημέρωση τελευταίας γραμμής
        last_row_index = len(all_rows)
        ws.update_cell(last_row_index, 10, round(today_price, 2))
        ws.update_cell(last_row_index, 11, pct_change)
        ws.update_cell(last_row_index, 12, result)

        log(f"  -> Χθες: {yesterday_signal} | Αποτέλεσμα: {result} | Μεταβολή: {pct_change}%")

        return {
            'today_price': round(today_price, 2),
            'pct_change': pct_change,
            'result': result,
        }

    except Exception as e:
        log(f"  -> Αδυναμία ελέγχου χθεσινής: {e}")
        return None

# ============================================================
# ΒΗΜΑ 5: ΑΠΟΘΗΚΕΥΣΗ ΣΤΟ GOOGLE SHEETS
# ============================================================
def save_to_sheets(sheet, prediction, model_accuracy):
    log("Αποθήκευση στο Google Sheets...")

    ws = sheet.worksheet("Προβλέψεις")

    new_row = [
        prediction['date'],
        prediction['signal'],
        prediction['confidence'],
        prediction['prob_up'],
        prediction['price'],
        prediction['rsi'],
        prediction['vix'],
        prediction['fng'],
        model_accuracy,
        "",  # Τιμή αύριο - θα συμπληρωθεί αύριο
        "",  # Μεταβολή - θα συμπληρωθεί αύριο
        "ΑΝΑΜΕΝΕΤΑΙ",  # Αποτέλεσμα
    ]

    ws.append_row(new_row)

    # Ενημέρωση στατιστικών
    ws_stats = sheet.worksheet("Στατιστικά")
    all_rows = ws.get_all_values()[1:]  # Χωρίς header

    correct = sum(1 for r in all_rows if len(r) > 11 and "ΣΩΣΤΟ" in r[11])
    wrong = sum(1 for r in all_rows if len(r) > 11 and "ΛΑΘΟΣ" in r[11])
    total = correct + wrong
    success_rate = round(correct / total * 100, 2) if total > 0 else 0

    # Καθαρισμός και εγγραφή στατιστικών
    ws_stats.clear()
    ws_stats.append_row(["Συνολικές Προβλέψεις", "Σωστές", "Λάθος", "Ποσοστό Επιτυχίας (%)", "Τελευταία Ενημέρωση"])
    ws_stats.append_row([len(all_rows), correct, wrong, success_rate, TODAY])

    log(f"  -> Google Sheets ενημερώθηκε!")
    log(f"  -> Ποσοστό επιτυχίας: {success_rate}% ({correct}/{total})")

# ============================================================
# ΚΥΡΙΟ ΠΡΟΓΡΑΜΜΑ
# ============================================================
if __name__ == "__main__":
    log("=" * 55)
    log("  NESTLE AI PREDICTION SYSTEM")
    log(f"  {TODAY}")
    log("=" * 55)

    try:
        sheet = connect_to_sheets()
        df = fetch_all_data()
        model, scaler, features, accuracy = train_model(df)
        prediction = make_prediction(df, model, scaler, features)
        check_yesterday(sheet, df)
        save_to_sheets(sheet, prediction, accuracy)

        log("=" * 55)
        log(f"ΣΗΜΑ    : {prediction['signal']}")
        log(f"ΕΜΠΙΣΤΟΣΥΝΗ: {prediction['confidence']}%")
        log(f"ΤΙΜΗ    : {prediction['price']} CHF")
        log("=" * 55)

    except Exception as e:
        log(f"ΚΡΙΣΙΜΟ ΣΦΑΛΜΑ: {e}")
        raise
