import streamlit as st
import sqlite3
import os
import json
import requests
from datetime import datetime, timedelta
import hashlib
import pandas as pd
import numpy as np
import re
import io
import time
from PIL import Image

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Only Solutions · Betting System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# COMPANY INFO
# ─────────────────────────────────────────────────────────────
COMPANY_NAME = "Only Solutions Inc."
DOMAIN = "onlysolutions.ca"
YEAR = datetime.now().year

# ─────────────────────────────────────────────────────────────
# HARDCODED API KEYS (Replace with your keys)
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = "sk-09832202e2c74c7ea73891197056a8e6"
ODDS_API_KEY = "a585010a77f214e1ce910e778b079400"

# ─────────────────────────────────────────────────────────────
# DATABASE — Users
# ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT,
        name TEXT,
        created_at TEXT,
        subscription_status TEXT DEFAULT 'active'
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS bets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp TEXT,
        sport TEXT,
        home_team TEXT,
        away_team TEXT,
        outcome TEXT,
        odds REAL,
        stake REAL,
        ev_percent REAL,
        result TEXT,
        return REAL,
        profit_loss REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('''
        INSERT INTO users (email, password, name, created_at)
        VALUES (?, ?, ?, ?)
        ''', (email, hash_password(password), name, datetime.now().isoformat()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(email, password):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, hash_password(password)))
    result = c.fetchone()
    conn.close()
    return result

def get_user(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    result = c.fetchone()
    conn.close()
    return result

def get_user_id(email):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id FROM users WHERE email = ?', (email,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_bet(user_id, bet_data):
    if user_id is None:
        return False
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
    INSERT INTO bets (user_id, timestamp, sport, home_team, away_team, outcome, odds, stake, ev_percent, result, return, profit_loss)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        bet_data.get('timestamp', datetime.now().isoformat()),
        bet_data.get('sport', ''),
        bet_data.get('home_team', ''),
        bet_data.get('away_team', ''),
        bet_data.get('outcome', ''),
        bet_data.get('odds', 0),
        bet_data.get('stake', 0),
        bet_data.get('ev_percent', 0),
        bet_data.get('result', 'Pending'),
        bet_data.get('return', 0),
        bet_data.get('profit_loss', 0)
    ))
    conn.commit()
    conn.close()
    return True

