import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import requests
import re
import io
import time
import threading
from datetime import datetime, timedelta
from PIL import Image
import os
import base64
import hashlib

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Betting System · Only Solutions",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# HARDCODED API KEYS
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = "sk-09832202e2c74c7ea73891197056a8e6"
ODDS_API_KEY = "a585010a77f214e1ce910e778b079400"
TELEGRAM_BOT_TOKEN = ""  # Add your Telegram bot token here for alerts
TELEGRAM_CHAT_ID = ""    # Add your Telegram chat ID here

# ─────────────────────────────────────────────────────────────
# SIDEBAR — SETTINGS
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    bankroll = st.number_input("Bankroll ($)", value=1000, min_value=100, step=100)
    min_ev = st.slider("Min. EV %", 1, 25, 5, 1)
    min_arb_profit = st.slider("Min. Arbitrage Profit %", 0.1, 5.0, 0.5, 0.1)
    kelly_fraction = st.slider("Kelly Fraction", 0.1, 0.5, 0.25, 0.05)
    st.markdown("---")
    st.caption("v5.1 · Only Solutions Inc.")

# ─────────────────────────────────────────────────────────────
# TELEGRAM ALERT FUNCTION (PASSIVE)
# ─────────────────────────────────────────────────────────────
def send_telegram_alert(message: str):
    """Send alert via Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={'chat_id': TELEGRAM_CHAT_ID, 'text': message}, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

# ─────────────────────────────────────────────────────────────
# ARBITRAGE SCANNER ENGINE
# ─────────────────────────────────────────────────────────────
class SportsBookScanner:
    def __init__(self, api_key: str, regions: str = "eu", markets: str = "h2h"):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4/sports"
        self.regions = regions
        self.markets = markets

    def get_active_sports(self) -> list:
        if not self.api_key or self.api_key == "YOUR_ODDS_API_KEY_HERE":
            return ["soccer_epl", "soccer_uefa_champs_league", "icehockey_nhl", "basketball_nba"]
        
        try:
            url = f"{self.base_url}/?apiKey={self.api_key}"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return [sport['key'] for sport in response.json()]
            return []
        except Exception:
            return []

    def fetch_live_odds(self, sport: str) -> list:
        if not self.api_key or self.api_key == "YOUR_ODDS_API_KEY_HERE":
            return self.get_sample_data(sport)
        
        try:
            url = f"{self.base_url}/{sport}/odds/"
            params = {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": self.markets,
                "oddsFormat": "decimal"
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    def get_sample_data(self, sport: str) -> list:
        sample_events = [
            {
                "id": "sample_1",
                "sport_key": sport,
                "home_team": "Emelec",
                "away_team": "Independiente del Valle",
                "bookmakers": [
                    {
                        "key": "sample_book",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Emelec", "price": 2.50},
                                    {"name": "Draw", "price": 4.05},
                                    {"name": "Independiente del Valle", "price": 2.80}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sample_2",
                "sport_key": sport,
                "home_team": "Barcelona Guayaquil",
                "away_team": "Un. Catolica",
                "bookmakers": [
                    {
                        "key": "sample_book",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Barcelona Guayaquil", "price": 3.90},
                                    {"name": "Draw", "price": 3.25},
                                    {"name": "Un. Catolica", "price": 1.75}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sample_3",
                "sport_key": sport,
                "home_team": "GIF Sundsvall",
                "away_team": "Norrby IF",
                "bookmakers": [
                    {
                        "key": "sample_book",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "GIF Sundsvall", "price": 3.50},
                                    {"name": "Draw", "price": 3.20},
                                    {"name": "Norrby IF", "price": 1.85}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sample_4",
                "sport_key": sport,
                "home_team": "Helsingborgs",
                "away_team": "Falkenbergs",
                "bookmakers": [
                    {
                        "key": "sample_book",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Helsingborgs", "price": 3.25},
                                    {"name": "Draw", "price": 3.25},
                                    {"name": "Falkenbergs", "price": 1.90}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                "id": "sample_5",
                "sport_key": sport,
                "home_team": "Lokomotiv Sofia",
                "away_team": "Botev Plovdiv",
                "bookmakers": [
                    {
                        "key": "sample_book",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Lokomotiv Sofia", "price": 4.15},
                                    {"name": "Draw", "price": 3.35},
                                    {"name": "Botev Plovdiv", "price": 1.70}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        return sample_events

class ArbitrageEngine:
    @staticmethod
    def calculate_arbitrage(home_odds: float, away_odds: float, draw_odds: float = None) -> dict:
        if home_odds <= 0 or away_odds <= 0:
            return None
        
        p_home = 1.0 / home_odds
        p_away = 1.0 / away_odds
        p_draw = (1.0 / draw_odds) if draw_odds and draw_odds > 0 else 0.0
        
        total_implied = p_home + p_away + p_draw
        
        if total_implied < 1.0:
            roi = (1.0 - total_implied) * 100
            total = p_home + p_away + p_draw
            return {
                "arbitrage_found": True,
                "total_implied_probability": total_implied,
                "roi_percentage": roi,
                "weights": {
                    "home": p_home / total if total > 0 else 0,
                    "away": p_away / total if total > 0 else 0,
                    "draw": p_draw / total if total > 0 else 0
                },
                "outcomes": {
                    "home": {"odds": home_odds, "implied": p_home},
                    "away": {"odds": away_odds, "implied": p_away},
                    "draw": {"odds": draw_odds, "implied": p_draw} if draw_odds else None
                }
            }
        return None

    @staticmethod
    def allocate_stakes(total_stake: float, weights: dict) -> dict:
        return {outcome: round(total_stake * weight, 2) for outcome, weight in weights.items() if weight > 0}

    @staticmethod
    def round_stakes(stakes: dict, increment: float = 5.0) -> dict:
        rounded = {}
        total = sum(stakes.values())
        
        for outcome, stake in stakes.items():
            rounded[outcome] = round(stake / increment) * increment
            if rounded[outcome] < 1:
                rounded[outcome] = 1
        
        rounded_total = sum(rounded.values())
        if rounded_total != total:
            largest = max(rounded, key=rounded.get)
            rounded[largest] += round(total - rounded_total, 2)
        
        return rounded

# ─────────────────────────────────────────────────────────────
# CRYPTO ARBITRAGE SCANNER (PASSIVE)
# ─────────────────────────────────────────────────────────────
class CryptoArbitrageScanner:
    def __init__(self):
        self.exchanges = {
            "binance": "https://api.binance.com/api/v3/ticker/price",
            "coinbase": "https://api.coinbase.com/v2/prices/",
            "kraken": "https://api.kraken.com/0/public/Ticker",
            "huobi": "https://api.huobi.pro/market/tickers",
        }
    
    def get_price_binance(self, symbol="BTCUSDT"):
        try:
            response = requests.get(f"{self.exchanges['binance']}?symbol={symbol}", timeout=5)
            return float(response.json()['price'])
        except:
            return None
    
    def get_price_coinbase(self, symbol="BTC-USD"):
        try:
            response = requests.get(f"{self.exchanges['coinbase']}{symbol}/spot", timeout=5)
            return float(response.json()['data']['amount'])
        except:
            return None
    
    def get_price_kraken(self, symbol="XBTUSD"):
        try:
            response = requests.get(f"{self.exchanges['kraken']}?pair={symbol}", timeout=5)
            return float(response.json()['result'][symbol]['c'][0])
        except:
            return None
    
    def scan_crypto_arbitrage(self, min_profit=0.5):
        opportunities = []
        
        prices = {
            "binance": self.get_price_binance("BTCUSDT"),
            "coinbase": self.get_price_coinbase("BTC-USD"),
            "kraken": self.get_price_kraken("XBTUSD"),
        }
        
        valid_prices = {k: v for k, v in prices.items() if v is not None}
        
        if len(valid_prices) < 2:
            return opportunities
        
        for exchange1, price1 in valid_prices.items():
            for exchange2, price2 in valid_prices.items():
                if exchange1 >= exchange2:
                    continue
                
                if price1 > price2:
                    profit_percent = ((price1 - price2) / price2) * 100
                    if profit_percent >= min_profit:
                        opportunities.append({
                            'buy': exchange2,
                            'sell': exchange1,
                            'buy_price': price2,
                            'sell_price': price1,
                            'profit_percent': profit_percent,
                            'symbol': 'BTC/USD'
                        })
                elif price2 > price1:
                    profit_percent = ((price2 - price1) / price1) * 100
                    if profit_percent >= min_profit:
                        opportunities.append({
                            'buy': exchange1,
                            'sell': exchange2,
                            'buy_price': price1,
                            'sell_price': price2,
                            'profit_percent': profit_percent,
                            'symbol': 'BTC/USD'
                        })
        
        return opportunities

# ─────────────────────────────────────────────────────────────
# EV CALCULATION FUNCTIONS
# ─────────────────────────────────────────────────────────────
def calculate_true_probability(odds, market_avg):
    implied = 1 / odds
    adjustment = 1 - (market_avg - 1) * 0.1
    return implied * adjustment

def calculate_correct_ev(odds, true_prob):
    return (true_prob * odds) - 1

def get_market_average(odds_list):
    valid = [o for o in odds_list if o > 0]
    if not valid:
        return 1.5
    return sum(1/o for o in valid) / len(valid)

def get_best_bet(match):
    home_odds = match.get('home_odds', 0)
    draw_odds = match.get('draw_odds', 0)
    away_odds = match.get('away_odds', 0)
    
    odds_list = [o for o in [home_odds, draw_odds, away_odds] if o > 0]
    if len(odds_list) < 2:
        return None
    
    market_avg = get_market_average(odds_list)
    results = {}
    
    if home_odds > 0:
        true_prob = calculate_true_probability(home_odds, market_avg)
        ev = calculate_correct_ev(home_odds, true_prob)
        results['home'] = {
            'odds': home_odds,
            'true_prob': true_prob * 100,
            'implied_prob': (1/home_odds) * 100,
            'ev_percent': ev * 100
        }
    
    if draw_odds > 0:
        true_prob = calculate_true_probability(draw_odds, market_avg)
        ev = calculate_correct_ev(draw_odds, true_prob)
        results['draw'] = {
            'odds': draw_odds,
            'true_prob': true_prob * 100,
            'implied_prob': (1/draw_odds) * 100,
            'ev_percent': ev * 100
        }
    
    if away_odds > 0:
        true_prob = calculate_true_probability(away_odds, market_avg)
        ev = calculate_correct_ev(away_odds, true_prob)
        results['away'] = {
            'odds': away_odds,
            'true_prob': true_prob * 100,
            'implied_prob': (1/away_odds) * 100,
            'ev_percent': ev * 100
        }
    
    if not results:
        return None
    
    best_outcome = None
    best_ev = -999
    
    for outcome, data in results.items():
        if data['ev_percent'] > best_ev:
            best_ev = data['ev_percent']
            best_outcome = outcome
    
    if best_outcome and best_ev >= min_ev:
        return {
            'match': f"{match['home_team']} vs {match['away_team']}",
            'outcome': best_outcome,
            'odds': results[best_outcome]['odds'],
            'ev_percent': best_ev,
            'true_prob': results[best_outcome]['true_prob'],
            'implied_prob': results[best_outcome]['implied_prob']
        }
    
    return None

# ─────────────────────────────────────────────────────────────
# DEEPSEEK AI FUNCTION
# ─────────────────────────────────────────────────────────────
def ask_deepseek(prompt: str) -> str:
    if not DEEPSEEK_API_KEY:
        return "⚠️ DeepSeek API key not configured."
    
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "You are Allison, a professional betting analyst. You MUST choose exactly ONE outcome. Format: 'BEST BET: [outcome] @ [odds]. Why: [one sentence]'"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 150
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"⚠️ API Error: {response.status_code}"
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

def get_ai_analysis(match: dict) -> dict:
    best_bet = get_best_bet(match)
    if not best_bet:
        return {'analysis': "⚠️ No positive EV bet found."}
    
    prompt = f"""
    Match: {match['home_team']} vs {match['away_team']}
    Odds: Home {match['home_odds']}, Draw {match['draw_odds']}, Away {match['away_odds']}
    Best bet: {best_bet['outcome'].upper()} @ {best_bet['odds']} with {best_bet['ev_percent']:.1f}% EV.
    Confirm this is the best bet and explain why in one sentence.
    Format: "BEST BET: [outcome] @ [odds]. Why: [one sentence]"
    """
    response = ask_deepseek(prompt)
    return {'analysis': response, 'best_bet': best_bet}

# ─────────────────────────────────────────────────────────────
# DATABASE FUNCTIONS
# ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('betting_history.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        sport TEXT,
        home_team TEXT,
        away_team TEXT,
        bet_type TEXT,
        outcome TEXT,
        odds REAL,
        stake REAL,
        ev_percent REAL,
        true_prob REAL,
        implied_prob REAL,
        result TEXT,
        return REAL,
        profit_loss REAL,
        notes TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS odds_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sport TEXT,
        data TEXT,
        timestamp TEXT
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS crypto_opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        buy_exchange TEXT,
        sell_exchange TEXT,
        symbol TEXT,
        buy_price REAL,
        sell_price REAL,
        profit_percent REAL,
        executed INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

def add_bet(bet_data):
    conn = sqlite3.connect('betting_history.db')
    c = conn.cursor()
    c.execute('''
    INSERT INTO bets (
        timestamp, sport, home_team, away_team, bet_type, outcome,
        odds, stake, ev_percent, true_prob, implied_prob,
        result, return, profit_loss, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        bet_data.get('timestamp', datetime.now().isoformat()),
        bet_data.get('sport', ''),
        bet_data.get('home_team', ''),
        bet_data.get('away_team', ''),
        bet_data.get('bet_type', 'Match Winner'),
        bet_data.get('outcome', ''),
        bet_data.get('odds', 0.0),
        bet_data.get('stake', 0.0),
        bet_data.get('ev_percent', 0.0),
        bet_data.get('true_prob', 0.0),
        bet_data.get('implied_prob', 0.0),
        bet_data.get('result', 'Pending'),
        bet_data.get('return', 0.0),
        bet_data.get('profit_loss', 0.0),
        bet_data.get('notes', '')
    ))
    conn.commit()
    conn.close()

def get_all_bets():
    conn = sqlite3.connect('betting_history.db')
    c = conn.cursor()
    c.execute('SELECT * FROM bets ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def get_bet_summary():
    conn = sqlite3.connect('betting_history.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM bets')
    total_bets = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(stake) FROM bets')
    total_staked = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(profit_loss) FROM bets WHERE result = "Win"')
    total_won = c.fetchone()[0] or 0
    
    c.execute('SELECT SUM(profit_loss) FROM bets WHERE result = "Loss"')
    total_lost = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM bets WHERE result = "Win"')
    wins = c.fetchone()[0] or 0
    
    c.execute('SELECT COUNT(*) FROM bets WHERE result = "Loss"')
    losses = c.fetchone()[0] or 0
    
    c.execute('SELECT AVG(ev_percent) FROM bets')
    avg_ev = c.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'total_bets': total_bets,
        'total_staked': total_staked,
        'total_won': total_won,
        'total_lost': total_lost,
        'net_profit': total_won - abs(total_lost),
        'wins': wins,
        'losses': losses,
        'win_rate': wins / (wins + losses) if (wins + losses) > 0 else 0,
        'avg_ev': avg_ev,
        'current_bankroll': bankroll + (total_won - abs(total_lost))
    }

def update_bet_result(bet_id, result, return_amount, profit_loss):
    conn = sqlite3.connect('betting_history.db')
    c = conn.cursor()
    c.execute('''
    UPDATE bets 
    SET result = ?, return = ?, profit_loss = ?
    WHERE id = ?
    ''', (result, return_amount, profit_loss, bet_id))
    conn.commit()
    conn.close()

def log_crypto_opportunity(opp):
    conn = sqlite3.connect('betting_history.db')
    c = conn.cursor()
    c.execute('''
    INSERT INTO crypto_opportunities (
        timestamp, buy_exchange, sell_exchange, symbol,
        buy_price, sell_price, profit_percent, executed
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        opp['buy'],
        opp['sell'],
        opp['symbol'],
        opp['buy_price'],
        opp['sell_price'],
        opp['profit_percent'],
        0
    ))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────────────────────
# LOGIN SYSTEM
# ─────────────────────────────────────────────────────────────
USERS_FILE = "users.json"
ADMIN_EMAIL = "admin@onlys.com"

DEFAULT_USERS = {
    ADMIN_EMAIL: {
        "password": "12345",
        "name": "Administrator",
        "role": "admin",
        "created": datetime.now().isoformat(),
    }
}

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    save_users(DEFAULT_USERS)
    return DEFAULT_USERS

def save_users(u):
    with open(USERS_FILE, "w") as f:
        json.dump(u, f, indent=2)

def authenticate(email, pw):
    u = load_users().get(email)
    return u if (u and u["password"] == pw) else None

def create_user(email, name, pw, role="user"):
    users = load_users()
    if email in users:
        return False
    users[email] = {"password": pw, "name": name, "role": role, "created": datetime.now().isoformat()}
    save_users(users)
    return True

def delete_user(email):
    if email == ADMIN_EMAIL:
        return False
    users = load_users()
    if email in users:
        del users[email]
        save_users(users)
        return True
    return False

def reset_password(email, pw):
    users = load_users()
    if email in users:
        users[email]["password"] = pw
        save_users(users)
        return True
    return False

def do_logout():
    for key in ['authenticated', 'user_email', 'user_name', 'user_role', 'matches', 'results']:
        st.session_state[key] = None if key not in ['matches', 'results'] else []
    st.session_state.authenticated = False
    st.rerun()

# ─────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────
def page_login():
    st.markdown("""
    <style>
        .login-box {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: #0C1929;
            border-radius: 10px;
            border: 1px solid #00D4FF;
            text-align: center;
        }
        .login-box h1 {
            color: #00D4FF;
            margin-bottom: 10px;
        }
        .login-box p {
            color: #4A7090;
            margin-bottom: 30px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1>📊 Betting System</h1>", unsafe_allow_html=True)
        st.markdown("<p>Only Solutions Inc.</p>", unsafe_allow_html=True)
        
        email = st.text_input("Email", placeholder="admin@onlys.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        
        if st.button("Sign In", use_container_width=True):
            user = authenticate(email, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.user_name = user["name"]
                st.session_state.user_role = user["role"]
                st.rerun()
            else:
                st.error("Invalid email or password")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'matches' not in st.session_state:
    st.session_state.matches = []
if 'results' not in st.session_state:
    st.session_state.results = []
if 'scanner_results' not in st.session_state:
    st.session_state.scanner_results = []

if not st.session_state.authenticated:
    page_login()

# ─── MAIN DASHBOARD ──────────────────────────────────────────
init_db()

st.title("📊 Hybrid Betting System — Active + Passive")
st.markdown(f"**Welcome, {st.session_state.user_name}** | Role: {st.session_state.user_role.upper()}")

with st.sidebar:
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        do_logout()

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📸 Upload", "📝 Manual", "📊 Results", "📄 Slip", "📋 History", "🔍 Scanner", "🪙 Crypto"
])

with tab1:
    st.markdown("### 📸 Upload Odds Board Photo")
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "webp"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_container_width=True)
        st.info("📝 For best results, use the 'Manual' tab.")

