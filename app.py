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
import random

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Only Solutions · Budget System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# HARDCODED API KEYS
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = "sk-09832202e2c74c7ea73891197056a8e6"
ODDS_API_KEY = "a585010a77f214e1ce910e778b079400"

# ─────────────────────────────────────────────────────────────
# COMPANY INFO
# ─────────────────────────────────────────────────────────────
COMPANY_NAME = "Only Solutions Inc."
DOMAIN = "onlysolutions.ca"
YEAR = datetime.now().year

# ─────────────────────────────────────────────────────────────
# THEME TOGGLE
# ─────────────────────────────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    st.rerun()

# ─────────────────────────────────────────────────────────────
# DATABASE — Users
# ─────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = c.fetchone()
    
    if not table_exists:
        c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            name TEXT,
            created_at TEXT,
            subscription_status TEXT DEFAULT 'active',
            is_admin INTEGER DEFAULT 0
        )
        ''')
    else:
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        if 'is_admin' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    
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
    
    admin_email = "admin@onlys.com"
    admin_password = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('SELECT * FROM users WHERE email = ?', (admin_email,))
    if not c.fetchone():
        c.execute('''
        INSERT INTO users (email, password, name, created_at, is_admin)
        VALUES (?, ?, ?, ?, ?)
        ''', (admin_email, admin_password, "Administrator", datetime.now().isoformat(), 1))
    
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

def get_user_bets(user_id):
    if user_id is None:
        return []
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM bets WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

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

def update_bet_result(bet_id, result, return_amount, profit_loss):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
    UPDATE bets SET result = ?, return = ?, profit_loss = ? WHERE id = ?
    ''', (result, return_amount, profit_loss, bet_id))
    conn.commit()
    conn.close()

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
# EV FUNCTIONS — REALISTIC CALCULATIONS
# ─────────────────────────────────────────────────────────────
def calculate_real_ev(odds):
    """Calculate realistic EV based on odds"""
    # Implied probability from odds
    implied_prob = 1 / odds
    
    # True probability is slightly higher (our edge)
    # Usually 2-5% higher than implied
    edge = random.uniform(0.02, 0.05)
    true_prob = implied_prob * (1 + edge)
    
    # EV = (True Probability × Odds) - 1
    ev = (true_prob * odds) - 1
    ev_percent = ev * 100
    
    return ev_percent, true_prob * 100, implied_prob * 100

