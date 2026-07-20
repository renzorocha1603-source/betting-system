import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import requests
import re
import io
from datetime import datetime
from PIL import Image
import os
import base64

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
# HARDCODED DEEPSEEK API KEY
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = "sk-09832202e2c74c7ea73891197056a8e6"

# ─────────────────────────────────────────────────────────────
# SIDEBAR — BANKROLL & SETTINGS
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    bankroll = st.number_input("Bankroll ($)", value=1000, min_value=100, step=100)
    min_ev = st.slider("Min. EV %", 1, 25, 5, 1)
    kelly_fraction = st.slider("Kelly Fraction", 0.1, 0.5, 0.25, 0.05)
    st.markdown("---")
    st.caption("v4.2 · Only Solutions Inc.")

# ─────────────────────────────────────────────────────────────
# DEEPSEEK AI FUNCTION
# ─────────────────────────────────────────────────────────────
def ask_deepseek(prompt: str) -> str:
    """Get analysis from DeepSeek AI using hardcoded key"""
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
                {"role": "system", "content": "You are Allison, a professional betting analyst. You MUST choose exactly ONE outcome to bet on — the best one based on value. Never recommend all three. Be decisive. Format: 'BEST BET: [outcome] @ [odds]. Why: [brief reason]'"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 300
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=15)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        elif response.status_code == 401:
            return "⚠️ Invalid DeepSeek API key. Please check your key."
        else:
            return f"⚠️ API Error: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "⚠️ AI request timed out. Please try again."
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

def get_ai_analysis(match: dict) -> dict:
    """Get AI analysis for a single match — picks ONE best bet"""
    prompt = f"""
    Analyze this match and tell me ONLY ONE bet to take.
    
    Match: {match.get('home_team', '')} vs {match.get('away_team', '')}
    Sport: {match.get('sport', 'Soccer')}
    Odds: Home {match.get('home_odds', 0)}, Draw {match.get('draw_odds', 0)}, Away {match.get('away_odds', 0)}
    
    Choose the BEST SINGLE bet out of the three outcomes.
    Answer format exactly: "BEST BET: [outcome] @ [odds]. Why: [one sentence reason]"
    """
    
    response = ask_deepseek(prompt)
    return {'analysis': response}

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

# ─────────────────────────────────────────────────────────────
# EV & ARBITRAGE FUNCTIONS
# ─────────────────────────────────────────────────────────────
def calculate_ev(odds, true_probability):
    return (true_probability * odds) - 1

def calculate_kelly(odds, true_probability, bankroll, fraction=0.25):
    b = odds - 1
    p = true_probability
    q = 1 - p
    if b <= 0:
        return 0
    kelly = (p * b - q) / b
    if kelly < 0:
        return 0
    return kelly * bankroll * fraction

def calculate_arbitrage(home_odds, draw_odds, away_odds, total_investment=100):
    imp_home = 1 / home_odds if home_odds > 0 else 0
    imp_draw = 1 / draw_odds if draw_odds > 0 else 0
    imp_away = 1 / away_odds if away_odds > 0 else 0
    total_imp = imp_home + imp_draw + imp_away
    
    if total_imp >= 1:
        return None
    
    stake_home = (imp_home / total_imp) * total_investment
    stake_draw = (imp_draw / total_imp) * total_investment
    stake_away = (imp_away / total_imp) * total_investment
    
    return_home = stake_home * home_odds
    return_draw = stake_draw * draw_odds
    return_away = stake_away * away_odds
    
    guaranteed_return = min(return_home, return_draw, return_away)
    
    return {
        'stakes': {'home': stake_home, 'draw': stake_draw, 'away': stake_away},
        'total_stake': total_investment,
        'guaranteed_return': guaranteed_return,
        'profit': guaranteed_return - total_investment
    }

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

if not st.session_state.authenticated:
    page_login()

# ─── MAIN DASHBOARD ──────────────────────────────────────────
init_db()

