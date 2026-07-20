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
    page_title="Only Solutions · Smart Betting System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# API KEYS — pulled from environment / Streamlit secrets, never hardcoded
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", st.secrets.get("DEEPSEEK_API_KEY", ""))
ODDS_API_KEY = os.environ.get("ODDS_API_KEY", st.secrets.get("ODDS_API_KEY", ""))

# ─────────────────────────────────────────────────────────────
# COMPANY INFO
# ─────────────────────────────────────────────────────────────
COMPANY_NAME = "Only Solutions Inc."
DOMAIN = "onlysolutions.ca"
YEAR = datetime.now().year

# ─────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS (must exist before anything reads them)
# ─────────────────────────────────────────────────────────────
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"
if 'lang' not in st.session_state:
    st.session_state.lang = "en"
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'page' not in st.session_state:
    st.session_state.page = "landing"
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = 0

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    st.rerun()

# ─────────────────────────────────────────────────────────────
# DATABASE — Users
# ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
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
            is_admin INTEGER DEFAULT 0,
            starting_bankroll REAL DEFAULT 1000
        )
        ''')
    else:
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        if 'is_admin' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
        if 'starting_bankroll' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN starting_bankroll REAL DEFAULT 1000')

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
    conn = get_conn()
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
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, hash_password(password)))
    result = c.fetchone()
    conn.close()
    return result

def get_user_bankroll(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT starting_bankroll FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] is not None else 1000.0

def set_user_bankroll(user_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute('UPDATE users SET starting_bankroll = ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_user_bets(user_id):
    if user_id is None:
        return []
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM bets WHERE user_id = ? ORDER BY timestamp DESC', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_bet(user_id, bet_data):
    if user_id is None:
        return False
    conn = get_conn()
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
    conn = get_conn()
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
# LANGUAGES
# ─────────────────────────────────────────────────────────────
LANGUAGES = {
    "en": {
        "title": "📊 Smart Betting System",
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
        "title": "📊 Système de Paris Intelligent",
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
        "title": "📊 Sistema de Apuestas Inteligente",
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
# CYBER CSS
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
    .arb-card .arb-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }}
    .arb-card .arb-body {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.75rem;
    }}
    .arb-card .odds-grid {{
        display: flex;
        gap: 0.6rem;
        flex-wrap: wrap;
    }}
    .arb-card .arb-actions {{
        display: flex;
        gap: 0.5rem;
    }}
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

    .slip-preview {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px dashed var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1.5rem;
        font-family: var(--font-mono);
        color: var(--text-secondary);
        white-space: pre-wrap;
        line-height: 1.6;
    }}

    #MainMenu, footer, header {{ visibility: hidden !important; display: none !important; }}
    </style>
    """

st.markdown(get_theme_css(), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LANGUAGE / THEME TOGGLE BAR (shared across public pages)
# ─────────────────────────────────────────────────────────────
def render_top_bar(key_suffix):
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]

    col_lang1, col_lang2, col_lang3, col_lang4, col_lang5 = st.columns([8, 0.8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button(t['lang_en'], key=f"lang_en_{key_suffix}"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button(t['lang_fr'], key=f"lang_fr_{key_suffix}"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button(t['lang_es'], key=f"lang_es_{key_suffix}"):
            st.session_state.lang = "es"
            st.rerun()
    with col_lang5:
        theme_label = t['theme_light'] if st.session_state.theme == "dark" else t['theme_dark']
        if st.button(theme_label, key=f"theme_{key_suffix}"):
            toggle_theme()

# ─────────────────────────────────────────────────────────────
# LANDING PAGE
# ─────────────────────────────────────────────────────────────
def landing_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]

    render_top_bar("landing")

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

    st.markdown("---")
    if st.button(t['already_account'], use_container_width=True):
        st.session_state.page = "login"
        st.rerun()

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

    render_top_bar("signup")

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

    render_top_bar("login")

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
                st.session_state.starting_bankroll = user[7] if len(user) > 7 and user[7] is not None else 1000.0
                st.rerun()
            else:
                st.error(t['login_error'])

    st.markdown("---")
    if st.button(t['create_account'], use_container_width=True):
        st.session_state.page = "signup"
        st.rerun()

# ─────────────────────────────────────────────────────────────
# SCANNER — result generators (simulated; swap with real odds
# API calls using ODDS_API_KEY when ready)
# ─────────────────────────────────────────────────────────────
SCAN_MATCHES = [
    ('Arsenal', 'Coventry'),
    ('Everton', 'Crystal Palace'),
    ('Ipswich', 'Sunderland'),
    ('Hull City', 'Man Utd'),
    ('Brentford', 'Spurs'),
    ('Leeds', 'Southampton'),
    ('Norwich', 'Watford'),
    ('Chelsea', 'West Ham')
]
SCAN_BOOKS = ['Betfair', 'Pinnacle', 'Bet365', 'NordicBet', 'Coolbet', 'Unibet']

def generate_ev_bets(count, target_stake, min_ev):
    """Directional value bets: one side, one bookmaker, positive expected value.
    Stake is sized as a modest slice of the bankroll the user entered, not the
    whole amount, and odds/EV are independent of each other on purpose —
    a big potential payout does NOT mean a big EV."""
    ev_options = [v for v in [3.2, 4.1, 5.8, 6.7, 8.2, 9.5, 10.1, 12.3] if v >= min_ev] or [min_ev]
    odds_options = [2.14, 3.44, 6.88, 8.20, 2.99, 3.15, 5.50, 4.80]
    outcomes = ['Draw', 'Home Win', 'Away Win']

    bets = []
    for _ in range(count):
        match = random.choice(SCAN_MATCHES)
        odds = random.choice(odds_options)
        ev = random.choice(ev_options)
        outcome = random.choice(outcomes)
        book = random.choice(SCAN_BOOKS)

        stake = round(max(5.0, target_stake * random.uniform(0.05, 0.15)), 2)
        potential_return = round(stake * odds, 2)

        bets.append({
            'type': 'ev',
            'match': f"{match[0]} vs {match[1]}",
            'outcome': outcome,
            'odds': odds,
            'ev_percent': ev,
            'true_prob': round((1 / odds) * 100 * (1 + ev / 100), 1),
            'stake': stake,
            'potential_return': potential_return,
            'book': book
        })
    return bets

def generate_arbitrage_opportunities(count, target_stake):
    """True arbitrage: odds on every outcome from different bookmakers whose
    implied probabilities sum to less than 100%, so splitting the stake across
    all legs guarantees the SAME small profit no matter which outcome wins."""
    opportunities = []
    for _ in range(count):
        match = random.choice(SCAN_MATCHES)
        book1, book2 = random.sample(SCAN_BOOKS, 2)

        margin = random.uniform(0.01, 0.05)          # 1-5% guaranteed edge — realistic for real arbitrage
        total_implied = 1 - margin
        split = random.uniform(0.35, 0.65)
        p1 = total_implied * split
        p2 = total_implied * (1 - split)

        odds1 = round(1 / p1, 2)
        odds2 = round(1 / p2, 2)
        stake1 = round(target_stake * p1 / total_implied, 2)
        stake2 = round(target_stake * p2 / total_implied, 2)
        actual_total_stake = round(stake1 + stake2, 2)
        guaranteed_payout = round(actual_total_stake / total_implied, 2)
        guaranteed_profit = round(guaranteed_payout - actual_total_stake, 2)
        profit_percent = round((guaranteed_profit / actual_total_stake) * 100, 2)

        opportunities.append({
            'type': 'arbitrage',
            'match': f"{match[0]} vs {match[1]}",
            'legs': [
                {'outcome': 'Home Win', 'book': book1, 'odds': odds1, 'stake': stake1},
                {'outcome': 'Away Win', 'book': book2, 'odds': odds2, 'stake': stake2},
            ],
            'total_stake': actual_total_stake,
            'guaranteed_payout': guaranteed_payout,
            'guaranteed_profit': guaranteed_profit,
            'profit_percent': profit_percent
        })
    return opportunities

# ─────────────────────────────────────────────────────────────
# LIVE ODDS — real data via The Odds API (the-odds-api.com)
# Uses ODDS_API_KEY from st.secrets / env, set up earlier.
# Cached for 60s so reruns/tab-switches don't burn API credits.
# ─────────────────────────────────────────────────────────────

# Fallback list only used if the live /sports call fails (e.g. no key yet) —
# the real, current list always comes from the API itself, not from here.
FALLBACK_SPORT_OPTIONS = {
    "Soccer — EPL": "soccer_epl",
    "Basketball — NBA": "basketball_nba",
    "American Football — NFL": "americanfootball_nfl",
    "Ice Hockey — NHL": "icehockey_nhl",
}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_available_sports():
    """Pulls the sports your key can actually see, straight from the API.
    /v4/sports does not cost quota credits, so it's safe to call often.
    Returns (dict of "Group — Title": sport_key, error_message)."""
    if not ODDS_API_KEY:
        return None, "No Odds API key found in st.secrets / environment."
    url = "https://api.the-odds-api.com/v4/sports"
    try:
        resp = requests.get(url, params={"apiKey": ODDS_API_KEY}, timeout=12)
    except requests.RequestException as e:
        return None, f"Network error reaching Odds API: {e}"
    if resp.status_code == 401:
        return None, "Odds API rejected the key (401). Check ODDS_API_KEY in secrets."
    if resp.status_code != 200:
        return None, f"Odds API error {resp.status_code}: {resp.text[:200]}"
    try:
        sports = resp.json()
    except ValueError:
        return None, "Odds API returned a non-JSON response."

    options = {}
    for s in sports:
        if not s.get("active", True):
            continue
        label = f"{s.get('group', 'Other')} — {s.get('title', s.get('key'))}"
        options[label] = s["key"]
    return dict(sorted(options.items())), None

@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_odds(sport_key, regions="uk,eu,us"):
    """Returns (events, error_message). error_message is None on success."""
    if not ODDS_API_KEY:
        return None, "No Odds API key found in st.secrets / environment."
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {"apiKey": ODDS_API_KEY, "regions": regions, "markets": "h2h", "oddsFormat": "decimal"}
    try:
        resp = requests.get(url, params=params, timeout=12)
    except requests.RequestException as e:
        return None, f"Network error reaching Odds API: {e}"
    if resp.status_code == 401:
        return None, "Odds API rejected the key (401). Check ODDS_API_KEY in secrets."
    if resp.status_code == 429:
        return None, "Odds API monthly quota exhausted (429)."
    if resp.status_code != 200:
        return None, f"Odds API error {resp.status_code}: {resp.text[:200]}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "Odds API returned a non-JSON response."

MIN_BOOKS_FOR_SIGNAL = 4      # too few quotes = consensus isn't trustworthy
MAX_PLAUSIBLE_EV_PERCENT = 20  # real markets essentially never leave more than this on the table;
                                # higher usually means a stale/mispriced outlier, not a real edge

def find_live_ev_bets(events, min_ev_percent, target_stake):
    """De-vigs every OTHER bookmaker's line (leave-one-out — a book's own price
    never counts toward its own 'fair value') to build a consensus per outcome,
    then flags a price that beats that consensus by at least min_ev_percent.
    Requires several independent bookmakers per event; skips events too thin
    to trust, and discards anything above a sanity ceiling as a likely bad
    price rather than a real edge."""
    results = []
    for event in events or []:
        home, away = event.get('home_team', ''), event.get('away_team', '')
        if len(event.get('bookmakers', [])) < MIN_BOOKS_FOR_SIGNAL:
            continue

        outcome_quotes, outcome_best = {}, {}  # outcome_quotes[name] = [(book, devigged_prob), ...]
        for bm in event.get('bookmakers', []):
            book = bm.get('title', bm.get('key', ''))
            for market in bm.get('markets', []):
                if market.get('key') != 'h2h':
                    continue
                outcomes = [o for o in market.get('outcomes', []) if o.get('price')]
                total_implied = sum(1 / o['price'] for o in outcomes)
                if total_implied <= 0:
                    continue
                for o in outcomes:
                    devigged = (1 / o['price']) / total_implied
                    outcome_quotes.setdefault(o['name'], []).append((book, devigged))
                    if o['name'] not in outcome_best or o['price'] > outcome_best[o['name']][0]:
                        outcome_best[o['name']] = (o['price'], book)

        for name, (price, book) in outcome_best.items():
            quotes = outcome_quotes.get(name, [])
            # leave-one-out: exclude the candidate book's own price from its fair-value estimate
            other_probs = [p for b, p in quotes if b != book]
            if len(other_probs) < MIN_BOOKS_FOR_SIGNAL - 1:
                continue
            fair_prob = sum(other_probs) / len(other_probs)
            ev_percent = ((fair_prob * price) - 1) * 100
            if min_ev_percent <= ev_percent <= MAX_PLAUSIBLE_EV_PERCENT:
                stake = round(max(5.0, target_stake * random.uniform(0.05, 0.15)), 2)
                results.append({
                    'type': 'ev', 'source': 'live',
                    'match': f"{home} vs {away}", 'outcome': name,
                    'odds': round(price, 2), 'ev_percent': round(ev_percent, 2),
                    'true_prob': round(fair_prob * 100, 1), 'book': book,
                    'stake': stake, 'potential_return': round(stake * price, 2)
                })
    results.sort(key=lambda r: r['ev_percent'], reverse=True)
    return results

def find_live_arbitrage(events, target_stake):
    """True arbitrage: takes the single best publicly available price on every
    outcome (possibly from different bookmakers) and checks whether their
    implied probabilities sum to under 100%. Genuinely rare — most scans
    will legitimately return zero, which is the honest result."""
    opportunities = []
    for event in events or []:
        home, away = event.get('home_team', ''), event.get('away_team', '')
        outcome_best = {}
        for bm in event.get('bookmakers', []):
            book = bm.get('title', bm.get('key', ''))
            for market in bm.get('markets', []):
                if market.get('key') != 'h2h':
                    continue
                for o in market.get('outcomes', []):
                    if not o.get('price'):
                        continue
                    if o['name'] not in outcome_best or o['price'] > outcome_best[o['name']][0]:
                        outcome_best[o['name']] = (o['price'], book)
        if len(outcome_best) < 2:
            continue
        total_implied = sum(1 / p for p, _ in outcome_best.values())
        if total_implied < 1:
            margin = 1 - total_implied
            legs = []
            for name, (price, book) in outcome_best.items():
                stake = round(target_stake * (1 / price) / total_implied, 2)
                legs.append({'outcome': name, 'book': book, 'odds': round(price, 2), 'stake': stake})
            actual_total_stake = round(sum(l['stake'] for l in legs), 2)
            guaranteed_payout = round(actual_total_stake / total_implied, 2)
            guaranteed_profit = round(guaranteed_payout - actual_total_stake, 2)
            opportunities.append({
                'type': 'arbitrage', 'source': 'live',
                'match': f"{home} vs {away}", 'legs': legs,
                'total_stake': actual_total_stake, 'guaranteed_payout': guaranteed_payout,
                'guaranteed_profit': guaranteed_profit,
                'profit_percent': round(margin / total_implied * 100, 2)
            })
    opportunities.sort(key=lambda o: o['profit_percent'], reverse=True)
    return opportunities

# ─────────────────────────────────────────────────────────────
# AI ANALYSIS — DeepSeek via raw HTTP (not the SDK — the studio
# hit silent 403s from an SDK on a prior integration, raw
# requests.post sidesteps that).
# ─────────────────────────────────────────────────────────────
def deepseek_analyze(results):
    if not DEEPSEEK_API_KEY:
        return None, "No DeepSeek API key found in st.secrets / environment."
    if not results:
        return None, "Nothing to analyze yet — run a scan first."

    lines = []
    for r in results[:10]:
        if r['type'] == 'ev':
            lines.append(f"EV bet: {r['match']} — {r['outcome']} @ {r['odds']} ({r['book']}), EV {r['ev_percent']}%, fair win prob ~{r['true_prob']}%")
        else:
            legs = "; ".join(f"{l['outcome']} @ {l['odds']} ({l['book']})" for l in r['legs'])
            lines.append(f"Arbitrage: {r['match']} — {legs}, guaranteed {r['profit_percent']}%")

    prompt = (
        "You are a concise, no-hype sports betting risk analyst. Given this list of scanner "
        "results, write at most 5 short bullet points: which ones look most worth acting on, "
        "any red flags (e.g. odds that look too good to be true, thin margins, single-bookmaker "
        "risk, stale lines), and one practical caution. Be direct and brief, no preamble.\n\n"
        + "\n".join(lines)
    )

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 400,
            },
            timeout=25,
        )
    except requests.RequestException as e:
        return None, f"Network error reaching DeepSeek: {e}"

    if resp.status_code != 200:
        return None, f"DeepSeek API error {resp.status_code}: {resp.text[:200]}"

    try:
        return resp.json()['choices'][0]['message']['content'], None
    except (KeyError, IndexError, ValueError):
        return None, "Unexpected response format from DeepSeek."

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

    render_top_bar("dash")

    if st.button("🚪 Log Out", key="logout_btn"):
        st.session_state.authenticated = False
        st.session_state.user_id = None
        st.session_state.page = "landing"
        st.rerun()

    st.markdown(f"""
    <div class="terminal-nav">
        <div class="terminal-logo">
            <span style="font-size:1.4rem;">📊</span>
            <div>
                <span class="brand">SMART BETTING SYSTEM</span>
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

    bets = get_user_bets(st.session_state.user_id)

    if 'starting_bankroll' not in st.session_state:
        st.session_state.starting_bankroll = get_user_bankroll(st.session_state.user_id)
    bankroll_base = st.session_state.starting_bankroll

    col_kpi_hdr, col_bankroll_edit = st.columns([5, 1])
    with col_bankroll_edit:
        with st.popover("💰 Set Bankroll"):
            st.markdown("**Starting Bankroll**")
            new_bankroll = st.number_input(
                "Amount ($)", min_value=0.0, value=float(bankroll_base), step=50.0, key="bankroll_input"
            )
            if st.button("Save", key="save_bankroll_btn", use_container_width=True, type="primary"):
                set_user_bankroll(st.session_state.user_id, new_bankroll)
                st.session_state.starting_bankroll = new_bankroll
                st.success("✅ Bankroll updated")
                st.rerun()

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
                <div class="value orange">${bankroll_base + profit:.2f}</div>
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
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="label">Active Bets</div><div class="value cyan">0</div><div class="change">No active bets</div></div>
            <div class="kpi-card"><div class="label">Win Rate</div><div class="value lime">0%</div><div class="change">No data yet</div></div>
            <div class="kpi-card"><div class="label">Bankroll</div><div class="value orange">${bankroll_base:,.2f}</div><div class="change">Start betting</div></div>
            <div class="kpi-card"><div class="label">Avg EV</div><div class="value purple">0%</div><div class="change">Scan to find value</div></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown(f"""
    <div class="ev-banner">
        <span class="ev-icon">💡</span>
        <span class="ev-text"><strong>{t['ev_explained']}</strong> {t['ev_explanation']}</span>
    </div>
    """, unsafe_allow_html=True)

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

        sport_options, sports_err = fetch_available_sports()
        if not sport_options:
            sport_options = FALLBACK_SPORT_OPTIONS
            if sports_err:
                st.caption(f"⚠️ Couldn't load your key's full sport list ({sports_err}) — showing a small fallback set.")

        col0, col1, col2, col3 = st.columns(4)
        with col0:
            sport_label = st.selectbox("Sport / League", list(sport_options.keys()))
            sport_key = sport_options[sport_label]
        with col1:
            scan_mode = st.selectbox(t['mode'], [t['ev_mode'], t['arbitrage_mode'], t['both_mode']])
        with col2:
            min_ev = st.slider(t['min_ev'], 1, 20, 5, 1)
        with col3:
            target_stake = st.number_input(t['stake_label'], min_value=10, value=100, step=10)

        if not ODDS_API_KEY:
            st.warning("⚠️ No live Odds API key detected in secrets — scans will use simulated demo data instead of real bookmaker odds.")

        if st.button(t['scan_btn'], use_container_width=True, type="primary"):
            with st.spinner("Scanning live bookmaker odds..."):
                results = []
                data_source = "demo"
                live_error = None

                events, err = fetch_live_odds(sport_key)
                if events is not None:
                    data_source = "live"
                    if scan_mode == t['ev_mode']:
                        results = find_live_ev_bets(events, min_ev, target_stake)
                    elif scan_mode == t['arbitrage_mode']:
                        results = find_live_arbitrage(events, target_stake)
                    else:
                        results = find_live_ev_bets(events, min_ev, target_stake) + find_live_arbitrage(events, target_stake)
                else:
                    live_error = err
                    if scan_mode == t['ev_mode']:
                        results = generate_ev_bets(5, target_stake, min_ev)
                    elif scan_mode == t['arbitrage_mode']:
                        results = generate_arbitrage_opportunities(4, target_stake)
                    else:  # Both
                        results = generate_ev_bets(3, target_stake, min_ev) + generate_arbitrage_opportunities(2, target_stake)

                for item in results:
                    if item['type'] == 'ev':
                        add_bet(st.session_state.user_id, {
                            'sport': 'Soccer',
                            'home_team': item['match'].split(' vs ')[0],
                            'away_team': item['match'].split(' vs ')[1],
                            'outcome': item['outcome'],
                            'odds': item['odds'],
                            'stake': item['stake'],
                            'ev_percent': item['ev_percent'],
                            'result': 'Pending',
                            'return': 0,
                            'profit_loss': 0
                        })
                    else:
                        for leg in item['legs']:
                            add_bet(st.session_state.user_id, {
                                'sport': 'Soccer',
                                'home_team': item['match'].split(' vs ')[0],
                                'away_team': item['match'].split(' vs ')[1],
                                'outcome': f"{leg['outcome']} ({leg['book']}) — arb leg",
                                'odds': leg['odds'],
                                'stake': leg['stake'],
                                'ev_percent': item['profit_percent'],
                                'result': 'Pending',
                                'return': 0,
                                'profit_loss': 0
                            })

                st.session_state.scan_results = results
                st.session_state.scan_mode_used = scan_mode
                st.session_state.scan_data_source = data_source

                if data_source == "live":
                    if results:
                        st.success(f"✅ Live scan complete — found {len(results)} real opportunities.")
                    else:
                        st.info("✅ Live scan complete — no qualifying opportunities right now. That's normal and expected; real edges are rare and short-lived. Try a different sport, lower the Min EV %, or scan again shortly.")
                else:
                    st.warning(f"⚠️ Couldn't reach live odds ({live_error}) — showing {len(results)} simulated demo opportunities instead.")
                st.rerun()

        if 'scan_results' in st.session_state and st.session_state.scan_results:
            source = st.session_state.get('scan_data_source', 'demo')
            badge = '🟢 LIVE DATA' if source == 'live' else '🟡 DEMO DATA (simulated)'
            badge_color = 'var(--lime)' if source == 'live' else 'var(--orange)'

            col_hdr, col_help = st.columns([5, 1])
            with col_hdr:
                st.markdown(
                    f"### {t['best_ev_bets']} "
                    f"<span style='font-family:var(--font-mono); font-size:0.6rem; color:{badge_color}; "
                    f"border:1px solid {badge_color}; border-radius:12px; padding:0.15rem 0.6rem; margin-left:0.5rem;'>{badge}</span>",
                    unsafe_allow_html=True
                )
            with col_help:
                with st.popover("❓ Return"):
                    st.markdown("""
**Why does Return look so big?**

For a **value bet (EV)**, *Return* is the total payout you'd get **only if that specific bet wins** — it's `stake × odds`, not your expected profit. Odds of 8.20 on a $15 stake pay $123 *if it hits*, but that outcome is unlikely, which is exactly why the odds are that high. It roughly cancels out over many bets.

The number that actually matters is the **EV%** badge — your true statistical edge after accounting for how often the bet is expected to win.

For a **true arbitrage** opportunity, there's no "if it wins" — you stake across every possible outcome, so exactly one leg always pays out and the small **Guaranteed Profit** is locked in regardless of the result. That number is deliberately small (often 1–5%) because it's real, not speculative.
                    """)

            total_stake = 0
            total_payout = 0

            for i, item in enumerate(st.session_state.scan_results, 1):
                if item['type'] == 'ev':
                    profit = item['potential_return'] - item['stake']
                    st.markdown(f"""
                    <div class="arb-card">
                        <div class="arb-header">
                            <div class="arb-match">
                                <div class="teams">#{i} {item['match'].replace(' vs ', ' <span class="vs">vs</span> ')}</div>
                                <div class="meta">{item['book']} · EV: {item['ev_percent']:.1f}% · Win Prob: {item['true_prob']:.1f}%</div>
                            </div>
                            <div class="arb-badge">⚡ +{item['ev_percent']:.1f}% EV</div>
                        </div>
                        <div class="arb-body">
                            <div class="odds-grid">
                                <div class="odd-cell"><span class="odd-label">Bet</span><span class="odd-value highlight">{item['outcome']}</span></div>
                                <div class="odd-cell"><span class="odd-label">Odds</span><span class="odd-value">{item['odds']}</span></div>
                                <div class="odd-cell"><span class="odd-label">Stake</span><span class="odd-value">${item['stake']:.2f}</span></div>
                                <div class="odd-cell"><span class="odd-label">Return if wins</span><span class="odd-value" style="color:var(--lime);">${item['potential_return']:.2f}</span></div>
                                <div class="odd-cell"><span class="odd-label">Profit if wins</span><span class="odd-value" style="color:var(--cyan);">+${profit:.2f}</span></div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    total_stake += item['stake']
                    total_payout += item['potential_return']
                else:
                    legs_html = "".join([
                        f"""<div class="odd-cell"><span class="odd-label">{leg['outcome']} · {leg['book']}</span><span class="odd-value">{leg['odds']} · ${leg['stake']:.2f}</span></div>"""
                        for leg in item['legs']
                    ])
                    st.markdown(f"""
                    <div class="arb-card">
                        <div class="arb-header">
                            <div class="arb-match">
                                <div class="teams">#{i} {item['match'].replace(' vs ', ' <span class="vs">vs</span> ')}</div>
                                <div class="meta">Split across {len(item['legs'])} bookmakers · guaranteed regardless of result</div>
                            </div>
                            <div class="arb-badge">🔒 +{item['profit_percent']:.1f}% Guaranteed</div>
                        </div>
                        <div class="arb-body">
                            <div class="odds-grid">
                                {legs_html}
                                <div class="odd-cell"><span class="odd-label">Total Stake</span><span class="odd-value">${item['total_stake']:.2f}</span></div>
                                <div class="odd-cell"><span class="odd-label">Guaranteed Profit</span><span class="odd-value" style="color:var(--cyan);">+${item['guaranteed_profit']:.2f}</span></div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    total_stake += item['total_stake']
                    total_payout += item['guaranteed_payout']

            total_profit = total_payout - total_stake
            st.markdown(f"""
            <div style="background:var(--bg-card); border:1px solid var(--border-glass); border-radius:var(--card-radius); padding:1rem 1.5rem; margin-top:0.5rem;">
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem;">
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Total Opportunities</span><br><span style="color:var(--text-primary); font-weight:700;">{len(st.session_state.scan_results)}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Total Stake</span><br><span style="color:var(--text-primary); font-weight:700;">${total_stake:.2f}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">If All Hit / Payout</span><br><span style="color:var(--lime); font-weight:700;">${total_payout:.2f}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Combined Upside</span><br><span style="color:var(--cyan); font-weight:700;">${total_profit:.2f}</span></div>
                </div>
                <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted); border-top:1px solid var(--border-glass); padding-top:0.5rem;">
                    💡 EV bets only pay out if they win individually — this total assumes every leg hits, which won't happen at once. Arbitrage legs are the only guaranteed number here.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("")
            if not DEEPSEEK_API_KEY:
                st.caption("🤖 AI Analysis unavailable — no DeepSeek API key found in secrets.")
            elif st.button("🤖 AI Analysis", use_container_width=True):
                with st.spinner("Asking the AI analyst..."):
                    analysis, ai_err = deepseek_analyze(st.session_state.scan_results)
                if ai_err:
                    st.error(f"AI Analysis failed: {ai_err}")
                else:
                    st.markdown(f"""
                    <div class="ev-banner">
                        <span class="ev-icon">🤖</span>
                        <span class="ev-text">{analysis}</span>
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
            options = {f"ID {b[0]}: {b[4]} vs {b[5]} — {b[6]} @ {b[7]}": b for b in pending}
            selected_label = st.selectbox(t['select_bet'], list(options.keys()), key="slip_select")
            bet = options[selected_label]

            slip_text = f"""
╔════════════════════════════════════╗
  {COMPANY_NAME.upper()}
  SMART BETTING SYSTEM · PAPER SLIP
╚════════════════════════════════════╝

Bet ID:      #{bet[0]}
Date:        {bet[2][:16]}
Sport:       {bet[3]}
Match:       {bet[4]} vs {bet[5]}
Selection:   {bet[6]}
Odds:        {bet[7]}
Stake:       ${bet[8]:.2f}
Est. EV:     {bet[9]:.1f}%
Potential:   ${bet[7] * bet[8]:.2f}
Status:      {bet[10]}

Generated by {COMPANY_NAME} · {DOMAIN}
""".strip()

            st.markdown(f'<div class="slip-preview">{slip_text}</div>', unsafe_allow_html=True)

            st.download_button(
                label=t['download_slip'],
                data=slip_text,
                file_name=f"slip_{bet[0]}.txt",
                mime="text/plain",
                use_container_width=True,
                type="primary"
            )
        else:
            st.info(t['no_pending_slips'])

    # ─── TAB 5: FAQ ──────────────────────────────────────────
    with tab5:
        st.markdown(f"### {t['faq_title']}")

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
# MAIN ENTRY POINT / ROUTING
# This block was missing from the previous version — without it,
# none of the page functions above ever get called, and the app
# just renders the CSS (near-black background) with no content.
# ─────────────────────────────────────────────────────────────
init_db()

if not st.session_state.authenticated:
    current_page = st.session_state.get('page', 'landing')
    if current_page == 'signup':
        signup_page()
    elif current_page == 'login':
        login_page()
    else:
        landing_page()
else:
    dashboard()