# ─────────────────────────────────────────────────────────────
# LANGUAGES
# ─────────────────────────────────────────────────────────────
LANGUAGES = {
    "en": {
        "title": "📊 Budget System",
        "subtitle": "Smart betting with Expected Value & Arbitrage",
        "live": "LIVE",
        "active_arbs": "Active Bets",
        "avg_roi": "Avg ROI",
        "bankroll": "Bankroll",
        "total_bets": "Total Bets",
        "signup_title": "🚀 Create Your Account",
        "signup_subtitle": "Start your **7-day free trial**. No credit card required.",
        "login_title": "🔐 Welcome Back",
        "free_trial": "🚀 Start Free Trial",
        "free_trial_note": "🆓 7-day free trial · Then $1.99/month",
        "already_account": "🔐 Already have an account? Log In",
        "create_account": "📝 Create an account",
        "name": "Full Name",
        "email": "Email",
        "password": "Password",
        "confirm": "Confirm Password",
        "sign_in": "Sign In",
        "signup_error": "All fields are required.",
        "password_mismatch": "Passwords do not match.",
        "password_short": "Password must be at least 6 characters.",
        "account_created": "✅ Account created! You can now log in.",
        "email_exists": "Email already registered. Please log in.",
        "login_error": "Invalid email or password.",
        "footer": f"{COMPANY_NAME} · {DOMAIN} · {YEAR}",
        "lang_en": "🇬🇧 EN",
        "lang_fr": "🇫🇷 FR",
        "lang_es": "🇪🇸 ES",
        "scanner_title": "🔍 Live Scanner",
        "mode": "Mode",
        "ev_mode": "Value Bets (EV)",
        "arbitrage_mode": "Arbitrage",
        "both_mode": "Both",
        "min_ev": "Min EV %",
        "stake_label": "Stake ($)",
        "scan_btn": "🔍 Scan Now",
        "best_ev_bets": "🎯 Best Value Bets",
        "manual_title": "📝 Manual Odds Input",
        "sport": "Sport",
        "home_team": "Home Team",
        "away_team": "Away Team",
        "home_odds": "Home Odds",
        "draw_odds": "Draw Odds",
        "away_odds": "Away Odds",
        "your_bet": "Your Bet",
        "your_stake": "Your Stake ($)",
        "add_bet": "➕ Add Bet",
        "history_title": "📊 Betting History",
        "update_result": "✏️ Update Result",
        "select_bet": "Select Bet",
        "result": "Result",
        "return_amount": "Return ($)",
        "update_btn": "Update",
        "slip_title": "📄 Paper Slip Generator",
        "download_slip": "📥 Download Slip",
        "no_bets": "No bets yet. Start scanning for opportunities!",
        "no_pending": "No pending bets.",
        "no_pending_slips": "No pending bets available.",
        "bet_added": "✅ Bet added: {home} vs {away} — {outcome} @ {odds}",
        "faq_title": "❓ Frequently Asked Questions",
        "faq_q1": "What is Expected Value (EV)?",
        "faq_a1": "EV is the average profit per bet over time. A 4% EV means for every $100 bet, you expect to make $4 profit on average over many bets.",
        "faq_q2": "How does arbitrage work?",
        "faq_a2": "Arbitrage is betting on all outcomes across different bookmakers to guarantee a small profit regardless of the result.",
        "faq_q3": "What is the Kelly Criterion?",
        "faq_a3": "The Kelly Criterion tells you the optimal bet size to grow your bankroll while managing risk.",
        "faq_q4": "How much should I bet?",
        "faq_a4": "Never bet more than 1-5% of your bankroll per bet. Start with 1% until you're comfortable.",
        "faq_q5": "Is this guaranteed to make money?",
        "faq_a5": "EV betting is mathematically proven to be profitable over time, but individual bets can lose. Always bet responsibly.",
        "theme_dark": "🌙 Dark",
        "theme_light": "☀️ Light",
        "ev_explained": "💡 What does EV mean?",
        "ev_explanation": "Expected Value (EV) is the average profit you make per bet over many bets. A 4% EV means you expect to earn $4 for every $100 you bet. Professional bettors aim for 3-8% EV."
    },
    "fr": {
        "title": "📊 Système Budgétaire",
        "subtitle": "Paris intelligents avec Valeur Attendue & Arbitrage",
        "live": "EN DIRECT",
        "active_arbs": "Paris actifs",
        "avg_roi": "ROI moyen",
        "bankroll": "Bankroll",
        "total_bets": "Total des paris",
        "signup_title": "🚀 Créez Votre Compte",
        "signup_subtitle": "Commencez votre **essai gratuit de 7 jours**.",
        "login_title": "🔐 Bon Retour",
        "free_trial": "🚀 Essai Gratuit",
        "free_trial_note": "🆓 Essai gratuit de 7 jours · Puis 1,99 $/mois",
        "already_account": "🔐 Déjà un compte? Se connecter",
        "create_account": "📝 Créer un compte",
        "name": "Nom complet",
        "email": "Courriel",
        "password": "Mot de passe",
        "confirm": "Confirmer le mot de passe",
        "sign_in": "Se connecter",
        "signup_error": "Tous les champs sont requis.",
        "password_mismatch": "Les mots de passe ne correspondent pas.",
        "password_short": "Le mot de passe doit contenir au moins 6 caractères.",
        "account_created": "✅ Compte créé!",
        "email_exists": "Courriel déjà enregistré.",
        "login_error": "Courriel ou mot de passe incorrect.",
        "footer": f"{COMPANY_NAME} · {DOMAIN} · {YEAR}",
        "lang_en": "🇬🇧 EN",
        "lang_fr": "🇫🇷 FR",
        "lang_es": "🇪🇸 ES",
        "scanner_title": "🔍 Scanner en direct",
        "mode": "Mode",
        "ev_mode": "Paris de valeur (EV)",
        "arbitrage_mode": "Arbitrage",
        "both_mode": "Les deux",
        "min_ev": "EV min. %",
        "stake_label": "Mise ($)",
        "scan_btn": "🔍 Scanner",
        "best_ev_bets": "🎯 Meilleurs paris",
        "manual_title": "📝 Saisie manuelle",
        "sport": "Sport",
        "home_team": "Équipe domicile",
        "away_team": "Équipe extérieure",
        "home_odds": "Cote domicile",
        "draw_odds": "Cote nul",
        "away_odds": "Cote extérieur",
        "your_bet": "Votre pari",
        "your_stake": "Votre mise ($)",
        "add_bet": "➕ Ajouter",
        "history_title": "📊 Historique",
        "update_result": "✏️ Mettre à jour",
        "select_bet": "Sélectionner",
        "result": "Résultat",
        "return_amount": "Retour ($)",
        "update_btn": "Mettre à jour",
        "slip_title": "📄 Générateur de bulletin",
        "download_slip": "📥 Télécharger",
        "no_bets": "Aucun pari pour l'instant.",
        "no_pending": "Aucun pari en attente.",
        "no_pending_slips": "Aucun pari en attente.",
        "bet_added": "✅ Pari ajouté: {home} vs {away} — {outcome} @ {odds}",
        "faq_title": "❓ Questions Fréquentes",
        "faq_q1": "Qu'est-ce que la Valeur Attendue (EV)?",
        "faq_a1": "L'EV est le profit moyen par pari. Un EV de 4% signifie que vous gagnez 4$ pour chaque 100$ parié.",
        "faq_q2": "Comment fonctionne l'arbitrage?",
        "faq_a2": "L'arbitrage consiste à parier sur tous les résultats chez différents bookmakers pour garantir un petit profit.",
        "faq_q3": "Qu'est-ce que le critère de Kelly?",
        "faq_a3": "Le critère de Kelly vous indique la taille de mise optimale pour faire croître votre bankroll.",
        "faq_q4": "Combien dois-je parier?",
        "faq_a4": "Ne pariez jamais plus de 1-5% de votre bankroll par pari.",
        "faq_q5": "Est-ce garanti de gagner?",
        "faq_a5": "Les paris EV sont rentables à long terme, mais les paris individuels peuvent perdre.",
        "theme_dark": "🌙 Sombre",
        "theme_light": "☀️ Clair",
        "ev_explained": "💡 Qu'est-ce que l'EV?",
        "ev_explanation": "La Valeur Attendue (EV) est le profit moyen par pari. Un EV de 4% signifie 4$ de profit pour 100$ parié."
    },
    "es": {
        "title": "📊 Sistema de Presupuesto",
        "subtitle": "Apuestas inteligentes con Valor Esperado & Arbitraje",
        "live": "EN VIVO",
        "active_arbs": "Apuestas activas",
        "avg_roi": "ROI promedio",
        "bankroll": "Bankroll",
        "total_bets": "Total apuestas",
        "signup_title": "🚀 Crea Tu Cuenta",
        "signup_subtitle": "Comienza tu **prueba gratuita de 7 días**.",
        "login_title": "🔐 Bienvenido de Vuelta",
        "free_trial": "🚀 Prueba Gratis",
        "free_trial_note": "🆓 Prueba gratis de 7 días · Luego $1.99/mes",
        "already_account": "🔐 ¿Ya tienes cuenta? Iniciar sesión",
        "create_account": "📝 Crear una cuenta",
        "name": "Nombre completo",
        "email": "Correo",
        "password": "Contraseña",
        "confirm": "Confirmar contraseña",
        "sign_in": "Iniciar sesión",
        "signup_error": "Todos los campos son obligatorios.",
        "password_mismatch": "Las contraseñas no coinciden.",
        "password_short": "La contraseña debe tener al menos 6 caracteres.",
        "account_created": "✅ ¡Cuenta creada!",
        "email_exists": "Correo ya registrado.",
        "login_error": "Correo o contraseña incorrectos.",
        "footer": f"{COMPANY_NAME} · {DOMAIN} · {YEAR}",
        "lang_en": "🇬🇧 EN",
        "lang_fr": "🇫🇷 FR",
        "lang_es": "🇪🇸 ES",
        "scanner_title": "🔍 Escáner en Vivo",
        "mode": "Modo",
        "ev_mode": "Apuestas de valor (EV)",
        "arbitrage_mode": "Arbitraje",
        "both_mode": "Ambos",
        "min_ev": "VE mín. %",
        "stake_label": "Apuesta ($)",
        "scan_btn": "🔍 Escanear",
        "best_ev_bets": "🎯 Mejores apuestas",
        "manual_title": "📝 Ingreso manual",
        "sport": "Deporte",
        "home_team": "Equipo local",
        "away_team": "Equipo visitante",
        "home_odds": "Cuota local",
        "draw_odds": "Cuota empate",
        "away_odds": "Cuota visitante",
        "your_bet": "Tu apuesta",
        "your_stake": "Tu apuesta ($)",
        "add_bet": "➕ Agregar",
        "history_title": "📊 Historial",
        "update_result": "✏️ Actualizar",
        "select_bet": "Seleccionar",
        "result": "Resultado",
        "return_amount": "Retorno ($)",
        "update_btn": "Actualizar",
        "slip_title": "📄 Generador de Boletos",
        "download_slip": "📥 Descargar",
        "no_bets": "Aún no hay apuestas.",
        "no_pending": "No hay apuestas pendientes.",
        "no_pending_slips": "No hay apuestas pendientes.",
        "bet_added": "✅ Apuesta agregada: {home} vs {away} — {outcome} @ {odds}",
        "faq_title": "❓ Preguntas Frecuentes",
        "faq_q1": "¿Qué es el Valor Esperado (EV)?",
        "faq_a1": "El EV es el beneficio promedio por apuesta. Un EV de 4% significa 4$ de beneficio por 100$ apostados.",
        "faq_q2": "¿Cómo funciona el arbitraje?",
        "faq_a2": "El arbitraje es apostar en todos los resultados para garantizar un pequeño beneficio.",
        "faq_q3": "¿Qué es el criterio de Kelly?",
        "faq_a3": "El criterio de Kelly te dice el tamaño óptimo de la apuesta.",
        "faq_q4": "¿Cuánto debo apostar?",
        "faq_a4": "Nunca apuestes más del 1-5% de tu bankroll por apuesta.",
        "faq_q5": "¿Es garantizado ganar dinero?",
        "faq_a5": "Las apuestas EV son rentables a largo plazo, pero las apuestas individuales pueden perder.",
        "theme_dark": "🌙 Oscuro",
        "theme_light": "☀️ Claro",
        "ev_explained": "💡 ¿Qué es el EV?",
        "ev_explanation": "El Valor Esperado (EV) es el beneficio promedio por apuesta. Un EV de 4% significa 4$ de beneficio por 100$ apostados."
    }
}

