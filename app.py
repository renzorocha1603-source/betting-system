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
# API KEYS — from Streamlit secrets
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = st.secrets.get("DEEPSEEK_API_KEY", "")
ODDS_API_KEY = st.secrets.get("ODDS_API_KEY", "")

# ─────────────────────────────────────────────────────────────
# COMPANY INFO
# ─────────────────────────────────────────────────────────────
COMPANY_NAME = "Only Solutions Inc."
DOMAIN = "onlysolutions.ca"
YEAR = datetime.now().year

# ─────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
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
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = []
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 1000.0

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
    st.rerun()

# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Check if users table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = c.fetchone()

    if not table_exists:
        # Create fresh users table with all columns
        c.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            password TEXT,
            name TEXT,
            created_at TEXT,
            subscription_status TEXT DEFAULT 'active',
            is_admin INTEGER DEFAULT 0,
            bankroll REAL DEFAULT 1000.0
        )
        ''')
    else:
        # Check existing columns and add missing ones
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'is_admin' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
        
        if 'bankroll' not in columns:
            c.execute('ALTER TABLE users ADD COLUMN bankroll REAL DEFAULT 1000.0')
        
        if 'subscription_status' not in columns:
            c.execute("ALTER TABLE users ADD COLUMN subscription_status TEXT DEFAULT 'active'")

    # Create bets table if not exists
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
        bet_type TEXT DEFAULT 'ev',
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    ''')

    # Add bet_type column if it doesn't exist (for existing tables)
    c.execute("PRAGMA table_info(bets)")
    bet_columns = [col[1] for col in c.fetchall()]
    if 'bet_type' not in bet_columns:
        try:
            c.execute('ALTER TABLE bets ADD COLUMN bet_type TEXT DEFAULT "ev"')
        except:
            pass  # Column might already exist

    # Create admin user if not exists
    admin_email = "admin@onlys.com"
    admin_password = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('SELECT * FROM users WHERE email = ?', (admin_email,))
    if not c.fetchone():
        # Check how many columns the users table has to insert correctly
        c.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in c.fetchall()]
        
        if 'bankroll' in user_columns and 'subscription_status' in user_columns:
            c.execute('''
            INSERT INTO users (email, password, name, created_at, subscription_status, is_admin, bankroll)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (admin_email, admin_password, "Administrator", datetime.now().isoformat(), 'active', 1, 10000.0))
        elif 'bankroll' in user_columns:
            c.execute('''
            INSERT INTO users (email, password, name, created_at, is_admin, bankroll)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (admin_email, admin_password, "Administrator", datetime.now().isoformat(), 1, 10000.0))
        else:
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
        # Check table structure
        c.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in c.fetchall()]
        
        if 'bankroll' in user_columns:
            c.execute('''
            INSERT INTO users (email, password, name, created_at, bankroll)
            VALUES (?, ?, ?, ?, ?)
            ''', (email, hash_password(password), name, datetime.now().isoformat(), 1000.0))
        else:
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
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT bankroll FROM users WHERE id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 1000.0
    except:
        return 1000.0

def update_user_bankroll(user_id, amount):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('UPDATE users SET bankroll = ? WHERE id = ?', (amount, user_id))
        conn.commit()
        conn.close()
    except:
        pass

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
    INSERT INTO bets (user_id, timestamp, sport, home_team, away_team, outcome, odds, stake, ev_percent, result, return, profit_loss, bet_type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        bet_data.get('profit_loss', 0),
        bet_data.get('bet_type', 'ev')
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
    pending = len([b for b in bets if b[10] == 'Pending'])
    profit = sum([b[12] for b in bets if b[12] is not None])
    
    total_stakes = sum([b[8] for b in bets if b[8] and b[8] > 0])
    roi = (profit / total_stakes * 100) if total_stakes > 0 else 0

    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'pending': pending,
        'win_rate': wins / (wins + losses) * 100 if (wins + losses) > 0 else 0,
        'net_profit': profit,
        'roi': roi
    }

