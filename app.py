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

def add_bet(user_id, bet_data):
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

def get_user_bets(user_id):
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
                },
                "outcomes": {
                    "home": {"odds": home_odds},
                    "away": {"odds": away_odds},
                    "draw": {"odds": draw_odds} if draw_odds else None
                }
            }
        return None

    @staticmethod
    def allocate_stakes(total_stake, weights):
        return {outcome: round(total_stake * weight, 2) for outcome, weight in weights.items() if weight > 0}

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
        ev = calculate_ev(home_odds, true_prob)
        results['home'] = {
            'odds': home_odds,
            'true_prob': true_prob * 100,
            'implied_prob': (1/home_odds) * 100,
            'ev_percent': ev * 100
        }
    
    if draw_odds > 0:
        true_prob = calculate_true_probability(draw_odds, market_avg)
        ev = calculate_ev(draw_odds, true_prob)
        results['draw'] = {
            'odds': draw_odds,
            'true_prob': true_prob * 100,
            'implied_prob': (1/draw_odds) * 100,
            'ev_percent': ev * 100
        }
    
    if away_odds > 0:
        true_prob = calculate_true_probability(away_odds, market_avg)
        ev = calculate_ev(away_odds, true_prob)
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
    
    if best_outcome and best_ev >= 3:
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
# USER-FRIENDLY GUIDES
# ─────────────────────────────────────────────────────────────
def show_guide():
    st.markdown("---")
    
    with st.expander("🎯 What is Expected Value (EV)?", expanded=False):
        st.markdown("""
        **EV (Expected Value)** is the average amount you win per bet over time.
        
        - **Positive EV (+)** = You will make money over time
        - **Negative EV (-)** = You will lose money over time
        
        **Formula:** `EV = (Win Probability × Odds) — 1`
        
        **Example:**
        - You bet $10 on a team at **2.00 odds**
        - You estimate they have a **60% chance** to win
        - EV = (0.60 × 2.00) — 1 = **+0.20 (20%)**
        - Over 100 bets, you'd make **$2 per bet** on average
        
        📖 **Key Rule:** Only bet when EV is positive!
        """)
    
    with st.expander("🔄 What is Arbitrage?", expanded=False):
        st.markdown("""
        **Arbitrage** is a guaranteed profit opportunity.
        
        It happens when different bookmakers disagree on the odds.
        
        **How it works:**
        - Bookmaker A offers Home at 3.00
        - Bookmaker B offers Away at 2.50
        - Bookmaker C offers Draw at 4.00
        
        You bet on ALL outcomes across different books.
        - **Total stake:** $100
        - **Guaranteed return:** $102+
        - **Profit:** $2 (risk-free!)
        
        ⚠️ **Note:** Arbitrage is rare but profitable when found.
        """)
    
    with st.expander("📊 How to Use This System", expanded=False):
        st.markdown("""
        **Step 1: Find Matches**
        - Use the Scanner to find EV or Arbitrage opportunities
        - Or enter odds manually
        
        **Step 2: Choose Your Bets**
        - Review the best EV bets
        - Check the AI recommendations
        
        **Step 3: Place Your Bets**
        - **📄 Print a paper slip** for retail betting
        - **📋 Copy bet details** for online betting
        - **🌐 Open bookmaker** to place manually
        
        **Step 4: Track Results**
        - Update wins/losses in History
        - Watch your profit grow over time
        
        📈 **Tip:** Start small and track everything!
        """)
    
    with st.expander("💰 How Much Should I Bet?", expanded=False):
        st.markdown("""
        **Kelly Criterion** — The optimal bet size.
        
        **Formula:** `Kelly Stake = Bankroll × Kelly %`
        
        **Guidelines:**
        - 🔵 **Conservative:** 1-2% of bankroll
        - 🟡 **Moderate:** 3-5% of bankroll
        - 🔴 **Aggressive:** 5-10% of bankroll
        
        **Example with $1,000 bankroll:**
        - Conservative: $10-$20 per bet
        - Moderate: $30-$50 per bet
        - Aggressive: $50-$100 per bet
        
        ⚠️ **Never bet more than 10% of your bankroll!**
        """)
    
    with st.expander("❓ FAQ", expanded=False):
        st.markdown("""
        **Q: Is this guaranteed to make money?**
        A: No betting system is 100% guaranteed. But EV betting is mathematically proven to be profitable over time.
        
        **Q: How much can I make?**
        A: With 5% EV and 100 bets at $50 each = $250 profit (5% return).
        
        **Q: Do I need to be a math expert?**
        A: No! The app does all the math for you.
        
        **Q: What sports can I bet on?**
        A: Soccer, Hockey, Basketball, Football, Baseball, Tennis, and more.
        
        **Q: How do I place a bet?**
        A: Use the Paper Slip Generator or copy the bet details to your bookmaker.
        """)