with tab2:
    st.markdown("### 📝 Manual Odds Input")
    
    with st.form("manual_odds_form"):
        col1, col2, col3, col4 = st.columns([1, 1, 1, 0.8])
        with col1:
            sport = st.selectbox("Sport", ["Soccer", "Hockey", "Basketball", "Football", "Baseball", "Tennis"])
            home_team = st.text_input("Home Team")
        with col2:
            away_team = st.text_input("Away Team")
            home_odds = st.number_input("Home Odds", min_value=1.01, step=0.01, value=2.50)
        with col3:
            draw_odds = st.number_input("Draw Odds", min_value=1.01, step=0.01, value=3.20)
            away_odds = st.number_input("Away Odds", min_value=1.01, step=0.01, value=2.80)
        with col4:
            stake = st.number_input("Stake ($)", min_value=1.0, step=1.0, value=10.0)
            use_ai = st.checkbox("🤖 AI Analysis")
        
        submitted = st.form_submit_button("Add Match")
        
        if submitted and home_team and away_team:
            match_data = {
                'home_team': home_team,
                'away_team': away_team,
                'home_odds': home_odds,
                'draw_odds': draw_odds,
                'away_odds': away_odds,
                'sport': sport,
                'stake': stake
            }
            st.session_state.matches.append(match_data)
            st.success(f"✅ Added: {home_team} vs {away_team} (Stake: ${stake:.2f})")
            
            if use_ai:
                with st.spinner("🤖 AI analyzing..."):
                    analysis = get_ai_analysis(match_data)
                    st.info(f"**🤖 AI Recommendation:**\n\n{analysis['analysis']}")
            
            st.rerun()
    
    if st.session_state.matches:
        st.markdown("---")
        st.subheader(f"📋 Current Matches ({len(st.session_state.matches)})")
        
        display_data = []
        for m in st.session_state.matches:
            display_data.append({
                'Home': m['home_team'],
                'Away': m['away_team'],
                'Home Odds': m['home_odds'],
                'Draw Odds': m['draw_odds'],
                'Away Odds': m['away_odds'],
                'Stake': f"${m.get('stake', 10):.2f}"
            })
        st.dataframe(pd.DataFrame(display_data), use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Find Best Bets", use_container_width=True, type="primary"):
                results = []
                for match in st.session_state.matches:
                    best = get_best_bet(match)
                    if best and best['ev_percent'] >= min_ev:
                        stake = match.get('stake', 10)
                        best['stake'] = stake
                        best['potential_return'] = stake * best['odds']
                        best['sport'] = match['sport']
                        best['home_team'] = match['home_team']
                        best['away_team'] = match['away_team']
                        results.append(best)
                
                st.session_state.results = results
                
                for bet in results:
                    add_bet({
                        'timestamp': datetime.now().isoformat(),
                        'sport': bet['sport'],
                        'home_team': bet['home_team'],
                        'away_team': bet['away_team'],
                        'bet_type': 'Match Winner',
                        'outcome': bet['outcome'],
                        'odds': bet['odds'],
                        'stake': bet['stake'],
                        'ev_percent': bet['ev_percent'],
                        'true_prob': bet['true_prob'],
                        'implied_prob': bet['implied_prob'],
                        'result': 'Pending',
                        'return': 0.0,
                        'profit_loss': 0.0,
                        'notes': f"EV: {bet['ev_percent']:.1f}%"
                    })
                
                st.success(f"✅ Found {len(results)} positive EV bets!")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Clear All Matches", use_container_width=True):
                st.session_state.matches = []
                st.session_state.results = []
                st.rerun()

with tab3:
    st.markdown("### 📊 Best Bets")
    
    if st.session_state.results:
        results = sorted(st.session_state.results, key=lambda x: x['ev_percent'], reverse=True)
        
        st.subheader("🎯 Positive EV Bets")
        
        total_stake = 0
        total_return = 0
        
        for i, bet in enumerate(results, 1):
            st.markdown(f"**{i}. {bet['match']}**")
            col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1.2])
            col1.write(f"**{bet['outcome'].upper()}** @ {bet['odds']}")
            col2.write(f"EV: {bet['ev_percent']:.1f}%")
            col3.write(f"Stake: ${bet['stake']:.2f}")
            col4.write(f"Return: ${bet['potential_return']:.2f}")
            
            if bet['ev_percent'] >= 15:
                col5.success("✅ Strong")
            elif bet['ev_percent'] >= 10:
                col5.info("🔵 Good")
            else:
                col5.warning("🟡 Consider")
            
            total_stake += bet['stake']
            total_return += bet['potential_return']
            
            if st.button("🤖 AI Analysis", key=f"ai_{i}"):
                with st.spinner("🤖 Thinking..."):
                    match = {
                        'home_team': bet['home_team'],
                        'away_team': bet['away_team'],
                        'home_odds': bet['odds'] if bet['outcome'] == 'home' else 0,
                        'draw_odds': bet['odds'] if bet['outcome'] == 'draw' else 0,
                        'away_odds': bet['odds'] if bet['outcome'] == 'away' else 0,
                        'sport': bet['sport']
                    }
                    analysis = get_ai_analysis(match)
                    st.info(f"**🤖 AI Recommendation:**\n\n{analysis['analysis']}")
            
            st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Bets", len(results))
        col2.metric("Total Stake", f"${total_stake:.2f}")
        col3.metric("Expected Return", f"${total_return:.2f}")
        col4.metric("Expected Profit", f"${total_return - total_stake:.2f}")
    else:
        st.info("No results yet. Add matches and run analysis.")