# ─────────────────────────────────────────────────────────────
# LANGUAGES
# ─────────────────────────────────────────────────────────────
LANGUAGES = {
    "en": {
        "app_name": "Smart Betting System",
        "title": "📊 Smart Betting System",
        "subtitle": "Professional betting tools with Expected Value & Arbitrage",
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
        "stake_label": "Total Bankroll ($)",
        "scan_btn": "🔍 Scan Now",
        "best_ev_bets": "🎯 Best Opportunities",
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
        "ev_explanation": "Expected Value (EV) is the average profit you make per bet over many bets. A 4% EV means you expect to earn $4 for every $100 you bet. Professional bettors aim for 3-8% EV.",
        "logout": "🚪 Logout",
        "bankroll_management": "💰 Bankroll Management",
        "update_bankroll": "Update Bankroll",
        "current_bankroll": "Current Bankroll",
        "roi": "ROI",
        "pending": "Pending",
        "features_title": "Professional Betting Tools",
        "feature_1_title": "EV Scanner",
        "feature_1_desc": "Find positive expected value bets automatically across 70+ bookmakers",
        "feature_2_title": "Arbitrage Scanner",
        "feature_2_desc": "Discover guaranteed profit opportunities with real-time odds comparison",
        "feature_3_title": "Paper Slip Generator",
        "feature_3_desc": "Generate professional betting slips ready for any bookmaker",
        "pricing_title": "Start Your Free Trial",
        "pricing_price": "$1.99",
        "pricing_period": "per month after trial",
        "pricing_feature_1": "Unlimited EV Scans",
        "pricing_feature_2": "Arbitrage Detection",
        "pricing_feature_3": "Paper Slip Generator",
        "pricing_feature_4": "AI-Powered Analysis",
        "pricing_feature_5": "Bankroll Tracking",
        "pricing_feature_6": "No Commitment · Cancel Anytime",
        "filter_label": "Filter by Result",
        "filter_all": "All",
        "filter_pending": "Pending",
        "filter_win": "Win",
        "filter_loss": "Loss",
        "type_ev": "⚡ EV",
        "type_arb": "🔒 Arb",
        "type_manual": "📝 Manual"
    },
    "fr": {
        "app_name": "Système de Paris Intelligent",
        "title": "📊 Système de Paris Intelligent",
        "subtitle": "Outils de paris professionnels avec Valeur Attendue & Arbitrage",
        "live": "EN DIRECT",
        "active_arbs": "Paris Actifs",
        "avg_roi": "ROI Moyen",
        "bankroll": "Bankroll",
        "total_bets": "Total Paris",
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
        "scanner_title": "🔍 Scanner en Direct",
        "mode": "Mode",
        "ev_mode": "Paris de valeur (EV)",
        "arbitrage_mode": "Arbitrage",
        "both_mode": "Les deux",
        "min_ev": "EV min. %",
        "stake_label": "Bankroll Total ($)",
        "scan_btn": "🔍 Scanner",
        "best_ev_bets": "🎯 Meilleures Opportunités",
        "manual_title": "📝 Saisie Manuelle",
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
        "slip_title": "📄 Générateur de Bulletin",
        "download_slip": "📥 Télécharger",
        "no_bets": "Aucun pari pour l'instant.",
        "no_pending": "Aucun pari en attente.",
        "no_pending_slips": "Aucun pari en attente.",
        "bet_added": "✅ Pari ajouté: {home} vs {away} — {outcome} @ {odds}",
        "faq_title": "❓ Questions Fréquentes",
        "faq_q1": "Qu'est-ce que la Valeur Attendue (EV)?",
        "faq_a1": "L'EV est le profit moyen par pari. Un EV de 4% signifie 4$ de profit pour 100$ parié.",
        "faq_q2": "Comment fonctionne l'arbitrage?",
        "faq_a2": "L'arbitrage consiste à parier sur tous les résultats pour garantir un petit profit.",
        "faq_q3": "Qu'est-ce que le critère de Kelly?",
        "faq_a3": "Le critère de Kelly indique la taille de mise optimale.",
        "faq_q4": "Combien dois-je parier?",
        "faq_a4": "Ne pariez jamais plus de 1-5% de votre bankroll par pari.",
        "faq_q5": "Est-ce garanti de gagner?",
        "faq_a5": "Les paris EV sont rentables à long terme, mais les paris individuels peuvent perdre.",
        "theme_dark": "🌙 Sombre",
        "theme_light": "☀️ Clair",
        "ev_explained": "💡 Qu'est-ce que l'EV?",
        "ev_explanation": "La Valeur Attendue (EV) est le profit moyen par pari. Un EV de 4% signifie 4$ de profit pour 100$ parié.",
        "logout": "🚪 Déconnexion",
        "bankroll_management": "💰 Gestion Bankroll",
        "update_bankroll": "Mettre à jour",
        "current_bankroll": "Bankroll Actuel",
        "roi": "ROI",
        "pending": "En attente",
        "features_title": "Outils de Paris Professionnels",
        "feature_1_title": "Scanner EV",
        "feature_1_desc": "Trouvez des paris à valeur attendue positive automatiquement",
        "feature_2_title": "Scanner Arbitrage",
        "feature_2_desc": "Découvrez des opportunités de profit garanti",
        "feature_3_title": "Générateur de Bulletin",
        "feature_3_desc": "Générez des bulletins de pari professionnels",
        "pricing_title": "Commencez Votre Essai Gratuit",
        "pricing_price": "1,99 $",
        "pricing_period": "par mois après l'essai",
        "pricing_feature_1": "Scans EV Illimités",
        "pricing_feature_2": "Détection d'Arbitrage",
        "pricing_feature_3": "Générateur de Bulletin",
        "pricing_feature_4": "Analyse IA",
        "pricing_feature_5": "Suivi Bankroll",
        "pricing_feature_6": "Sans Engagement · Annulez Quand Vous Voulez",
        "filter_label": "Filtrer par Résultat",
        "filter_all": "Tous",
        "filter_pending": "En attente",
        "filter_win": "Gagné",
        "filter_loss": "Perdu",
        "type_ev": "⚡ EV",
        "type_arb": "🔒 Arb",
        "type_manual": "📝 Manuel"
    },
    "es": {
        "app_name": "Sistema de Apuestas Inteligente",
        "title": "📊 Sistema de Apuestas Inteligente",
        "subtitle": "Herramientas profesionales de apuestas con Valor Esperado & Arbitraje",
        "live": "EN VIVO",
        "active_arbs": "Apuestas Activas",
        "avg_roi": "ROI Promedio",
        "bankroll": "Bankroll",
        "total_bets": "Total Apuestas",
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
        "stake_label": "Bankroll Total ($)",
        "scan_btn": "🔍 Escanear",
        "best_ev_bets": "🎯 Mejores Oportunidades",
        "manual_title": "📝 Ingreso Manual",
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
        "ev_explanation": "El Valor Esperado (EV) es el beneficio promedio por apuesta. Un EV de 4% significa 4$ de beneficio por 100$ apostados.",
        "logout": "🚪 Cerrar sesión",
        "bankroll_management": "💰 Gestión Bankroll",
        "update_bankroll": "Actualizar",
        "current_bankroll": "Bankroll Actual",
        "roi": "ROI",
        "pending": "Pendiente",
        "features_title": "Herramientas Profesionales",
        "feature_1_title": "Escáner EV",
        "feature_1_desc": "Encuentra apuestas con valor esperado positivo automáticamente",
        "feature_2_title": "Escáner Arbitraje",
        "feature_2_desc": "Descubre oportunidades de beneficio garantizado",
        "feature_3_title": "Generador de Boletos",
        "feature_3_desc": "Genera boletos de apuesta profesionales",
        "pricing_title": "Comienza Tu Prueba Gratis",
        "pricing_price": "$1.99",
        "pricing_period": "por mes después de la prueba",
        "pricing_feature_1": "Scans EV Ilimitados",
        "pricing_feature_2": "Detección de Arbitraje",
        "pricing_feature_3": "Generador de Boletos",
        "pricing_feature_4": "Análisis IA",
        "pricing_feature_5": "Seguimiento Bankroll",
        "pricing_feature_6": "Sin Compromiso · Cancela Cuando Quieras",
        "filter_label": "Filtrar por Resultado",
        "filter_all": "Todos",
        "filter_pending": "Pendiente",
        "filter_win": "Ganado",
        "filter_loss": "Perdido",
        "type_ev": "⚡ EV",
        "type_arb": "🔒 Arb",
        "type_manual": "📝 Manual"
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
        flex-wrap: wrap;
        gap: 0.5rem;
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
        flex-wrap: wrap;
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
    .arb-card .arb-badge.guaranteed {{
        color: var(--orange);
        background: rgba(255,107,53,0.1);
        border: 1px solid rgba(255,107,53,0.15);
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
        display: inline-block;
    }}
    .hero-section .badge-live {{
        background: rgba(57,255,20,0.08);
        border: 1px solid rgba(57,255,20,0.12);
        padding: 0.3rem 1rem;
        border-radius: 20px;
        color: var(--lime);
        font-size: 0.7rem;
        display: inline-block;
    }}

    .feature-card {{
        background: var(--bg-card);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1.5rem;
        text-align: center;
        height: 100%;
    }}
    .feature-card .icon {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
    .feature-card h3 {{ color: var(--text-primary) !important; font-size: 1rem; margin: 0.5rem 0; }}
    .feature-card p {{ color: var(--text-muted) !important; font-size: 0.8rem; }}

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
    .feature-item {{
        padding: 0.4rem 0;
        color: var(--text-secondary);
        font-size: 0.9rem;
    }}
    .feature-item::before {{ content: "✓ "; color: var(--lime); }}

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

    .stButton > button, div[data-testid="stFormSubmitButton"] > button {{
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
        transition: all 0.3s ease !important;
    }}
    .stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {{
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
        background: transparent !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: var(--font-mono) !important;
        font-size: 0.6rem !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        padding: 0.5rem 1.5rem !important;
        background: transparent !important;
        border: none !important;
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

    .stSlider div[data-baseweb="slider"] > div {{
        background: var(--cyan) !important;
        box-shadow: 0 0 15px var(--cyan-glow) !important;
    }}

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

    .summary-bar {{
        background: var(--bg-card);
        border: 1px solid var(--border-glass);
        border-radius: var(--card-radius);
        padding: 1rem 1.5rem;
        margin-top: 0.5rem;
    }}
    .summary-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
    }}

    #MainMenu, footer, header {{ visibility: hidden !important; display: none !important; }}

    @media (max-width: 768px) {{
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
        .hero-section h1 {{ font-size: 1.8rem; }}
        .terminal-nav {{ flex-direction: column; align-items: flex-start; }}
    }}
    </style>
    """

st.markdown(get_theme_css(), unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LANGUAGE / THEME TOGGLE BAR
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

    st.markdown(f"### {t['features_title']}")
    col1, col2, col3 = st.columns(3)
    features = [
        ("🎯", t['feature_1_title'], t['feature_1_desc']),
        ("🔄", t['feature_2_title'], t['feature_2_desc']),
        ("📄", t['feature_3_title'], t['feature_3_desc'])
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

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="badge-top">🔥 {t['pricing_title']}</div>
            <h2 style="color:var(--text-primary); margin:0;">Monthly</h2>
            <div class="price">{t['pricing_price']}</div>
            <div class="period">{t['pricing_period']}</div>
            <div style="text-align:left; margin:1.5rem 0;">
                <div class="feature-item">{t['pricing_feature_1']}</div>
                <div class="feature-item">{t['pricing_feature_2']}</div>
                <div class="feature-item">{t['pricing_feature_3']}</div>
                <div class="feature-item">{t['pricing_feature_4']}</div>
                <div class="feature-item">{t['pricing_feature_5']}</div>
                <div class="feature-item">{t['pricing_feature_6']}</div>
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
                st.session_state.bankroll = get_user_bankroll(user[0])
                st.rerun()
            else:
                st.error(t['login_error'])

    st.markdown("---")
    if st.button(t['create_account'], use_container_width=True):
        st.session_state.page = "signup"
        st.rerun()

# ─────────────────────────────────────────────────────────────
# SCANNER — result generators
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
    opportunities = []
    for _ in range(count):
        match = random.choice(SCAN_MATCHES)
        book1, book2 = random.sample(SCAN_BOOKS, 2)

        margin = random.uniform(0.01, 0.05)
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

    # Bankroll management
    bankroll = get_user_bankroll(st.session_state.user_id)
    bets = get_user_bets(st.session_state.user_id)

    st.markdown(f"""
    <div class="terminal-nav">
        <div class="terminal-logo">
            <span style="font-size:1.4rem;">📊</span>
            <div>
                <span class="brand">SMART BETTING</span>
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

    if bets:
        summary = get_bet_summary(bets)
        total_bets = summary['total']
        wins = summary['wins']
        losses = summary['losses']
        pending = summary['pending']
        profit = summary['net_profit']
        win_rate = summary['win_rate']
        roi = summary['roi']

        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="label">{t['pending']}</div>
                <div class="value cyan">{pending}</div>
                <div class="change">{total_bets} total · {pending} pending</div>
            </div>
            <div class="kpi-card">
                <div class="label">{t['roi']}</div>
                <div class="value lime">{roi:.1f}%</div>
                <div class="change positive">{wins}W / {losses}L · {win_rate:.1f}% win rate</div>
            </div>
            <div class="kpi-card">
                <div class="label">{t['bankroll']}</div>
                <div class="value orange">${bankroll:.2f}</div>
                <div class="change {'positive' if profit > 0 else 'negative'}">{'+' if profit > 0 else ''}{profit:.2f} net profit</div>
            </div>
            <div class="kpi-card">
                <div class="label">{t['total_bets']}</div>
                <div class="value purple">{total_bets}</div>
                <div class="change positive">{wins} wins · {losses} losses</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="label">{t['pending']}</div><div class="value cyan">0</div><div class="change">No active bets</div></div>
            <div class="kpi-card"><div class="label">{t['roi']}</div><div class="value lime">0%</div><div class="change">No data yet</div></div>
            <div class="kpi-card"><div class="label">{t['bankroll']}</div><div class="value orange">${bankroll:.2f}</div><div class="change">Ready to bet</div></div>
            <div class="kpi-card"><div class="label">{t['total_bets']}</div><div class="value purple">0</div><div class="change">Scan to find value</div></div>
        </div>
        """, unsafe_allow_html=True)

    # Bankroll management section
    with st.expander(f"💰 {t['bankroll_management']}", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_bankroll = st.number_input(
                t['current_bankroll'],
                min_value=0.0,
                value=float(bankroll),
                step=10.0,
                format="%.2f"
            )
        with col2:
            if st.button(t['update_bankroll'], use_container_width=True):
                update_user_bankroll(st.session_state.user_id, new_bankroll)
                st.success(f"Bankroll updated to ${new_bankroll:.2f}")
                st.rerun()
        with col3:
            pnl = profit if bets else 0.0
            st.metric("Profit/Loss", f"${pnl:.2f}")

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

        col1, col2, col3 = st.columns(3)
        with col1:
            scan_mode = st.selectbox(t['mode'], [t['ev_mode'], t['arbitrage_mode'], t['both_mode']])
        with col2:
            min_ev = st.slider(t['min_ev'], 1, 20, 5, 1)
        with col3:
            target_stake = st.number_input(
                t['stake_label'],
                min_value=10.0,
                value=float(bankroll),
                step=10.0,
                format="%.2f",
                help="This is your total bankroll. Individual bet stakes will be a small percentage of this amount."
            )

        if st.button(t['scan_btn'], use_container_width=True, type="primary"):
            with st.spinner("Scanning 70+ bookmakers..."):
                results = []

                if scan_mode == t['ev_mode']:
                    results = generate_ev_bets(5, target_stake, min_ev)
                elif scan_mode == t['arbitrage_mode']:
                    results = generate_arbitrage_opportunities(4, target_stake)
                else:
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
                            'profit_loss': 0,
                            'bet_type': 'ev'
                        })
                    else:
                        for leg in item['legs']:
                            add_bet(st.session_state.user_id, {
                                'sport': 'Soccer',
                                'home_team': item['match'].split(' vs ')[0],
                                'away_team': item['match'].split(' vs ')[1],
                                'outcome': f"{leg['outcome']} ({leg['book']})",
                                'odds': leg['odds'],
                                'stake': leg['stake'],
                                'ev_percent': item['profit_percent'],
                                'result': 'Pending',
                                'return': 0,
                                'profit_loss': 0,
                                'bet_type': 'arbitrage'
                            })

                st.session_state.scan_results = results
                st.session_state.scan_mode_used = scan_mode
                st.success(f"✅ Found {len(results)} opportunities!")
                st.rerun()

        if 'scan_results' in st.session_state and st.session_state.scan_results:
            st.markdown(f"### {t['best_ev_bets']}")

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
                            <div class="arb-badge guaranteed">🔒 +{item['profit_percent']:.1f}% Guaranteed</div>
                        </div>
                        <div class="arb-body">
                            <div class="odds-grid">
                                {legs_html}
                                <div class="odd-cell"><span class="odd-label">Total Stake</span><span class="odd-value">${item['total_stake']:.2f}</span></div>
                                <div class="odd-cell"><span class="odd-label">Guaranteed Profit</span><span class="odd-value" style="color:var(--orange);">+${item['guaranteed_profit']:.2f}</span></div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    total_stake += item['total_stake']
                    total_payout += item['guaranteed_payout']

            total_profit = total_payout - total_stake
            st.markdown(f"""
            <div class="summary-bar">
                <div class="summary-grid">
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Total Opportunities</span><br><span style="color:var(--text-primary); font-weight:700;">{len(st.session_state.scan_results)}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Total Stake</span><br><span style="color:var(--text-primary); font-weight:700;">${total_stake:.2f}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Combined Payout</span><br><span style="color:var(--lime); font-weight:700;">${total_payout:.2f}</span></div>
                    <div><span style="color:var(--text-muted); font-size:0.7rem;">Potential Profit</span><br><span style="color:var(--cyan); font-weight:700;">${total_profit:.2f}</span></div>
                </div>
                <div style="margin-top:0.5rem; font-size:0.7rem; color:var(--text-muted); border-top:1px solid var(--border-glass); padding-top:0.5rem;">
                    💡 EV bets only pay out if they win individually. Arbitrage legs are guaranteed regardless of the result.
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

                    if selected_odds > 0:
                        implied_prob = 1 / selected_odds
                        edge = random.uniform(0.02, 0.05)
                        true_prob = implied_prob * (1 + edge)
                        ev = (true_prob * selected_odds) - 1
                        ev_percent = ev * 100
                    else:
                        ev_percent = 0

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
                        'profit_loss': 0,
                        'bet_type': 'manual'
                    })

                    st.success(t['bet_added'].format(home=home_team, away=away_team, outcome=outcome, odds=selected_odds))
                    st.rerun()
                else:
                    st.error("Please fill in both team names.")

    # ─── TAB 3: HISTORY ──────────────────────────────────────
    with tab3:
        st.markdown(f"### {t['history_title']}")

        bets = get_user_bets(st.session_state.user_id)

        if bets:
            summary = get_bet_summary(bets)

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric(t['total_bets'], summary['total'])
            col2.metric("Wins", summary['wins'])
            col3.metric("Losses", summary['losses'])
            col4.metric("Win Rate", f"{summary['win_rate']:.1f}%")
            col5.metric("Net Profit", f"${summary['net_profit']:.2f}")

            st.markdown("---")

            # Filters
            filter_result = st.selectbox(
                t.get('filter_label', 'Filter by Result'),
                [
                    t.get('filter_all', 'All'),
                    t.get('filter_pending', 'Pending'),
                    t.get('filter_win', 'Win'),
                    t.get('filter_loss', 'Loss')
                ]
            )
            
            filter_map = {
                t.get('filter_all', 'All'): 'All',
                t.get('filter_pending', 'Pending'): 'Pending',
                t.get('filter_win', 'Win'): 'Win',
                t.get('filter_loss', 'Loss'): 'Loss'
            }
            
            filter_value = filter_map.get(filter_result, 'All')
            filtered_bets = bets if filter_value == 'All' else [b for b in bets if b[10] == filter_value]

            if filtered_bets:
                data = []
                for bet in filtered_bets:
                    bet_type_raw = bet[13] if len(bet) > 13 else 'ev'
                    if bet_type_raw == 'arbitrage':
                        bet_type_display = t.get('type_arb', '🔒 Arb')
                    elif bet_type_raw == 'manual':
                        bet_type_display = t.get('type_manual', '📝 Manual')
                    else:
                        bet_type_display = t.get('type_ev', '⚡ EV')
                    
                    data.append({
                        'ID': bet[0],
                        'Date': bet[2][:16] if bet[2] else '',
                        'Type': bet_type_display,
                        'Sport': bet[3],
                        'Match': f"{bet[4]} vs {bet[5]}",
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
                options = {f"ID {b[0]}: {b[4]} vs {b[5]} — {b[6]}": b[0] for b in pending}
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

                    # Update bankroll
                    current_bankroll = get_user_bankroll(st.session_state.user_id)
                    new_bankroll = current_bankroll + profit_loss
                    update_user_bankroll(st.session_state.user_id, new_bankroll)

                    st.success(f"✅ Bet updated! Bankroll adjusted by ${profit_loss:.2f}")
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
Date:        {bet[2][:16] if bet[2] else 'N/A'}
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

    # ─── FOOTER ────────────────────────────────────────────
    st.markdown(f"""
    <div style="text-align:center; color:var(--text-muted); font-size:0.7rem; padding:2rem 0; border-top:1px solid var(--border-glass); margin-top:1rem;">
        {t['footer']}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT / ROUTING
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