st.title("📊 Betting System — Arbitrage + EV Scanner")
st.markdown(f"**Welcome, {st.session_state.user_name}** | Role: {st.session_state.user_role.upper()}")

# Sidebar with logout
with st.sidebar:
    st.markdown("---")
    if st.button("🚪 Logout", use_container_width=True):
        do_logout()

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 Upload", "📝 Manual", "📊 Results", "📄 Slip", "📋 History"])

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
                with st.spinner("🤖 AI is analyzing..."):
                    analysis = get_ai_analysis(match_data)
                    st.info(f"**AI Analysis:**\n\n{analysis['analysis']}")
            
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
            if st.button("🔍 Run EV Analysis", use_container_width=True, type="primary"):
                results = []
                for match in st.session_state.matches:
                    outcomes = ['home', 'draw', 'away']
                    odds = [match['home_odds'], match['draw_odds'], match['away_odds']]
                    user_stake = match.get('stake', 10)
                    
                    for outcome, odd in zip(outcomes, odds):
                        if odd > 0:
                            implied_prob = 1 / odd
                            true_prob = min(implied_prob * 1.1, 0.95)
                            ev = calculate_ev(odd, true_prob)
                            ev_percent = ev * 100
                            
                            if ev_percent >= min_ev:
                                kelly_stake = calculate_kelly(odd, true_prob, bankroll, kelly_fraction)
                                stake_to_use = user_stake if user_stake > 0 else kelly_stake
                                
                                results.append({
                                    'match': f"{match['home_team']} vs {match['away_team']}",
                                    'outcome': outcome,
                                    'odds': odd,
                                    'ev_percent': ev_percent,
                                    'stake': stake_to_use,
                                    'potential_return': stake_to_use * odd,
                                    'sport': match['sport'],
                                    'home_team': match['home_team'],
                                    'away_team': match['away_team'],
                                    'true_prob': true_prob * 100,
                                    'implied_prob': implied_prob * 100,
                                    'user_stake': user_stake
                                })
                
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
    st.markdown("### 📊 Analysis Results")
    
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
                    st.info(f"**AI Analysis:**\n\n{analysis['analysis']}")
            
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
Expected Profit: ${sum(b['potential_return'] for b in selected_bets) - total_stake:.2f}
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
            # Safely access each field
            bet_id = bet[0] if len(bet) > 0 else 0
            timestamp = bet[1][:16] if len(bet) > 1 and bet[1] else ''
            sport = bet[2] if len(bet) > 2 else ''
            home = bet[3] if len(bet) > 3 else ''
            away = bet[4] if len(bet) > 4 else ''
            outcome = bet[6] if len(bet) > 6 else ''
            odds = bet[7] if len(bet) > 7 else 0
            stake = f"${bet[8]:.2f}" if len(bet) > 8 and bet[8] else '$0.00'
            ev = f"{bet[9]:.1f}%" if len(bet) > 9 and bet[9] else '0.0%'
            result = bet[12] if len(bet) > 12 else 'Pending'
            pl = f"${bet[14]:.2f}" if len(bet) > 14 and bet[14] != 0 else "Pending"
            
            data.append({
                'ID': bet_id,
                'Timestamp': timestamp,
                'Sport': sport,
                'Home': home,
                'Away': away,
                'Outcome': outcome,
                'Odds': odds,
                'Stake': stake,
                'EV%': ev,
                'Result': result,
                'P/L': pl
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("✏️ Update Bet Result")
        
        # Get pending bets safely
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
            bet_options = [b['label'] for b in pending_bets]
            selected_label = st.selectbox("Select Bet to Update", bet_options)
            # Extract the ID from the selected label
            selected_id = int(selected_label.split()[1])
            
            result = st.selectbox("Result", ["Win", "Loss"])
            return_amount = st.number_input("Return Amount ($)", min_value=0.0, step=0.01)
            
            if st.button("Update Result"):
                # Get the stake for this bet
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

# ─────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("Mathematical betting — only bet when the numbers say so. | Only Solutions Inc.")