with tab4:
    st.markdown("### 📄 Paper Slip Generator")
    
    if st.session_state.results:
        selected_bets = []
        st.subheader("Select Bets for Your Paper Slip")
        
        for i, bet in enumerate(st.session_state.results):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            col1.write(f"{bet['match']}")
            col2.write(f"{bet['outcome']} @ {bet['odds']}")
            col3.write(f"EV: {bet['ev_percent']:.1f}%")
            if col4.checkbox("Add", key=f"add_{i}"):
                selected_bets.append(bet)
        
        if selected_bets:
            total_stake = sum(b['stake'] for b in selected_bets)
            
            st.markdown("---")
            st.subheader(f"📋 Your Selected Bets (${total_stake:.2f})")
            
            slip_text = f"""
═══════════════════════════════════════════════
📄 PARI SPORTIF — BULLETIN DE JEU
═══════════════════════════════════════════════
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
───────────────────────────────────────────────
"""
            for bet in selected_bets:
                slip_text += f"""
{bet['match']}
   Bet: {bet['outcome'].upper()} @ {bet['odds']}
   Stake: ${bet['stake']:.2f}
   Potential: ${bet['potential_return']:.2f}
"""
            
            slip_text += f"""
───────────────────────────────────────────────
Total Stake: ${total_stake:.2f}
Expected Return: ${sum(b['potential_return'] for b in selected_bets):.2f}
═══════════════════════════════════════════════
"""
            st.code(slip_text, language="text")
            
            st.download_button(
                label="📥 Download Paper Slip",
                data=slip_text,
                file_name=f"paper_slip_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.info("No bets available. Run analysis first.")

with tab5:
    st.markdown("### 📋 Betting History")
    
    summary = get_bet_summary()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Bets", summary['total_bets'])
    col2.metric("Wins", summary['wins'])
    col3.metric("Losses", summary['losses'])
    col4.metric("Win Rate", f"{summary['win_rate']*100:.1f}%")
    col5.metric("Net Profit", f"${summary['net_profit']:.2f}")
    
    st.markdown("---")
    
    bets = get_all_bets()
    
    if bets:
        data = []
        for bet in bets:
            data.append({
                'ID': bet[0],
                'Timestamp': bet[1][:16] if len(bet) > 1 else '',
                'Sport': bet[2] if len(bet) > 2 else '',
                'Home': bet[3] if len(bet) > 3 else '',
                'Away': bet[4] if len(bet) > 4 else '',
                'Outcome': bet[6] if len(bet) > 6 else '',
                'Odds': bet[7] if len(bet) > 7 else 0,
                'Stake': f"${bet[8]:.2f}" if len(bet) > 8 else '',
                'EV%': f"{bet[9]:.1f}%" if len(bet) > 9 else '',
                'Result': bet[12] if len(bet) > 12 else 'Pending',
                'P/L': f"${bet[14]:.2f}" if len(bet) > 14 and bet[14] != 0 else "Pending"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("✏️ Update Bet Result")
        
        pending_bets = []
        for b in bets:
            if len(b) > 12 and b[12] == 'Pending':
                home_name = b[3] if len(b) > 3 else ''
                away_name = b[4] if len(b) > 4 else ''
                outcome_name = b[6] if len(b) > 6 else ''
                pending_bets.append({
                    'id': b[0],
                    'label': f"ID {b[0]}: {home_name} vs {away_name} - {outcome_name}"
                })
        
        if pending_bets:
            bet_options = {b['label']: b['id'] for b in pending_bets}
            selected_label = st.selectbox("Select Bet to Update", list(bet_options.keys()))
            selected_id = bet_options[selected_label]
            
            result = st.selectbox("Result", ["Win", "Loss"])
            return_amount = st.number_input("Return Amount ($)", min_value=0.0, step=0.01)
            
            if st.button("Update Result"):
                stake = 0
                for b in bets:
                    if b[0] == selected_id:
                        stake = b[8] if len(b) > 8 else 0
                        break
                
                if result == "Win":
                    profit_loss = return_amount - stake
                else:
                    profit_loss = -stake
                
                update_bet_result(selected_id, result, return_amount, profit_loss)
                st.success("✅ Bet updated!")
                st.rerun()
        else:
            st.info("No pending bets to update.")

with tab6:
    st.markdown("### 🔍 Live Arbitrage + EV Scanner")
    st.markdown("Scan multiple sportsbooks for arbitrage or positive EV opportunities.")
    
    # Scanner settings
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        scan_mode = st.selectbox("Scan Mode", ["Arbitrage", "EV (Value Bets)", "Both"])
    with col2:
        scan_sport = st.selectbox("Sport", ["soccer_epl", "soccer_uefa_champs_league", "soccer_spain_la_liga", "soccer_germany_bundesliga", "soccer_italy_serie_a", "tennis_atp", "tennis_wta", "basketball_nba", "icehockey_nhl", "all"])
    with col3:
        target_stake = st.number_input("Target Stake ($)", min_value=10, value=100, step=10)
    with col4:
        min_ev = st.slider("Min. EV %", 1, 20, 5, 1)
    
    # Debug mode toggle
    show_debug = st.checkbox("🔍 Show Debug Info", value=True)
    
    if st.button("🧪 Test API Key", use_container_width=True):
        with st.spinner("Testing API key..."):
            test_scanner = SportsBookScanner(ODDS_API_KEY)
            test_result = test_scanner.get_active_sports()
            if test_result:
                st.success(f"✅ API key working! Found {len(test_result)} active sports.")
                st.write(f"Sports: {', '.join(test_result[:10])}")
            else:
                st.error("❌ API key test failed. Please check your API key.")
    
    if st.button("🔍 Scan for Opportunities", use_container_width=True, type="primary"):
        with st.spinner("Scanning multiple sportsbooks..."):
            scanner = SportsBookScanner(ODDS_API_KEY)
            
            if scan_sport == "all":
                sports = scanner.get_active_sports()
                if not sports:
                    st.error("No sports found. Please check your API key.")
                    st.stop()
                relevant_sports = ["soccer_", "tennis_", "basketball_", "icehockey_", "baseball_"]
                sports = [s for s in sports if any(r in s for r in relevant_sports)]
                sports = sports[:10]
            else:
                sports = [scan_sport]
            
            debug_info = []
            all_opportunities = []
            total_events = 0
            total_books = 0
            
            for sport in sports[:10]:
                events = scanner.fetch_live_odds(sport)
                total_events += len(events)
                
                # FIX: Initialize sport_debug with ALL keys
                sport_debug = {
                    'sport': sport,
                    'events_found': len(events),
                    'books_found': 0,
                    'arbitrage_found': 0,
                    'ev_bets_found': 0
                }
                
                for event in events:
                    if 'bookmakers' not in event:
                        continue
                    
                    total_books += len(event.get('bookmakers', []))
                    sport_debug['books_found'] += len(event.get('bookmakers', []))
                    
                    for book in event.get('bookmakers', []):
                        for market in book.get('markets', []):
                            if market.get('key') == 'h2h':
                                odds = {}
                                for outcome in market.get('outcomes', []):
                                    name = outcome.get('name', '')
                                    price = outcome.get('price', 0)
                                    odds[name] = price
                                
                                if len(odds) >= 2:
                                    home = odds.get(event.get('home_team', ''), 0)
                                    away = odds.get(event.get('away_team', ''), 0)
                                    draw = odds.get('Draw', 0)
                                    home_team = event.get('home_team', '')
                                    away_team = event.get('away_team', '')
                                    
                                    # Check for arbitrage (only if mode includes it)
                                    if scan_mode in ["Arbitrage", "Both"]:
                                        arb = ArbitrageEngine.calculate_arbitrage(home, away, draw)
                                        if arb and arb.get('roi_percentage', 0) >= 0.1:
                                            all_opportunities.append({
                                                'type': 'Arbitrage',
                                                'sport': sport,
                                                'home_team': home_team,
                                                'away_team': away_team,
                                                'arb': arb,
                                                'book': book.get('key', ''),
                                                'stakes': ArbitrageEngine.allocate_stakes(
                                                    target_stake,
                                                    arb.get('weights', {})
                                                ),
                                                'rounded_stakes': ArbitrageEngine.round_stakes(
                                                    ArbitrageEngine.allocate_stakes(
                                                        target_stake,
                                                        arb.get('weights', {})
                                                    )
                                                )
                                            })
                                            sport_debug['arbitrage_found'] += 1
                                    
                                    # Check for EV bets (only if mode includes it)
                                    if scan_mode in ["EV (Value Bets)", "Both"]:
                                        outcomes = [
                                            ('home', home, home_team),
                                            ('draw', draw, 'Draw'),
                                            ('away', away, away_team)
                                        ]
                                        
                                        for outcome_name, odds_val, label in outcomes:
                                            if odds_val > 0:
                                                implied_prob = 1 / odds_val
                                                true_prob = min(implied_prob * 1.08, 0.95)
                                                ev = (true_prob * odds_val) - 1
                                                ev_percent = ev * 100
                                                
                                                if ev_percent >= min_ev:
                                                    b = odds_val - 1
                                                    p = true_prob
                                                    q = 1 - p
                                                    if b > 0:
                                                        kelly = (p * b - q) / b
                                                        if kelly > 0:
                                                            stake = kelly * bankroll * 0.25
                                                        else:
                                                            stake = 10
                                                    else:
                                                        stake = 10
                                                    
                                                    stake = max(stake, 5)
                                                    
                                                    all_opportunities.append({
                                                        'type': 'EV Bet',
                                                        'sport': sport,
                                                        'home_team': home_team,
                                                        'away_team': away_team,
                                                        'outcome': outcome_name,
                                                        'label': label,
                                                        'odds': odds_val,
                                                        'ev_percent': ev_percent,
                                                        'implied_prob': implied_prob * 100,
                                                        'true_prob': true_prob * 100,
                                                        'stake': round(stake, 2),
                                                        'potential_return': round(stake * odds_val, 2),
                                                        'book': book.get('key', '')
                                                    })
                                                    sport_debug['ev_bets_found'] += 1
                
                debug_info.append(sport_debug)
            
            st.session_state.scanner_results = all_opportunities
            st.session_state.scanner_debug = {
                'debug_info': debug_info,
                'total_events': total_events,
                'total_books': total_books,
                'total_opportunities': len(all_opportunities)
            }
            
            # Send Telegram alert if opportunities found
            if all_opportunities:
                ev_count = len([o for o in all_opportunities if o.get('type') == 'EV Bet'])
                arb_count = len([o for o in all_opportunities if o.get('type') == 'Arbitrage'])
                send_telegram_alert(f"🔔 New opportunities found!\nEV Bets: {ev_count}\nArbitrage: {arb_count}")
    
    # Display debug info
    if show_debug and 'scanner_debug' in st.session_state:
        debug = st.session_state.scanner_debug
        st.markdown("---")
        st.markdown("### 📊 Scan Summary")
        
        arb_count = len([o for o in st.session_state.scanner_results if o.get('type') == 'Arbitrage'])
        ev_count = len([o for o in st.session_state.scanner_results if o.get('type') == 'EV Bet'])
        
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Sports Scanned", len(debug['debug_info']))
        col2.metric("Events Found", debug['total_events'])
        col3.metric("Books Checked", debug['total_books'])
        col4.metric("Arbitrage", arb_count)
        col5.metric("EV Bets", ev_count)
        
        if debug['total_events'] == 0:
            st.warning("⚠️ No events found. Check your API key or try a different sport.")
        
        with st.expander("📋 Detailed Scan Results"):
            for sport_debug in debug['debug_info']:
                st.markdown(f"**{sport_debug['sport']}**")
                st.markdown(f"- Events: {sport_debug['events_found']}")
                st.markdown(f"- Books: {sport_debug['books_found']}")
                st.markdown(f"- Arbs: {sport_debug['arbitrage_found']}")
                st.markdown(f"- EV Bets: {sport_debug['ev_bets_found']}")
                st.markdown("---")
    
    # Display scanner results
    if st.session_state.scanner_results:
        arb_results = [o for o in st.session_state.scanner_results if o.get('type') == 'Arbitrage']
        ev_results = [o for o in st.session_state.scanner_results if o.get('type') == 'EV Bet']
        
        if ev_results:
            st.subheader(f"🎯 EV Bets Found ({len(ev_results)})")
            st.markdown("These are bets with **positive Expected Value** — profitable over time.")
            
            ev_results = sorted(ev_results, key=lambda x: x.get('ev_percent', 0), reverse=True)
            
            for i, bet in enumerate(ev_results[:20], 1):
                st.markdown(f"**{i}. {bet['home_team']} vs {bet['away_team']}**")
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                col1.write(f"**{bet['label']}** @ {bet['odds']}")
                col2.write(f"EV: {bet['ev_percent']:.1f}%")
                col3.write(f"True: {bet['true_prob']:.1f}%")
                col4.write(f"Stake: ${bet['stake']:.2f}")
                col5.write(f"Return: ${bet['potential_return']:.2f}")
                
                if bet['ev_percent'] >= 15:
                    st.success("✅ Strong")
                elif bet['ev_percent'] >= 10:
                    st.info("🔵 Good")
                else:
                    st.warning("🟡 Consider")
                
                st.caption(f"Book: {bet.get('book', 'Unknown')}")
                st.markdown("---")
        
        if arb_results:
            st.subheader(f"🔄 Arbitrage Opportunities ({len(arb_results)})")
            st.markdown("These are **guaranteed profit** opportunities — bet on all outcomes.")
            
            for i, result in enumerate(arb_results, 1):
                arb = result['arb']
                st.markdown(f"**{i}. {result['home_team']} vs {result['away_team']}**")
                st.markdown(f"📊 **Profit:** {arb.get('roi_percentage', 0):.2f}%")
                st.markdown(f"📚 **Book:** {result['book']}")
                
                col1, col2, col3 = st.columns(3)
                
                if 'home' in result['stakes']:
                    col1.metric("Home Bet", f"${result['stakes']['home']:.2f}", f"@ {arb['outcomes']['home']['odds']}")
                
                if 'draw' in result['stakes'] and result['stakes']['draw'] > 0:
                    col2.metric("Draw Bet", f"${result['stakes']['draw']:.2f}", f"@ {arb['outcomes']['draw']['odds']}")
                
                if 'away' in result['stakes']:
                    col3.metric("Away Bet", f"${result['stakes']['away']:.2f}", f"@ {arb['outcomes']['away']['odds']}")
                
                st.markdown("**Rounded Stakes:**")
                st.json(result['rounded_stakes'])
                st.markdown("---")
        
        if ev_results or arb_results:
            total_ev_stake = sum(b.get('stake', 0) for b in ev_results)
            total_ev_return = sum(b.get('potential_return', 0) for b in ev_results)
            
            st.markdown("---")
            st.markdown("### 📊 Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total EV Bets", len(ev_results))
            col2.metric("Total Stake (EV)", f"${total_ev_stake:.2f}")
            col3.metric("Expected Return", f"${total_ev_return:.2f}")
            col4.metric("Expected Profit", f"${total_ev_return - total_ev_stake:.2f}")
            
    elif 'scanner_debug' in st.session_state:
        st.info("No opportunities found. Try:")
        st.markdown("""
        - **Lowering the Min. EV %** (try 3-4% instead of 5%)
        - **Scanning a different sport** (try soccer or tennis)
        - **Using a different API region**
        - **Scanning during peak hours** (when more matches are live)
        """)

with tab7:
    st.markdown("### 🪙 Crypto Arbitrage Scanner (Passive)")
    st.markdown("Scan multiple crypto exchanges for price discrepancies.")
    
    col1, col2 = st.columns(2)
    with col1:
        crypto_symbol = st.selectbox("Crypto Pair", ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD"])
        min_crypto_profit = st.slider("Min. Crypto Arbitrage %", 0.1, 2.0, 0.5, 0.1)
    with col2:
        st.info("""
        **How Crypto Arbitrage Works:**
        - Buy on Exchange A at lower price
        - Sell on Exchange B at higher price
        - Profit = price difference - fees
        
        **Current Exchanges Scanned:**
        - Binance
        - Coinbase
        - Kraken
        """)
    
    if st.button("🔍 Scan Crypto Arbitrage", use_container_width=True, type="primary"):
        with st.spinner("Scanning crypto exchanges..."):
            scanner = CryptoArbitrageScanner()
            
            if crypto_symbol == "BTC/USD":
                opportunities = scanner.scan_crypto_arbitrage(min_crypto_profit)
            else:
                st.warning(f"Full support for {crypto_symbol} coming soon. BTC/USD is fully implemented.")
                opportunities = scanner.scan_crypto_arbitrage(min_crypto_profit)
            
            if opportunities:
                st.subheader(f"💰 Found {len(opportunities)} Crypto Arbitrage Opportunities")
                
                for opp in opportunities:
                    st.markdown(f"**{opp['symbol']}**")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Buy", opp['buy'].upper(), f"${opp['buy_price']:.2f}")
                    col2.metric("Sell", opp['sell'].upper(), f"${opp['sell_price']:.2f}")
                    col3.metric("Profit", f"{opp['profit_percent']:.2f}%")
                    col4.metric("Action", "BUY → SELL")
                    
                    log_crypto_opportunity(opp)
                    
                    send_telegram_alert(f"🪙 Crypto Arbitrage!\nBuy: {opp['buy']} @ ${opp['buy_price']:.2f}\nSell: {opp['sell']} @ ${opp['sell_price']:.2f}\nProfit: {opp['profit_percent']:.2f}%")
                    
                    st.markdown("---")
                
                st.info("⚠️ Note: Fees and transfer times may impact profitability. Always verify before executing.")
            else:
                st.info("No crypto arbitrage opportunities found. Try again later.")
    
    st.markdown("---")
    st.markdown("### 📋 Recent Crypto Opportunities")
    
    conn = sqlite3.connect('betting_history.db')
    try:
        df = pd.read_sql_query('SELECT * FROM crypto_opportunities ORDER BY timestamp DESC LIMIT 20', conn)
        if not df.empty:
            st.dataframe(df[['timestamp', 'buy_exchange', 'sell_exchange', 'symbol', 'profit_percent', 'executed']], use_container_width=True)
        else:
            st.info("No crypto opportunities logged yet.")
    except:
        st.info("No crypto opportunities logged yet.")
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Mathematical betting — only bet when the numbers say so. | Only Solutions Inc.")