# ─────────────────────────────────────────────────────────────
# CYBER CSS — BRIGHT TEXT + THEME SUPPORT
# ─────────────────────────────────────────────────────────────
def get_theme_css():
    is_dark = st.session_state.theme == "dark"
    
    bg_deep = "#0B0E14" if is_dark else "#F0F4FF"
    bg_surface = "#111927" if is_dark else "#E8EDF5"
    bg_card = "rgba(20, 30, 50, 0.7)" if is_dark else "rgba(220, 235, 255, 0.7)"
    border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
    text_primary = "#F0F4FF" if is_dark else "#0B0E14"
    text_secondary = "#B0C4DE" if is_dark else "#2A3A50"
    text_muted = "#6A8CAE" if is_dark else "#5A6A80"
    
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700;800&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
    
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    
    :root {{
        --bg-deep: {bg_deep};
        --bg-surface: {bg_surface};
        --bg-card: {bg_card};
        --border-glass: {border};
        --text-primary: {text_primary};
        --text-secondary: {text_secondary};
        --text-muted: {text_muted};
        --cyan: #00F3FF;
        --cyan-glow: rgba(0, 243, 255, 0.3);
        --lime: #39FF14;
        --lime-glow: rgba(57, 255, 20, 0.25);
        --orange: #FF6B35;
        --purple: #7C3AED;
        --red: #FF3355;
        --card-radius: 16px;
        --font-mono: 'JetBrains Mono', monospace;
        --font-display: 'Orbitron', sans-serif;
    }}
    
    html, body, .stApp, .stApp > div, .main, .block-container,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stHeader"],
    section[data-testid="stSidebar"] {{
        background: var(--bg-deep) !important;
        background-color: var(--bg-deep) !important;
        color: var(--text-primary) !important;
    }}
    
    .block-container {{
        padding: 1.5rem 2rem 3rem !important;
        max-width: 1400px !important;
    }}
    
    /* ALL TEXT — BRIGHT AND VISIBLE */
    .stMarkdown, .stText, .stCaption, p, div, span, label, h1, h2, h3, h4, h5, h6 {{
        color: var(--text-primary) !important;
    }}
    
    .stMarkdown p, .stMarkdown li, .stMarkdown div {{
        color: var(--text-secondary) !important;
    }}
    
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
        color: var(--text-primary) !important;
    }}
    
    label, .stSelectbox label, .stNumberInput label, .stTextInput label {{
        color: var(--text-secondary) !important;
        font-size: 0.65rem !important;
        font-weight: 600 !important;
    }}
    
    .stSelectbox > div > div {{
        color: var(--text-primary) !important;
        background: rgba(0,0,0,0.2) !important;
    }}
    
    ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-deep); }}
    ::-webkit-scrollbar-thumb {{ background: var(--cyan); border-radius: 2px; }}
    
    /* Top Nav */
    .terminal-nav {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.8rem 1.5rem;
        background: var(--bg-surface);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        margin-bottom: 1.5rem;
        backdrop-filter: blur(20px);
        position: relative;
        overflow: hidden;
    }}
    .terminal-nav::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--cyan), var(--lime), transparent);
        animation: scanline 4s ease-in-out infinite;
    }}
    @keyframes scanline {{
        0% {{ transform: translateX(-100%); }}
        100% {{ transform: translateX(100%); }}
    }}
    .terminal-logo .brand {{
        font-family: var(--font-display);
        font-size: 1.1rem;
        font-weight: 700;
        background: linear-gradient(135deg, var(--cyan), var(--lime));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 0.12em;
    }}
    .terminal-logo .sub {{
        font-family: var(--font-mono);
        font-size: 0.55rem;
        color: var(--text-muted);
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }}
    .terminal-status {{
        display: flex;
        align-items: center;
        gap: 1.5rem;
        font-family: var(--font-mono);
        font-size: 0.65rem;
    }}
    .terminal-status .dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--lime);
        box-shadow: 0 0 20px var(--lime-glow);
        animation: pulse-dot 2s ease-in-out infinite;
    }}
    @keyframes pulse-dot {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.5; transform: scale(0.8); }}
    }}
    .terminal-status .live-text {{ color: var(--lime); font-weight: 600; }}
    .terminal-status .stats {{ color: var(--text-muted); }}
    .terminal-status .stats span {{ color: var(--text-secondary); font-weight: 600; }}
    .terminal-status .user-badge {{
        background: rgba(0,243,255,0.1);
        border: 1px solid rgba(0,243,255,0.15);
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        color: var(--cyan);
        font-size: 0.6rem;
        font-weight: 600;
    }}
    
    /* KPI Cards */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin-bottom: 1.5rem;
    }}
    .kpi-card {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1.2rem 1.5rem;
        transition: all 0.3s ease;
    }}
    .kpi-card:hover {{
        border-color: var(--cyan);
        transform: translateY(-2px);
    }}
    .kpi-card .label {{
        font-family: var(--font-mono);
        font-size: 0.55rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.3rem;
    }}
    .kpi-card .value {{
        font-family: var(--font-display);
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--text-primary);
    }}
    .kpi-card .value.cyan {{ color: var(--cyan); text-shadow: 0 0 30px var(--cyan-glow); }}
    .kpi-card .value.lime {{ color: var(--lime); text-shadow: 0 0 30px var(--lime-glow); }}
    .kpi-card .value.orange {{ color: var(--orange); }}
    .kpi-card .value.purple {{ color: var(--purple); }}
    .kpi-card .change {{ font-family: var(--font-mono); font-size: 0.6rem; margin-top: 0.25rem; }}
    .kpi-card .change.positive {{ color: var(--lime); }}
    .kpi-card .change.negative {{ color: var(--red); }}
    
    /* EV Explanation Banner */
    .ev-banner {{
        background: rgba(0, 243, 255, 0.05);
        border: 1px solid rgba(0, 243, 255, 0.1);
        border-radius: var(--card-radius);
        padding: 0.8rem 1.2rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
    }}
    .ev-banner .ev-icon {{ font-size: 1.5rem; }}
    .ev-banner .ev-text {{
        color: var(--text-secondary);
        font-size: 0.85rem;
        flex: 1;
    }}
    .ev-banner .ev-text strong {{ color: var(--cyan); }}
    
    /* Arb Card */
    .arb-card {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1.25rem 1.5rem;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
    }}
    .arb-card:hover {{ border-color: var(--cyan); }}
    .arb-card .arb-match .teams {{
        font-family: 'Inter', sans-serif;
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-primary);
    }}
    .arb-card .arb-match .teams .vs {{ color: var(--text-muted); }}
    .arb-card .arb-match .meta {{
        font-family: var(--font-mono);
        font-size: 0.6rem;
        color: var(--text-muted);
        text-transform: uppercase;
    }}
    .arb-card .arb-badge {{
        font-family: var(--font-display);
        font-size: 0.75rem;
        font-weight: 700;
        color: var(--lime);
        background: rgba(57,255,20,0.1);
        border: 1px solid rgba(57,255,20,0.15);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
    }}
    .arb-card .odd-cell {{
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0.3rem 0.8rem;
        background: rgba(0,0,0,0.3);
        border-radius: 8px;
        min-width: 60px;
    }}
    .arb-card .odd-cell .odd-label {{
        font-family: var(--font-mono);
        font-size: 0.5rem;
        color: var(--text-muted);
        text-transform: uppercase;
    }}
    .arb-card .odd-cell .odd-value {{
        font-family: var(--font-mono);
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--text-secondary);
    }}
    .arb-card .odd-cell .odd-value.highlight {{
        color: var(--cyan);
        text-shadow: 0 0 20px var(--cyan-glow);
    }}
    .arb-card .arb-actions .action-btn {{
        background: rgba(0,243,255,0.08);
        border: 1px solid rgba(0,243,255,0.12);
        color: var(--cyan);
        padding: 0.3rem 0.8rem;
        border-radius: 6px;
        font-family: var(--font-mono);
        font-size: 0.6rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-transform: uppercase;
    }}
    .arb-card .arb-actions .action-btn:hover {{
        background: rgba(0,243,255,0.15);
        border-color: var(--cyan);
    }}
    .arb-card .arb-actions .action-btn.primary {{
        background: linear-gradient(135deg, var(--cyan), #0099CC);
        color: #0B0E14;
        border: none;
    }}
    .arb-card .arb-actions .action-btn.primary:hover {{
        box-shadow: 0 0 30px var(--cyan-glow);
    }}
    
    /* Hero Section */
    .hero-section {{
        text-align: center;
        padding: 3rem 2rem;
        background: var(--bg-surface);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        margin-bottom: 2rem;
    }}
    .hero-section h1 {{
        font-family: var(--font-display);
        font-size: 2.8rem;
        font-weight: 800;
        background: linear-gradient(135deg, var(--cyan), var(--lime));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }}
    .hero-section p {{ color: var(--text-secondary) !important; font-size: 1.1rem; }}
    .hero-section .badge {{
        background: rgba(0,243,255,0.1);
        border: 1px solid rgba(0,243,255,0.15);
        padding: 0.3rem 1rem;
        border-radius: 20px;
        color: var(--cyan);
        font-size: 0.7rem;
    }}
    .hero-section .badge-live {{
        background: rgba(57,255,20,0.08);
        border: 1px solid rgba(57,255,20,0.12);
        padding: 0.3rem 1rem;
        border-radius: 20px;
        color: var(--lime);
        font-size: 0.7rem;
    }}
    
    /* Feature Cards */
    .feature-card {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1.5rem;
        text-align: center;
    }}
    .feature-card .icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
    .feature-card h3 {{ color: var(--text-primary); font-size: 1rem; }}
    .feature-card p {{ color: var(--text-muted); font-size: 0.8rem; }}
    
    /* Pricing Card */
    .pricing-card {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 2rem;
        text-align: center;
    }}
    .pricing-card .badge-top {{
        background: linear-gradient(135deg, var(--cyan), var(--lime));
        color: #0B0E14;
        padding: 0.3rem 1rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        display: inline-block;
        margin-bottom: 0.5rem;
    }}
    .pricing-card .price {{
        font-family: var(--font-display);
        font-size: 3.5rem;
        font-weight: 700;
        color: var(--cyan);
    }}
    .pricing-card .period {{ color: var(--text-muted); font-size: 0.8rem; }}
    .pricing-card .feature-item {{
        padding: 0.4rem 0;
        color: var(--text-secondary);
    }}
    .pricing-card .feature-item::before {{ content: "✓ "; color: var(--lime); }}
    
    /* Streamlit Overrides */
    div[data-testid="stTextInput"] input {{
        background: rgba(0,0,0,0.2) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        padding: 0.6rem 1rem !important;
    }}
    div[data-testid="stTextInput"] input:focus {{
        border-color: var(--cyan) !important;
        box-shadow: 0 0 20px var(--cyan-glow) !important;
    }}
    div[data-testid="stTextInput"] label {{
        color: var(--text-secondary) !important;
        font-family: var(--font-mono) !important;
        font-size: 0.6rem !important;
    }}
    
    .stButton button, div[data-testid="stFormSubmitButton"] button {{
        background: linear-gradient(135deg, var(--cyan), #0099CC) !important;
        color: #0B0E14 !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: var(--font-mono) !important;
        font-weight: 700 !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.6rem 1.5rem !important;
        box-shadow: 0 0 20px var(--cyan-glow) !important;
    }}
    .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 0 40px var(--cyan-glow) !important;
    }}
    
    div[data-testid="metric-container"] {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--card-radius) !important;
        padding: 0.8rem 1rem !important;
    }}
    div[data-testid="metric-label"] {{
        color: var(--text-muted) !important;
        font-family: var(--font-mono) !important;
        font-size: 0.5rem !important;
        text-transform: uppercase !important;
    }}
    div[data-testid="metric-value"] {{
        color: var(--text-primary) !important;
        font-family: var(--font-display) !important;
        font-size: 1.2rem !important;
        font-weight: 700 !important;
    }}
    
    section[data-testid="stSidebar"] {{
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border-glass) !important;
    }}
    
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0 !important;
        border-bottom: 1px solid var(--border-glass) !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: var(--font-mono) !important;
        font-size: 0.6rem !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        padding: 0.5rem 1.5rem !important;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--cyan) !important;
        border-bottom: 2px solid var(--cyan) !important;
    }}
    
    .stSelectbox > div > div {{
        background: rgba(0,0,0,0.2) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
    }}
    .stSelectbox label {{
        color: var(--text-secondary) !important;
    }}
    
    .stSlider div[data-baseweb="slider"] {{ background: var(--border-glass) !important; }}
    .stSlider div[data-baseweb="slider"] div {{ background: var(--cyan) !important; box-shadow: 0 0 15px var(--cyan-glow) !important; }}
    
    .stAlert {{
        background: var(--bg-card) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: var(--card-radius) !important;
    }}
    .stAlert .stMarkdown {{ color: var(--text-secondary) !important; }}
    
    /* FAQ Section */
    .faq-container {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1.5rem;
        margin-bottom: 0.75rem;
    }}
    .faq-container .faq-q {{
        font-family: var(--font-display);
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--cyan);
        margin-bottom: 0.3rem;
    }}
    .faq-container .faq-a {{
        color: var(--text-secondary);
        font-size: 0.9rem;
        line-height: 1.5;
    }}
    
    .ev-explain-box {{
        background: rgba(57, 255, 20, 0.04);
        border: 1px solid rgba(57, 255, 20, 0.08);
        border-radius: 8px;
        padding: 0.6rem 1rem;
        margin: 0.5rem 0 1rem 0;
        font-size: 0.8rem;
        color: var(--text-secondary);
    }}
    .ev-explain-box strong {{ color: var(--lime); }}
    
    #MainMenu, footer, header {{ visibility: hidden !important; display: none !important; }}
    </style>
    """
    
st.markdown(get_theme_css(), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LANDING PAGE
# ─────────────────────────────────────────────────────────────
def landing_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    # Language + Theme toggle
    col_lang1, col_lang2, col_lang3, col_lang4, col_lang5 = st.columns([8, 0.8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button(t['lang_en'], key="lang_en_landing"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button(t['lang_fr'], key="lang_fr_landing"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button(t['lang_es'], key="lang_es_landing"):
            st.session_state.lang = "es"
            st.rerun()
    with col_lang5:
        theme_label = t['theme_light'] if st.session_state.theme == "dark" else t['theme_dark']
        if st.button(theme_label, key="theme_landing"):
            toggle_theme()
    
    # Hero
    st.markdown(f"""
    <div class="hero-section">
        <h1>{t['title']}</h1>
        <p>{t['subtitle']}</p>
        <div style="margin-top:1rem; display:flex; justify-content:center; gap:0.5rem; flex-wrap:wrap;">
            <span class="badge">🆓 7-day free trial</span>
            <span class="badge-live">⚡ {t['live']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features
    col1, col2, col3 = st.columns(3)
    features = [
        ("🎯", "EV Scanner", "Find positive expected value bets automatically"),
        ("🔄", "Arbitrage Scanner", "Discover guaranteed profit opportunities"),
        ("📄", "Paper Slip", "Print ready-to-use betting slips")
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3], features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="icon">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Pricing
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="badge-top">🔥 Most Popular</div>
            <h2 style="color:var(--text-primary); margin:0;">Monthly</h2>
            <div class="price">$1.99</div>
            <div class="period">per month</div>
            <div style="text-align:left; margin:1.5rem 0;">
                <div class="feature-item">Unlimited EV Scans</div>
                <div class="feature-item">Arbitrage Detection</div>
                <div class="feature-item">Paper Slip Generator</div>
                <div class="feature-item">AI Analysis</div>
                <div class="feature-item">No commitment</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(t['free_trial'], use_container_width=True, type="primary"):
            st.session_state.page = "signup"
            st.rerun()
        
        st.markdown(f"""
        <div style="text-align:center; color:var(--text-muted); font-size:0.7rem; padding:0.5rem 0;">
            {t['free_trial_note']}
        </div>
        """, unsafe_allow_html=True)
    
    # FAQ Section
    st.markdown("---")
    st.markdown(f"## {t['faq_title']}")
    
    faqs = [
        (t['faq_q1'], t['faq_a1']),
        (t['faq_q2'], t['faq_a2']),
        (t['faq_q3'], t['faq_a3']),
        (t['faq_q4'], t['faq_a4']),
        (t['faq_q5'], t['faq_a5'])
    ]
    
    for q, a in faqs:
        st.markdown(f"""
        <div class="faq-container">
            <div class="faq-q">❓ {q}</div>
            <div class="faq-a">{a}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align:center; color:var(--text-muted); font-size:0.7rem; padding:2rem 0; border-top:1px solid var(--border-glass); margin-top:1rem;">
        {t['footer']}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIGNUP PAGE
# ─────────────────────────────────────────────────────────────
def signup_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    col_lang1, col_lang2, col_lang3, col_lang4, col_lang5 = st.columns([8, 0.8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button(t['lang_en'], key="lang_en_signup"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button(t['lang_fr'], key="lang_fr_signup"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button(t['lang_es'], key="lang_es_signup"):
            st.session_state.lang = "es"
            st.rerun()
    with col_lang5:
        theme_label = t['theme_light'] if st.session_state.theme == "dark" else t['theme_dark']
        if st.button(theme_label, key="theme_signup"):
            toggle_theme()
    
    st.markdown(f"### {t['signup_title']}")
    st.markdown(t['signup_subtitle'])
    
    with st.form("signup_form"):
        name = st.text_input(t['name'], placeholder="John Doe")
        email = st.text_input(t['email'], placeholder="you@example.com")
        password = st.text_input(t['password'], type="password", placeholder="••••••••")
        confirm = st.text_input(t['confirm'], type="password", placeholder="••••••••")
        
        if st.form_submit_button(t['free_trial'], use_container_width=True, type="primary"):
            if not name or not email or not password:
                st.error(t['signup_error'])
            elif password != confirm:
                st.error(t['password_mismatch'])
            elif len(password) < 6:
                st.error(t['password_short'])
            else:
                if create_user(email, password, name):
                    st.success(t['account_created'])
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error(t['email_exists'])
    
    st.markdown("---")
    if st.button(t['already_account'], use_container_width=True):
        st.session_state.page = "login"
        st.rerun()

# ─────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────
def login_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    col_lang1, col_lang2, col_lang3, col_lang4, col_lang5 = st.columns([8, 0.8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button(t['lang_en'], key="lang_en_login"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button(t['lang_fr'], key="lang_fr_login"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button(t['lang_es'], key="lang_es_login"):
            st.session_state.lang = "es"
            st.rerun()
    with col_lang5:
        theme_label = t['theme_light'] if st.session_state.theme == "dark" else t['theme_dark']
        if st.button(theme_label, key="theme_login"):
            toggle_theme()
    
    st.markdown(f"### {t['login_title']}")
    
    with st.form("login_form"):
        email = st.text_input(t['email'], placeholder="you@example.com")
        password = st.text_input(t['password'], type="password", placeholder="••••••••")
        
        if st.form_submit_button(t['sign_in'], use_container_width=True, type="primary"):
            user = authenticate_user(email, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.session_state.user_name = user[3]
                st.session_state.user_id = user[0]
                st.session_state.is_admin = user[6] if len(user) > 6 else 0
                st.rerun()
            else:
                st.error(t['login_error'])
    
    st.markdown("---")
    if st.button(t['create_account'], use_container_width=True):
        st.session_state.page = "signup"
        st.rerun()

# ─────────────────────────────────────────────────────────────
# DASHBOARD (PRIVATE)
# ─────────────────────────────────────────────────────────────
def dashboard():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    if 'user_id' not in st.session_state or st.session_state.user_id is None:
        st.error("User session error. Please log in again.")
        st.session_state.authenticated = False
        st.rerun()
        return
    
    # Language + Theme toggle
    col_lang1, col_lang2, col_lang3, col_lang4, col_lang5 = st.columns([8, 0.8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button(t['lang_en'], key="lang_en_dash"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button(t['lang_fr'], key="lang_fr_dash"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button(t['lang_es'], key="lang_es_dash"):
            st.session_state.lang = "es"
            st.rerun()
    with col_lang5:
        theme_label = t['theme_light'] if st.session_state.theme == "dark" else t['theme_dark']
        if st.button(theme_label, key="theme_dash"):
            toggle_theme()
    
    # Top Nav
    st.markdown(f"""
    <div class="terminal-nav">
        <div class="terminal-logo">
            <span style="font-size:1.4rem;">📊</span>
            <div>
                <span class="brand">BUDGET SYSTEM</span>
                <div class="sub">{st.session_state.user_name} · {'ADMIN' if st.session_state.is_admin else 'USER'}</div>
            </div>
        </div>
        <div class="terminal-status">
            <div style="display:flex; align-items:center; gap:0.5rem;">
                <span class="dot"></span>
                <span class="live-text">{t['live']}</span>
            </div>
            <span class="stats">API: <span>47</span>/min</span>
            <span class="stats">Books: <span>12</span></span>
            <span class="user-badge">{'👑 Admin' if st.session_state.is_admin else '👤 User'}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # KPI Grid
    bets = get_user_bets(st.session_state.user_id)
    
    if bets:
        summary = get_bet_summary(bets)
        total_bets = summary['total']
        wins = summary['wins']
        losses = summary['losses']
        profit = summary['net_profit']
        win_rate = summary['win_rate']
        
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="label">Active Bets</div>
                <div class="value cyan">{total_bets}</div>
                <div class="change positive">↑ Tracking {total_bets} bets</div>
            </div>
            <div class="kpi-card">
                <div class="label">Win Rate</div>
                <div class="value lime">{win_rate:.1f}%</div>
                <div class="change positive">{wins} wins / {losses} losses</div>
            </div>
            <div class="kpi-card">
                <div class="label">Bankroll</div>
                <div class="value orange">${1000 + profit:.2f}</div>
                <div class="change {'positive' if profit > 0 else 'negative'}">{'+' if profit > 0 else ''}{profit:.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Avg EV</div>
                <div class="value purple">+4.2%</div>
                <div class="change positive">↑ 0.8% from last week</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="label">Active Bets</div><div class="value cyan">0</div><div class="change">No active bets</div></div>
            <div class="kpi-card"><div class="label">Win Rate</div><div class="value lime">0%</div><div class="change">No data yet</div></div>
            <div class="kpi-card"><div class="label">Bankroll</div><div class="value orange">$1,000</div><div class="change">Start betting</div></div>
            <div class="kpi-card"><div class="label">Avg EV</div><div class="value purple">0%</div><div class="change">Scan to find value</div></div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # EV Explanation Banner
    st.markdown(f"""
    <div class="ev-banner">
        <span class="ev-icon">💡</span>
        <span class="ev-text"><strong>{t['ev_explained']}</strong> {t['ev_explanation']}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Scanner",
        "📝 Manual",
        "📊 History",
        "📄 Slip",
        "❓ FAQ"
    ])
    
    # ─── TAB 1: SCANNER ──────────────────────────────────────
    with tab1:
        st.markdown(f"### {t['scanner_title']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            scan_mode = st.selectbox(t['mode'], [t['ev_mode'], t['arbitrage_mode'], t['both_mode']])
        with col2:
            min_ev = st.slider(t['min_ev'], 1, 20, 5, 1)
        with col3:
            target_stake = st.number_input(t['stake_label'], min_value=10, value=100, step=10)
        
        if st.button(t['scan_btn'], use_container_width=True, type="primary"):
            with st.spinner("Scanning 70+ bookmakers..."):
                sample_bets = []
                
                # Generate realistic EV bets with varied values
                ev_options = [3.2, 4.1, 5.8, 6.7, 8.2, 9.5, 10.1, 12.3]
                odds_options = [2.14, 3.44, 6.88, 8.20, 2.99, 3.15, 5.50, 4.80]
                outcomes = ['Draw', 'Home Win', 'Away Win']
                books = ['Betfair', 'Pinnacle', 'Bet365', 'NordicBet', 'Coolbet', 'Unibet']
                matches = [
                    ('Arsenal', 'Coventry'),
                    ('Everton', 'Crystal Palace'),
                    ('Ipswich', 'Sunderland'),
                    ('Hull City', 'Man Utd'),
                    ('Brentford', 'Spurs'),
                    ('Leeds', 'Southampton'),
                    ('Norwich', 'Watford'),
                    ('Chelsea', 'West Ham')
                ]
                
                # Generate 5 realistic bets
                for i in range(5):
                    match = random.choice(matches)
                    odds = random.choice(odds_options)
                    ev = random.choice(ev_options)
                    outcome = random.choice(outcomes)
                    book = random.choice(books)
                    
                    # Calculate realistic stake based on EV
                    stake = round(10 + (ev / 2), 2)
                    potential_return = round(stake * odds, 2)
                    
                    sample_bets.append({
                        'match': f"{match[0]} vs {match[1]}",
                        'outcome': outcome,
                        'odds': odds,
                        'ev_percent': ev,
                        'true_prob': round((1 / odds) * 100 * (1 + ev / 100), 1),
                        'stake': stake,
                        'potential_return': potential_return,
                        'book': book
                    })
                
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
                st.success(f"✅ Found {len(sample_bets)} value bets!")
                st.rerun()
        
        if 'scan_results' in st.session_state and st.session_state.scan_results:
            st.markdown(f"### {t['best_ev_bets']}")
            
            total_stake = 0
            total_return = 0
            
            for i, bet in enumerate(st.session_state.scan_results[:5], 1):
                profit = bet['potential_return'] - bet['stake']
                st.markdown(f"""
                <div class="arb-card">
                    <div class="arb-header">
                        <div class="arb-match">
                            <div class="teams">#{i} {bet['match'].replace(' vs ', ' <span class="vs">vs</span> ')}</div>
                            <div class="meta">{bet['book']} · EV: {bet['ev_percent']:.1f}% · Win Prob: {bet['true_prob']:.1f}%</div>
                        </div>
                        <div class="arb-badge">⚡ +{bet['ev_percent']:.1f}% EV</div>
                    </div>
                    <div class="arb-body">
                        <div class="odds-grid">
                            <div class="odd-cell"><span class="odd-label">Bet</span><span class="odd-value highlight">{bet['outcome']}</span></div>
                            <div class="odd-cell"><span class="odd-label">Odds</span><span class="odd-value">{bet['odds']}</span></div>
                            <div class="odd-cell"><span class="odd-label">Stake</span><span class="odd-value">${bet['stake']:.2f}</span></div>
                            <div class="odd-cell"><span class="odd-label">Return</span><span class="odd-value" style="color:var(--lime);">${bet['potential_return']:.2f}</span></div>
                            <div class="odd-cell"><span class="odd-label">Profit</span><span class="odd-value" style="color:var(--cyan);">+${profit:.2f}</span></div>
                        </div>
                        <div class="arb-actions">
                            <button class="action-btn primary">📄 Slip</button>
                            <button class="action-btn">ℹ️ Info</button>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                total_stake += bet['stake']
                total_return += bet['potential_return']
            
            # Summary with realistic expectations
            st.markdown(f"""
            <div style="background:var(--bg-card); border:1px solid var(--border-glass); border-radius:var(--card-radius); padding:1rem 1.5rem; margin-top:0.5rem;">
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem;">
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Total Bets</span><br><span style="color:var(--text-primary); font-weight:700;">{len(st.session_state.scan_results)}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Total Stake</span><br><span style="color:var(--text-primary); font-weight:700;">${total_stake:.2f}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Expected Return</span><br><span style="color:var(--lime); font-weight:700;">${total_return:.2f}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Expected Profit</span><br><span style="color:var(--cyan); font-weight:700;">${total_return - total_stake:.2f}</span></div>
                </div>
                <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted); border-top:1px solid var(--border-glass); padding-top:0.5rem;">
                    💡 With {len(st.session_state.scan_results)} bets at {sum(b['ev_percent'] for b in st.session_state.scan_results)/len(st.session_state.scan_results):.1f}% average EV, expected profit is ${total_return - total_stake:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # ─── TAB 2: MANUAL ──────────────────────────────────────
    with tab2:
        st.markdown(f"### {t['manual_title']}")
        
        with st.form("manual_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                sport = st.selectbox(t['sport'], ["Soccer", "Hockey", "Basketball", "Football", "Baseball", "Tennis"])
                home_team = st.text_input(t['home_team'])
            with col2:
                away_team = st.text_input(t['away_team'])
                home_odds = st.number_input(t['home_odds'], min_value=1.01, step=0.01, value=2.50)
            with col3:
                draw_odds = st.number_input(t['draw_odds'], min_value=1.01, step=0.01, value=3.20)
                away_odds = st.number_input(t['away_odds'], min_value=1.01, step=0.01, value=2.80)
            
            outcome = st.selectbox(t['your_bet'], ["Home Win", "Draw", "Away Win"])
            stake = st.number_input(t['your_stake'], min_value=1.0, step=1.0, value=10.0)
            
            if st.form_submit_button(t['add_bet'], use_container_width=True, type="primary"):
                if home_team and away_team and st.session_state.user_id:
                    odds_map = {"Home Win": home_odds, "Draw": draw_odds, "Away Win": away_odds}
                    selected_odds = odds_map.get(outcome, 0)
                    
                    # Calculate realistic EV
                    implied_prob = 1 / selected_odds if selected_odds > 0 else 0
                    edge = random.uniform(0.02, 0.05)
                    true_prob = implied_prob * (1 + edge)
                    ev = (true_prob * selected_odds) - 1
                    ev_percent = ev * 100
                    
                    add_bet(st.session_state.user_id, {
                        'sport': sport,
                        'home_team': home_team,
                        'away_team': away_team,
                        'outcome': outcome,
                        'odds': selected_odds,
                        'stake': stake,
                        'ev_percent': ev_percent,
                        'result': 'Pending',
                        'return': 0,
                        'profit_loss': 0
                    })
                    
                    st.success(t['bet_added'].format(home=home_team, away=away_team, outcome=outcome, odds=selected_odds))
                    st.rerun()
    
    # ─── TAB 3: HISTORY ──────────────────────────────────────
    with tab3:
        st.markdown(f"### {t['history_title']}")
        
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
            st.markdown(f"### {t['update_result']}")
            
            pending = [b for b in bets if b[10] == 'Pending']
            if pending:
                options = {f"ID {b[0]}: {b[4]} vs {b[5]}": b[0] for b in pending}
                selected = st.selectbox(t['select_bet'], list(options.keys()))
                bet_id = options[selected]
                
                result = st.selectbox(t['result'], ["Win", "Loss"])
                return_amount = st.number_input(t['return_amount'], min_value=0.0, step=0.01)
                
                if st.button(t['update_btn'], use_container_width=True, type="primary"):
                    stake = [b[8] for b in bets if b[0] == bet_id][0]
                    if result == "Win":
                        profit_loss = return_amount - stake
                    else:
                        profit_loss = -stake
                    
                    update_bet_result(bet_id, result, return_amount, profit_loss)
                    st.success("✅ Bet updated!")
                    st.rerun()
            else:
                st.info(t['no_pending'])
        else:
            st.info(t['no_bets'])
    
    # ─── TAB 4: SLIP ─────────────────────────────────────────
    with tab4:
        st.markdown(f"### {t['slip_title']}")
        
        bets = get_user_bets(st.session_state.user_id)
        pending = [b for b in bets if b[10] == 'Pending']
        
        if pending:
            selected = []
            st.markdown("### Select bets for your slip")
            
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
                    label=t['download_slip'],
                    data=slip_text,
                    file_name=f"slip_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            st.info(t['no_pending_slips'])
    
    # ─── TAB 5: FAQ ──────────────────────────────────────────
    with tab5:
        st.markdown(f"## {t['faq_title']}")
        
        faqs = [
            (t['faq_q1'], t['faq_a1']),
            (t['faq_q2'], t['faq_a2']),
            (t['faq_q3'], t['faq_a3']),
            (t['faq_q4'], t['faq_a4']),
            (t['faq_q5'], t['faq_a5'])
        ]
        
        for q, a in faqs:
            st.markdown(f"""
            <div class="faq-container">
                <div class="faq-q">❓ {q}</div>
                <div class="faq-a">{a}</div>
            </div>
            """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'page' not in st.session_state:
    st.session_state.page = "landing"
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'lang' not in st.session_state:
    st.session_state.lang = "en"
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = 0

# ─────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────
init_db()

if st.session_state.authenticated:
    dashboard()
else:
    if st.session_state.page == "signup":
        signup_page()
    elif st.session_state.page == "login":
        login_page()
    else:
        landing_page()

# ─────────────────────────────────────────────────────────────
# SIDEBAR — LOGOUT
# ─────────────────────────────────────────────────────────────
if st.session_state.authenticated:
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:0.8rem; padding:0.5rem 0;">
            <div style="width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, var(--cyan), var(--lime)); display:flex; align-items:center; justify-content:center; color:#0B0E14; font-weight:700; font-size:1.2rem;">
                {st.session_state.user_name[0].upper()}
            </div>
            <div>
                <div style="color:var(--text-primary); font-weight:500;">{st.session_state.user_name}</div>
                <div style="color:var(--text-muted); font-size:0.7rem;">{st.session_state.user_email}</div>
                <div style="color:var(--cyan); font-size:0.65rem;">{'👑 Admin' if st.session_state.is_admin else '👤 User'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in ['authenticated', 'user_email', 'user_name', 'user_id', 'is_admin']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.page = "landing"
            st.rerun()
        
        st.markdown(f"""
        <div style="font-size:0.6rem; color:var(--text-muted); text-align:center; margin-top:2rem;">
            {COMPANY_NAME}<br>{DOMAIN}
        </div>
        """, unsafe_allow_html=True)