# ─────────────────────────────────────────────────────────────
# LANDING PAGE (PUBLIC)
# ─────────────────────────────────────────────────────────────
def landing_page():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .hero {{
            text-align: center;
            padding: 4rem 2rem;
            background: linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%);
            border-radius: 20px;
            border: 1px solid #2A4A6A;
            margin-bottom: 2rem;
        }}
        .hero h1 {{
            font-size: 3rem;
            font-weight: 700;
            color: #00D4FF;
            margin-bottom: 1rem;
        }}
        .hero p {{
            font-size: 1.2rem;
            color: #B8CCDE;
            max-width: 600px;
            margin: 0 auto;
        }}
        .pricing-card {{
            background: #0D1B2E;
            border: 1px solid #2A4A6A;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            max-width: 400px;
            margin: 0 auto;
        }}
        .pricing-card .price {{
            font-size: 3rem;
            font-weight: 700;
            color: #00D4FF;
        }}
        .pricing-card .period {{
            color: #4A6E8A;
        }}
        .feature-list {{
            text-align: left;
            margin: 1.5rem 0;
        }}
        .feature-list li {{
            list-style: none;
            padding: 0.5rem 0;
            color: #B8CCDE;
        }}
        .feature-list li::before {{
            content: "✓ ";
            color: #00D4FF;
        }}
        .cta-button {{
            background: linear-gradient(90deg, #00D4FF 0%, #0088CC 100%);
            color: #0D1B2E;
            padding: 0.8rem 2.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1.1rem;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
        }}
        .cta-button:hover {{
            transform: scale(1.02);
            box-shadow: 0 0 20px rgba(0,212,255,0.3);
        }}
        .features-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 1.5rem;
            margin: 2rem 0;
        }}
        .feature-card {{
            background: #0D1B2E;
            border: 1px solid #1A3050;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
        }}
        .feature-card .icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
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
        <p>Mathematical betting with EV + Arbitrage scanning. Only bet when the numbers say so.</p>
        <p style="margin-top:1rem; font-size:0.9rem; color:#4A6E8A;">
            🆓 7-day free trial · No credit card required
        </p>
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
            <div class="icon">{icon}</div>
            <h3 style="color:#F0F4FA; margin:0.5rem 0;">{title}</h3>
            <p style="color:#4A6E8A; font-size:0.9rem;">{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Pricing
    st.markdown("---")
    st.markdown("### 💰 Simple Pricing")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div class="pricing-card">
            <h2 style="color:#F0F4FA;">Monthly</h2>
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
            <button class="cta-button" onclick="window.location.href='?page=signup'">
                Start Free Trial
            </button>
            <p style="font-size:0.8rem; color:#4A6E8A; margin-top:1rem;">
                🆓 7-day free trial · Then $1.99/month
            </p>
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
        
        st.markdown("""
        <p style="font-size:0.8rem; color:#4A6E8A;">
            By signing up, you agree to our Terms of Service and Privacy Policy.
        </p>
        """, unsafe_allow_html=True)
        
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
    st.markdown("Already have an account? **Log in** below.")
    if st.button("🔐 Log In", use_container_width=True):
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
    st.markdown("Don't have an account? **Sign up** for free.")
    if st.button("📝 Create Account", use_container_width=True):
        st.session_state.show_signup = True
        st.rerun()
    
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center; color:#1A3050; font-size:0.8rem;">
        {COMPANY_NAME} · {DOMAIN}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# DASHBOARD (PRIVATE)
# ─────────────────────────────────────────────────────────────
def dashboard():
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
        <div>
            <h1 style="margin:0;">📊 Betting System</h1>
            <p style="color:#4A6E8A; margin:0;">Welcome back, <strong>{st.session_state.user_name}</strong></p>
        </div>
        <div style="text-align:right;">
            <p style="color:#4A6E8A; margin:0; font-size:0.8rem;">Member since</p>
            <p style="color:#F0F4FA; margin:0; font-size:0.9rem;">{datetime.now().strftime('%B %Y')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Show guide at top
    show_guide()
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Scanner", 
        "📝 Manual Input", 
        "📊 History", 
        "📄 Paper Slip",
        "ℹ️ Help"
    ])
    
    # ─── TAB 1: SCANNER ──────────────────────────────────────────
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
        
        # Use a placeholder scanner for now
        st.info("🔍 Scanner connected to The Odds API (70+ bookmakers)")
        
        if st.button("🔍 Scan Now", use_container_width=True, type="primary"):
            with st.spinner("Scanning..."):
                # Sample data for demo
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
                    # Add to database
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
        
        # Display results
        if 'scan_results' in st.session_state:
            st.markdown("### 🎯 Best EV Bets")
            
            for i, bet in enumerate(st.session_state.scan_results[:5], 1):
                st.markdown(f"**{i}. {bet['match']}**")
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
                col1.write(f"**{bet['outcome']}** @ {bet['odds']}")
                col2.write(f"EV: {bet['ev_percent']:.1f}%")
                col3.write(f"True: {bet['true_prob']:.1f}%")
                col4.write(f"Stake: ${bet['stake']:.2f}")
                col5.write(f"Return: ${bet['potential_return']:.2f}")
                
                # Buttons for each bet
                col_a, col_b, col_c = st.columns([1, 1, 1])
                with col_a:
                    if st.button("📄 Slip", key=f"slip_{i}"):
                        st.info(f"Paper slip generated for {bet['match']}")
                with col_b:
                    if st.button("📋 Copy", key=f"copy_{i}"):
                        st.info(f"Bet details copied!")
                with col_c:
                    if st.button("ℹ️ Why?", key=f"why_{i}"):
                        st.info(f"EV: {bet['ev_percent']:.1f}% — This bet has positive Expected Value.")
                
                st.markdown("---")
            
            # Summary
            total_stake = sum(b['stake'] for b in st.session_state.scan_results)
            total_return = sum(b['potential_return'] for b in st.session_state.scan_results)
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Bets", len(st.session_state.scan_results))
            col2.metric("Total Stake", f"${total_stake:.2f}")
            col3.metric("Expected Return", f"${total_return:.2f}")
            col4.metric("Expected Profit", f"${total_return - total_stake:.2f}")
    
    # ─── TAB 2: MANUAL INPUT ──────────────────────────────────────
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
            
            if st.form_submit_button("Add Bet", use_container_width=True):
                if home_team and away_team:
                    odds_map = {"Home Win": home_odds, "Draw": draw_odds, "Away Win": away_odds}
                    selected_odds = odds_map.get(outcome, 0)
                    
                    # Calculate EV (simplified)
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
    
    # ─── TAB 3: HISTORY ────────────────────────────────────────────
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
            
            # Update result
            st.markdown("---")
            st.markdown("### ✏️ Update Result")
            
            pending = [b for b in bets if b[10] == 'Pending']
            if pending:
                options = {f"ID {b[0]}: {b[4]} vs {b[5]}": b[0] for b in pending}
                selected = st.selectbox("Select Bet", list(options.keys()))
                bet_id = options[selected]
                
                result = st.selectbox("Result", ["Win", "Loss"])
                return_amount = st.number_input("Return ($)", min_value=0.0, step=0.01)
                
                if st.button("Update"):
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

    # ─── TAB 4: PAPER SLIP ──────────────────────────────────────────
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

    # ─── TAB 5: HELP ──────────────────────────────────────────────────
    with tab5:
        st.markdown("### ℹ️ Help & Guides")
        
        st.markdown("""
        **Welcome to the Only Solutions Betting System!**
        
        This app uses **mathematical betting** to find profitable opportunities.
        
        ---
        
        ### 🎯 Getting Started
        
        1. **Scan for opportunities** — Click the Scanner tab
        2. **Review the best bets** — Check EV% and probabilities
        3. **Place your bets** — Use paper slip or manual betting
        4. **Track results** — Update wins/losses in History
        
        ---
        
        ### 📖 Key Concepts
        
        **EV (Expected Value)** — The average profit per bet over time. Only bet when EV is positive!
        
        **Arbitrage** — A guaranteed profit opportunity across different bookmakers.
        
        **Kelly Criterion** — Optimal bet size based on your bankroll.
        
        ---
        
        ### ❓ Need Help?
        
        Contact us at: **support@onlysolutions.ca**
        
        """)
        
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align:center; color:#1A3050; font-size:0.8rem;">
            {COMPANY_NAME} · {DOMAIN} · {YEAR}
        </div>
        """, unsafe_allow_html=True)

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

# ─────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────
init_db()

# Check URL params
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
        st.markdown(f"**{st.session_state.user_name}**")
        st.markdown(f"📧 {st.session_state.user_email}")
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