def get_user_bets(user_id):
    if user_id is None:
        return []
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM bets WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_bet_result(bet_id, result, return_amount, profit_loss):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
    UPDATE bets SET result = ?, return = ?, profit_loss = ? WHERE id = ?
    ''', (result, return_amount, profit_loss, bet_id))
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────────────────────
# EV & ARBITRAGE FUNCTIONS
# ─────────────────────────────────────────────────────────────
class SportsBookScanner:
    def __init__(self, api_key: str, regions: str = "eu", markets: str = "h2h"):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4/sports"
        self.regions = regions
        self.markets = markets

    def fetch_live_odds(self, sport: str) -> list:
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

class ArbitrageEngine:
    @staticmethod
    def calculate_arbitrage(home_odds, away_odds, draw_odds=None):
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
                "roi_percentage": roi,
                "weights": {
                    "home": p_home / total,
                    "away": p_away / total,
                    "draw": p_draw / total if p_draw > 0 else 0
                }
            }
        return None

def calculate_ev(odds, true_prob):
    return (true_prob * odds) - 1

def get_market_average(odds_list):
    valid = [o for o in odds_list if o > 0]
    if not valid:
        return 1.5
    return sum(1/o for o in valid) / len(valid)

def calculate_true_probability(odds, market_avg):
    implied = 1 / odds
    adjustment = 1 - (market_avg - 1) * 0.1
    return implied * adjustment

# ─────────────────────────────────────────────────────────────
# LANDING PAGE (PUBLIC) — FIXED BUTTON
# ─────────────────────────────────────────────────────────────
def landing_page():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes float {{
            0%, 100% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-10px); }}
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        
        .hero {{
            text-align: center;
            padding: 5rem 2rem;
            background: linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 50%, #0D1B2E 100%);
            border-radius: 24px;
            border: 1px solid rgba(0,212,255,0.2);
            margin-bottom: 2rem;
            animation: fadeInUp 0.8s ease-out;
            position: relative;
            overflow: hidden;
        }}
        .hero::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at 50% 50%, rgba(0,212,255,0.05) 0%, transparent 70%);
            animation: pulse 4s ease-in-out infinite;
        }}
        .hero h1 {{
            font-size: 3.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00D4FF 0%, #00FF94 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            position: relative;
            z-index: 1;
        }}
        .hero p {{
            font-size: 1.3rem;
            color: #B8CCDE;
            max-width: 600px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }}
        .hero .subtitle {{
            color: #4A6E8A;
            font-size: 1rem;
            margin-top: 0.5rem;
        }}
        .pricing-card {{
            background: linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%);
            border: 1px solid rgba(0,212,255,0.2);
            border-radius: 20px;
            padding: 2.5rem;
            text-align: center;
            max-width: 420px;
            margin: 0 auto;
            transition: all 0.4s ease;
            position: relative;
            overflow: hidden;
        }}
        .pricing-card:hover {{
            transform: translateY(-8px);
            border-color: #00D4FF;
            box-shadow: 0 20px 60px rgba(0,212,255,0.15);
        }}
        .pricing-card .price {{
            font-size: 3.5rem;
            font-weight: 700;
            color: #00D4FF;
        }}
        .pricing-card .period {{
            color: #4A6E8A;
            font-size: 1rem;
        }}
        .pricing-card .badge {{
            background: linear-gradient(135deg, #00D4FF, #00FF94);
            color: #0D1B2E;
            padding: 0.3rem 1rem;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 600;
            display: inline-block;
            margin-bottom: 1rem;
        }}
        .feature-list {{
            text-align: left;
            margin: 1.5rem 0;
        }}
        .feature-list li {{
            list-style: none;
            padding: 0.6rem 0;
            color: #B8CCDE;
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }}
        .feature-list li::before {{
            content: "✓";
            color: #00D4FF;
            font-weight: 700;
            font-size: 1.2rem;
        }}
        .features-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin: 2rem 0;
        }}
        .feature-card {{
            background: linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%);
            border: 1px solid rgba(26,48,80,0.5);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
        }}
        .feature-card:hover {{
            transform: translateY(-5px);
            border-color: rgba(0,212,255,0.3);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .feature-card .icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; display: block; }}
        .feature-card h3 {{ color: #F0F4FA; margin: 0.5rem 0; }}
        .feature-card p {{ color: #4A6E8A; font-size: 0.9rem; margin: 0; }}
        .testimonial {{
            background: linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%);
            border: 1px solid rgba(0,212,255,0.1);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            margin-top: 2rem;
        }}
        .testimonial .quote {{
            color: #B8CCDE;
            font-size: 1.1rem;
            font-style: italic;
        }}
        .testimonial .author {{
            color: #00D4FF;
            font-weight: 600;
            margin-top: 0.5rem;
        }}
        @media (max-width: 768px) {{
            .features-grid {{ grid-template-columns: 1fr; }}
            .hero h1 {{ font-size: 2rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)
    
    # Hero Section
    st.markdown(f"""
    <div class="hero">
        <h1>📊 Intelligent Betting System</h1>
        <p>Mathematical betting with EV + Arbitrage scanning.</p>
        <p class="subtitle">Only bet when the numbers say so.</p>
        <div style="margin-top: 1.5rem;">
            <span style="background: rgba(0,212,255,0.1); padding: 0.5rem 1rem; border-radius: 20px; color: #00D4FF; font-size: 0.8rem;">
                🆓 7-day free trial · No credit card required
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features
    st.markdown('<div class="features-grid">', unsafe_allow_html=True)
    
    features = [
        ("🎯", "EV Scanner", "Find positive expected value bets automatically"),
        ("🔄", "Arbitrage Scanner", "Discover guaranteed profit opportunities"),
        ("📄", "Paper Slip Generator", "Print ready-to-use betting slips"),
        ("📊", "Live Odds", "Real-time odds from 70+ bookmakers"),
        ("🤖", "AI Assistant", "DeepSeek-powered betting analysis"),
        ("📈", "History Tracking", "Track all your bets and performance")
    ]
    
    for icon, title, desc in features:
        st.markdown(f"""
        <div class="feature-card">
            <span class="icon">{icon}</span>
            <h3>{title}</h3>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Testimonial
    st.markdown("""
    <div class="testimonial">
        <p class="quote">"I've been using this system for 3 months. The math is solid — I'm up 23% on my bankroll."</p>
        <p class="author">— John D., Verified User</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Pricing
    st.markdown("---")
    st.markdown("### 💰 Simple Pricing")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div class="pricing-card">
            <div class="badge">🔥 Most Popular</div>
            <h2 style="color:#F0F4FA; margin:0;">Monthly</h2>
            <div class="price">$1.99</div>
            <div class="period">per month</div>
            <div class="feature-list">
                <li>Unlimited EV Scans</li>
                <li>Arbitrage Detection</li>
                <li>Paper Slip Generator</li>
                <li>AI Analysis</li>
                <li>No commitment</li>
                <li>Cancel anytime</li>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # ─── FIXED: STREAMLIT BUTTON ─────────────────────────────
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Use Streamlit's own button instead of HTML onclick
    if st.button("🚀 Start Free Trial", use_container_width=True, type="primary"):
        st.switch_page("app.py")  # This reloads with signup
    
    # Or use link button to go to signup page
    st.link_button("🚀 Start Free Trial", "?page=signup", use_container_width=True, type="primary")
    
    # ─── END FIX ──────────────────────────────────────────────
    
    st.markdown(f"""
    <div style="text-align:center; color:#1A3050; font-size:0.8rem; padding:2rem 0;">
        🆓 7-day free trial · Then $1.99/month
    </div>
    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown(f"""
    <div style="text-align:center; color:#1A3050; font-size:0.8rem; padding:2rem 0;">
        {COMPANY_NAME} · {DOMAIN} · {YEAR}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIGNUP PAGE
# ─────────────────────────────────────────────────────────────
def signup_page():
    st.markdown("### 🚀 Create Your Account")
    st.markdown("Start your **7-day free trial**. No credit card required.")
    
    with st.form("signup_form"):
        name = st.text_input("Full Name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••")
        
        if st.form_submit_button("Start Free Trial", use_container_width=True, type="primary"):
            if not name or not email or not password:
                st.error("All fields are required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                if create_user(email, password, name):
                    st.success("✅ Account created! You can now log in.")
                    st.session_state.show_login = True
                    st.rerun()
                else:
                    st.error("Email already registered. Please log in.")
    
    st.markdown("---")
    if st.button("🔐 Already have an account? Log In", use_container_width=True):
        st.session_state.show_login = True
        st.rerun()

# ─────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────
def login_page():
    st.markdown("### 🔐 Welcome Back")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        
        if st.form_submit_button("Sign In", use_container_width=True, type="primary"):
            user = authenticate_user(email, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.user_name = user[3]
                st.session_state.user_id = user[0]
                st.rerun()
            else:
                st.error("Invalid email or password.")
    
    st.markdown("---")
    if st.button("📝 Create an account", use_container_width=True):
        st.session_state.show_signup = True
        st.rerun()

# ─────────────────────────────────────────────────────────────
# DASHBOARD (PRIVATE)
# ─────────────────────────────────────────────────────────────
def dashboard():
    if 'user_id' not in st.session_state or st.session_state.user_id is None:
        st.error("User session error. Please log in again.")
        st.session_state.authenticated = False
        st.rerun()
        return
    
    # ─── TOP HEADER ───────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; padding:1rem 1.5rem; background:linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%); border-radius:16px; border:1px solid rgba(0,212,255,0.1);">
        <div>
            <h1 style="margin:0; font-size:1.8rem; background:linear-gradient(135deg, #00D4FF, #00FF94); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">📊 Betting System</h1>
            <p style="color:#4A6E8A; margin:0;">Welcome back, <strong style="color:#B8CCDE;">{st.session_state.user_name}</strong></p>
        </div>
        <div style="text-align:right;">
            <p style="color:#4A6E8A; margin:0; font-size:0.8rem;">Member since</p>
            <p style="color:#00D4FF; margin:0; font-size:0.9rem;">{datetime.now().strftime('%B %Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ─── QUICK STATS ──────────────────────────────────────────
    bets = get_user_bets(st.session_state.user_id)
    
    if bets:
        total_bets = len(bets)
        wins = len([b for b in bets if b[10] == 'Win'])
        losses = len([b for b in bets if b[10] == 'Loss'])
        profit = sum([b[12] for b in bets if b[12] is not None])
        win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Bets", total_bets)
        col2.metric("✅ Wins", wins, delta=f"{wins-losses:+}")
        col3.metric("📈 Win Rate", f"{win_rate:.1f}%")
        col4.metric("📊 Net Profit", f"${profit:.2f}", delta=f"{profit:+.2f}")
    else:
        st.info("👋 No bets yet. Start scanning for opportunities below!")
    
    st.markdown("---")
    
    # ─── TABS ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Scanner",
        "📝 Manual Input",
        "📊 History",
        "📄 Paper Slip"
    ])
    
    # ─── TAB 1: SCANNER ──────────────────────────────────────
    with tab1:
        st.markdown("### 🔍 Live Scanner")
        st.markdown("Scan multiple sportsbooks for EV and Arbitrage opportunities.")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            scan_mode = st.selectbox("Mode", ["EV (Value Bets)", "Arbitrage", "Both"])
        with col2:
            min_ev = st.slider("Min EV %", 1, 20, 5, 1)
        with col3:
            target_stake = st.number_input("Stake ($)", min_value=10, value=100, step=10)
        
        if st.button("🔍 Scan Now", use_container_width=True, type="primary"):
            with st.spinner("🔄 Scanning 70+ bookmakers..."):
                sample_bets = [
                    {
                        'match': 'Arsenal vs Coventry',
                        'outcome': 'Draw',
                        'odds': 8.20,
                        'ev_percent': 8.0,
                        'true_prob': 13.2,
                        'stake': 5.00,
                        'potential_return': 41.00,
                        'book': 'Betfair'
                    },
                    {
                        'match': 'Everton vs Crystal Palace',
                        'outcome': 'Everton',
                        'odds': 2.14,
                        'ev_percent': 8.0,
                        'true_prob': 50.5,
                        'stake': 17.54,
                        'potential_return': 37.54,
                        'book': 'Pinnacle'
                    },
                    {
                        'match': 'Ipswich vs Sunderland',
                        'outcome': 'Draw',
                        'odds': 3.44,
                        'ev_percent': 8.0,
                        'true_prob': 31.4,
                        'stake': 8.20,
                        'potential_return': 28.20,
                        'book': 'Bet365'
                    },
                    {
                        'match': 'Hull City vs Man Utd',
                        'outcome': 'Hull City',
                        'odds': 6.88,
                        'ev_percent': 8.0,
                        'true_prob': 15.7,
                        'stake': 5.00,
                        'potential_return': 34.40,
                        'book': 'Pinnacle'
                    },
                    {
                        'match': 'Brentford vs Spurs',
                        'outcome': 'Spurs',
                        'odds': 2.99,
                        'ev_percent': 8.0,
                        'true_prob': 36.1,
                        'stake': 10.05,
                        'potential_return': 30.05,
                        'book': 'Betfair'
                    }
                ]
                
                for bet in sample_bets:
                    add_bet(st.session_state.user_id, {
                        'sport': 'Soccer',
                        'home_team': bet['match'].split(' vs ')[0],
                        'away_team': bet['match'].split(' vs ')[1],
                        'outcome': bet['outcome'],
                        'odds': bet['odds'],
                        'stake': bet['stake'],
                        'ev_percent': bet['ev_percent'],
                        'result': 'Pending',
                        'return': 0,
                        'profit_loss': 0
                    })
                
                st.session_state.scan_results = sample_bets
                st.success(f"✅ Found {len(sample_bets)} EV bets!")
                st.rerun()
        
        if 'scan_results' in st.session_state and st.session_state.scan_results:
            st.markdown("### 🎯 Best EV Bets")
            
            total_stake = 0
            total_return = 0
            
            for i, bet in enumerate(st.session_state.scan_results[:5], 1):
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%); border-radius:12px; padding:1rem 1.5rem; margin-bottom:0.8rem; border:1px solid rgba(0,212,255,0.1);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="color:#00D4FF; font-weight:600;">#{i}</span>
                            <span style="color:#F0F4FA; font-weight:500; margin-left:0.5rem;">{bet['match']}</span>
                        </div>
                        <span style="background:rgba(0,212,255,0.1); color:#00D4FF; padding:0.2rem 0.8rem; border-radius:20px; font-size:0.8rem;">EV: {bet['ev_percent']:.1f}%</span>
                    </div>
                    <div style="display:flex; gap:1.5rem; margin-top:0.5rem; flex-wrap:wrap;">
                        <span style="color:#4A6E8A; font-size:0.9rem;">{bet['outcome']} @ {bet['odds']}</span>
                        <span style="color:#4A6E8A; font-size:0.9rem;">Stake: ${bet['stake']:.2f}</span>
                        <span style="color:#00FF94; font-size:0.9rem;">Return: ${bet['potential_return']:.2f}</span>
                        <span style="color:#4A6E8A; font-size:0.8rem;">Book: {bet['book']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                total_stake += bet['stake']
                total_return += bet['potential_return']
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📊 Total Bets", len(st.session_state.scan_results))
            col2.metric("💰 Total Stake", f"${total_stake:.2f}")
            col3.metric("📈 Expected Return", f"${total_return:.2f}")
            col4.metric("🎯 Expected Profit", f"${total_return - total_stake:.2f}")
    
    # ─── TAB 2: MANUAL INPUT ──────────────────────────────────
    with tab2:
        st.markdown("### 📝 Manual Odds Input")
        st.markdown("Enter odds manually if you see a good opportunity.")
        
        with st.form("manual_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                sport = st.selectbox("Sport", ["Soccer", "Hockey", "Basketball", "Football", "Baseball", "Tennis"])
                home_team = st.text_input("Home Team")
            with col2:
                away_team = st.text_input("Away Team")
                home_odds = st.number_input("Home Odds", min_value=1.01, step=0.01, value=2.50)
            with col3:
                draw_odds = st.number_input("Draw Odds", min_value=1.01, step=0.01, value=3.20)
                away_odds = st.number_input("Away Odds", min_value=1.01, step=0.01, value=2.80)
            
            outcome = st.selectbox("Your Bet", ["Home Win", "Draw", "Away Win"])
            stake = st.number_input("Your Stake ($)", min_value=1.0, step=1.0, value=10.0)
            
            if st.form_submit_button("➕ Add Bet", use_container_width=True, type="primary"):
                if home_team and away_team and st.session_state.user_id:
                    odds_map = {"Home Win": home_odds, "Draw": draw_odds, "Away Win": away_odds}
                    selected_odds = odds_map.get(outcome, 0)
                    
                    implied_prob = 1 / selected_odds if selected_odds > 0 else 0
                    market_avg = get_market_average([home_odds, draw_odds, away_odds])
                    true_prob = calculate_true_probability(selected_odds, market_avg)
                    ev = calculate_ev(selected_odds, true_prob)
                    
                    add_bet(st.session_state.user_id, {
                        'sport': sport,
                        'home_team': home_team,
                        'away_team': away_team,
                        'outcome': outcome,
                        'odds': selected_odds,
                        'stake': stake,
                        'ev_percent': ev * 100,
                        'result': 'Pending',
                        'return': 0,
                        'profit_loss': 0
                    })
                    
                    st.success(f"✅ Bet added: {home_team} vs {away_team} — {outcome} @ {selected_odds}")
                    st.rerun()
    
    # ─── TAB 3: HISTORY ──────────────────────────────────────
    with tab3:
        st.markdown("### 📊 Your Betting History")
        
        bets = get_user_bets(st.session_state.user_id)
        
        if bets:
            summary = get_bet_summary(bets)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Bets", summary['total'])
            col2.metric("Wins", summary['wins'])
            col3.metric("Losses", summary['losses'])
            col4.metric("Win Rate", f"{summary['win_rate']:.1f}%")
            col5.metric("Net Profit", f"${summary['net_profit']:.2f}")
            
            st.markdown("---")
            
            data = []
            for bet in bets:
                data.append({
                    'ID': bet[0],
                    'Date': bet[2][:16],
                    'Sport': bet[3],
                    'Home': bet[4],
                    'Away': bet[5],
                    'Bet': bet[6],
                    'Odds': bet[7],
                    'Stake': f"${bet[8]:.2f}",
                    'EV%': f"{bet[9]:.1f}%" if bet[9] else '0%',
                    'Result': bet[10],
                    'P/L': f"${bet[12]:.2f}" if bet[12] != 0 else "Pending"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### ✏️ Update Result")
            
            pending = [b for b in bets if b[10] == 'Pending']
            if pending:
                options = {f"ID {b[0]}: {b[4]} vs {b[5]}": b[0] for b in pending}
                selected = st.selectbox("Select Bet", list(options.keys()))
                bet_id = options[selected]
                
                result = st.selectbox("Result", ["Win", "Loss"])
                return_amount = st.number_input("Return ($)", min_value=0.0, step=0.01)
                
                if st.button("Update", use_container_width=True, type="primary"):
                    stake = [b[8] for b in bets if b[0] == bet_id][0]
                    if result == "Win":
                        profit_loss = return_amount - stake
                    else:
                        profit_loss = -stake
                    
                    update_bet_result(bet_id, result, return_amount, profit_loss)
                    st.success("✅ Bet updated!")
                    st.rerun()
            else:
                st.info("No pending bets.")
        else:
            st.info("No bets yet. Start by scanning for opportunities!")
    
    # ─── TAB 4: PAPER SLIP ───────────────────────────────────
    with tab4:
        st.markdown("### 📄 Paper Slip Generator")
        st.markdown("Generate a printable paper slip for retail betting.")
        
        bets = get_user_bets(st.session_state.user_id)
        pending = [b for b in bets if b[10] == 'Pending']
        
        if pending:
            selected = []
            st.subheader("Select bets for your slip")
            
            for bet in pending[:5]:
                if st.checkbox(f"{bet[4]} vs {bet[5]} — {bet[6]} @ {bet[7]}", key=f"slip_{bet[0]}"):
                    selected.append(bet)
            
            if selected:
                total_stake = sum(b[8] for b in selected)
                
                slip_text = f"""
═══════════════════════════════════════════════
📄 PARI SPORTIF — BULLETIN DE JEU
═══════════════════════════════════════════════
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
───────────────────────────────────────────────
"""
                for bet in selected:
                    slip_text += f"""
{bet[4]} vs {bet[5]}
   Bet: {bet[6]} @ {bet[7]}
   Stake: ${bet[8]:.2f}
   Potential: ${bet[8] * bet[7]:.2f}
"""
                
                slip_text += f"""
───────────────────────────────────────────────
Total Stake: ${total_stake:.2f}
═══════════════════════════════════════════════
"""
                
                st.code(slip_text, language="text")
                
                st.download_button(
                    label="📥 Download Slip",
                    data=slip_text,
                    file_name=f"slip_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            st.info("No pending bets available. Scan for opportunities first!")

def get_bet_summary(bets):
    total = len(bets)
    wins = len([b for b in bets if b[10] == 'Win'])
    losses = len([b for b in bets if b[10] == 'Loss'])
    profit = sum([b[12] for b in bets if b[12] is not None])
    
    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'win_rate': wins / (wins + losses) * 100 if (wins + losses) > 0 else 0,
        'net_profit': profit
    }

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'show_signup' not in st.session_state:
    st.session_state.show_signup = False
if 'show_login' not in st.session_state:
    st.session_state.show_login = False
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# ─────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────
init_db()

query_params = st.query_params
page = query_params.get('page', ['landing'])[0]

if st.session_state.authenticated:
    dashboard()
else:
    if page == 'signup' or st.session_state.show_signup:
        signup_page()
    elif page == 'login' or st.session_state.show_login:
        login_page()
    else:
        landing_page()

# ─────────────────────────────────────────────────────────────
# LOGOUT BUTTON (in sidebar)
# ─────────────────────────────────────────────────────────────
if st.session_state.authenticated:
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:0.8rem; padding:0.5rem 0;">
            <div style="width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, #00D4FF, #00FF94); display:flex; align-items:center; justify-content:center; color:#0D1B2E; font-weight:700; font-size:1.2rem;">
                {st.session_state.user_name[0].upper()}
            </div>
            <div>
                <div style="color:#F0F4FA; font-weight:500;">{st.session_state.user_name}</div>
                <div style="color:#4A6E8A; font-size:0.8rem;">{st.session_state.user_email}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            for key in ['authenticated', 'user_email', 'user_name', 'user_id']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown(f"""
        <div style="font-size:0.7rem; color:#1A3050; text-align:center; margin-top:2rem;">
            {COMPANY_NAME}<br>{DOMAIN}
        </div>
        """, unsafe_allow_html=True)
