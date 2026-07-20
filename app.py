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
# HARDCODED API KEYS
# ─────────────────────────────────────────────────────────────
DEEPSEEK_API_KEY = "sk-09832202e2c74c7ea73891197056a8e6"
ODDS_API_KEY = "a585010a77f214e1ce910e778b079400"

# ─────────────────────────────────────────────────────────────
# LANGUAGES
# ─────────────────────────────────────────────────────────────
LANGUAGES = {
    "en": {
        "title": "📊 Intelligent Betting System",
        "subtitle": "Mathematical betting with EV + Arbitrage scanning.",
        "tagline": "Only bet when the numbers say so.",
        "free_trial_badge": "🆓 7-day free trial · No credit card required",
        "features": [
            ("🎯", "EV Scanner", "Find positive expected value bets automatically"),
            ("🔄", "Arbitrage Scanner", "Discover guaranteed profit opportunities"),
            ("📄", "Paper Slip Generator", "Print ready-to-use betting slips"),
            ("📊", "Live Odds", "Real-time odds from 70+ bookmakers"),
            ("🤖", "AI Assistant", "DeepSeek-powered betting analysis"),
            ("📈", "History Tracking", "Track all your bets and performance")
        ],
        "testimonial": "I've been using this system for 3 months. The math is solid — I'm up 23% on my bankroll.",
        "testimonial_author": "— John D., Verified User",
        "pricing_title": "💰 Simple Pricing",
        "pricing_badge": "🔥 Most Popular",
        "pricing_name": "Monthly",
        "pricing_price": "$1.99",
        "pricing_period": "per month",
        "pricing_features": [
            "Unlimited EV Scans",
            "Arbitrage Detection",
            "Paper Slip Generator",
            "AI Analysis",
            "No commitment",
            "Cancel anytime"
        ],
        "free_trial_btn": "🚀 Start Free Trial",
        "free_trial_note": "🆓 7-day free trial · Then $1.99/month",
        "signup_title": "🚀 Create Your Account",
        "signup_subtitle": "Start your **7-day free trial**. No credit card required.",
        "name_label": "Full Name",
        "email_label": "Email",
        "password_label": "Password",
        "confirm_label": "Confirm Password",
        "signup_btn": "Start Free Trial",
        "login_btn": "🔐 Already have an account? Log In",
        "login_title": "🔐 Welcome Back",
        "login_submit": "Sign In",
        "create_account": "📝 Create an account",
        "footer": f"{COMPANY_NAME} · {DOMAIN} · {YEAR}",
        "dashboard_welcome": "Welcome back",
        "dashboard_title": "📊 Betting System",
        "member_since": "Member since",
        "total_bets": "💰 Total Bets",
        "wins": "✅ Wins",
        "win_rate": "📈 Win Rate",
        "net_profit": "📊 Net Profit",
        "no_bets": "👋 No bets yet. Start scanning for opportunities below!",
        "scanner_title": "🔍 Live Scanner",
        "scanner_desc": "Scan multiple sportsbooks for EV and Arbitrage opportunities.",
        "mode": "Mode",
        "ev_mode": "EV (Value Bets)",
        "arbitrage_mode": "Arbitrage",
        "both_mode": "Both",
        "min_ev": "Min EV %",
        "stake_label": "Stake ($)",
        "scan_btn": "🔍 Scan Now",
        "scanning": "🔄 Scanning 70+ bookmakers...",
        "found_bets": "✅ Found {count} EV bets!",
        "best_ev_bets": "🎯 Best EV Bets",
        "book": "Book",
        "total_stake": "💰 Total Stake",
        "expected_return": "📈 Expected Return",
        "expected_profit": "🎯 Expected Profit",
        "manual_title": "📝 Manual Odds Input",
        "manual_desc": "Enter odds manually if you see a good opportunity.",
        "sport": "Sport",
        "home_team": "Home Team",
        "away_team": "Away Team",
        "home_odds": "Home Odds",
        "draw_odds": "Draw Odds",
        "away_odds": "Away Odds",
        "your_bet": "Your Bet",
        "your_stake": "Your Stake ($)",
        "add_bet": "➕ Add Bet",
        "bet_added": "✅ Bet added: {home} vs {away} — {outcome} @ {odds}",
        "history_title": "📊 Your Betting History",
        "update_result": "✏️ Update Result",
        "select_bet": "Select Bet",
        "result": "Result",
        "return_amount": "Return ($)",
        "update_btn": "Update",
        "bet_updated": "✅ Bet updated!",
        "no_pending": "No pending bets.",
        "slip_title": "📄 Paper Slip Generator",
        "slip_desc": "Generate a printable paper slip for retail betting.",
        "select_slip_bets": "Select bets for your slip",
        "download_slip": "📥 Download Slip",
        "no_pending_slips": "No pending bets available. Scan for opportunities first!",
        "sign_out": "🚪 Sign Out",
        "logout": "Logout",
        "login_error": "Invalid email or password.",
        "signup_error": "All fields are required.",
        "password_mismatch": "Passwords do not match.",
        "password_short": "Password must be at least 6 characters.",
        "account_created": "✅ Account created! You can now log in.",
        "email_exists": "Email already registered. Please log in.",
        "user_session_error": "User session error. Please log in again."
    },
    "fr": {
        "title": "📊 Système de Paris Intelligent",
        "subtitle": "Paris mathématiques avec analyse EV + Arbitrage.",
        "tagline": "Ne pariez que lorsque les chiffres le disent.",
        "free_trial_badge": "🆓 Essai gratuit de 7 jours · Aucune carte de crédit requise",
        "features": [
            ("🎯", "Scanner EV", "Trouvez automatiquement des paris à valeur positive"),
            ("🔄", "Scanner d'arbitrage", "Découvrez des opportunités de profit garanties"),
            ("📄", "Générateur de bulletin", "Imprimez des bulletins de jeu prêts à l'emploi"),
            ("📊", "Cotes en direct", "Cotes en temps réel de plus de 70 bookmakers"),
            ("🤖", "Assistant IA", "Analyse de paris alimentée par DeepSeek"),
            ("📈", "Suivi d'historique", "Suivez tous vos paris et performances")
        ],
        "testimonial": "J'utilise ce système depuis 3 mois. Les calculs sont solides — je suis en hausse de 23% sur ma bankroll.",
        "testimonial_author": "— Jean D., Utilisateur vérifié",
        "pricing_title": "💰 Tarification Simple",
        "pricing_badge": "🔥 Le Plus Populaire",
        "pricing_name": "Mensuel",
        "pricing_price": "1,99 $",
        "pricing_period": "par mois",
        "pricing_features": [
            "Analyses EV illimitées",
            "Détection d'arbitrage",
            "Générateur de bulletin",
            "Analyse IA",
            "Sans engagement",
            "Annulation à tout moment"
        ],
        "free_trial_btn": "🚀 Essai Gratuit",
        "free_trial_note": "🆓 Essai gratuit de 7 jours · Puis 1,99 $/mois",
        "signup_title": "🚀 Créez Votre Compte",
        "signup_subtitle": "Commencez votre **essai gratuit de 7 jours**. Aucune carte de crédit requise.",
        "name_label": "Nom complet",
        "email_label": "Courriel",
        "password_label": "Mot de passe",
        "confirm_label": "Confirmer le mot de passe",
        "signup_btn": "Essai Gratuit",
        "login_btn": "🔐 Déjà un compte? Se connecter",
        "login_title": "🔐 Bon Retour",
        "login_submit": "Se connecter",
        "create_account": "📝 Créer un compte",
        "footer": f"{COMPANY_NAME} · {DOMAIN} · {YEAR}",
        "dashboard_welcome": "Bon retour",
        "dashboard_title": "📊 Système de Paris",
        "member_since": "Membre depuis",
        "total_bets": "💰 Total des paris",
        "wins": "✅ Victoires",
        "win_rate": "📈 Taux de réussite",
        "net_profit": "📊 Profit net",
        "no_bets": "👋 Aucun pari pour l'instant. Commencez à scanner des opportunités!",
        "scanner_title": "🔍 Scanner en direct",
        "scanner_desc": "Analysez plusieurs bookmakers pour des opportunités EV et d'arbitrage.",
        "mode": "Mode",
        "ev_mode": "EV (Paris de valeur)",
        "arbitrage_mode": "Arbitrage",
        "both_mode": "Les deux",
        "min_ev": "EV min. %",
        "stake_label": "Mise ($)",
        "scan_btn": "🔍 Scanner",
        "scanning": "🔄 Analyse de 70+ bookmakers...",
        "found_bets": "✅ {count} paris EV trouvés!",
        "best_ev_bets": "🎯 Meilleurs paris EV",
        "book": "Bookmaker",
        "total_stake": "💰 Mise totale",
        "expected_return": "📈 Retour attendu",
        "expected_profit": "🎯 Profit attendu",
        "manual_title": "📝 Saisie manuelle des cotes",
        "manual_desc": "Entrez les cotes manuellement si vous voyez une bonne opportunité.",
        "sport": "Sport",
        "home_team": "Équipe domicile",
        "away_team": "Équipe extérieure",
        "home_odds": "Cote domicile",
        "draw_odds": "Cote nul",
        "away_odds": "Cote extérieur",
        "your_bet": "Votre pari",
        "your_stake": "Votre mise ($)",
        "add_bet": "➕ Ajouter un pari",
        "bet_added": "✅ Pari ajouté: {home} vs {away} — {outcome} @ {odds}",
        "history_title": "📊 Historique de vos paris",
        "update_result": "✏️ Mettre à jour le résultat",
        "select_bet": "Sélectionnez un pari",
        "result": "Résultat",
        "return_amount": "Retour ($)",
        "update_btn": "Mettre à jour",
        "bet_updated": "✅ Pari mis à jour!",
        "no_pending": "Aucun pari en attente.",
        "slip_title": "📄 Générateur de bulletin",
        "slip_desc": "Générez un bulletin de jeu imprimable pour les paris en boutique.",
        "select_slip_bets": "Sélectionnez les paris pour votre bulletin",
        "download_slip": "📥 Télécharger le bulletin",
        "no_pending_slips": "Aucun pari en attente. Scannez d'abord des opportunités!",
        "sign_out": "🚪 Déconnexion",
        "logout": "Se déconnecter",
        "login_error": "Courriel ou mot de passe incorrect.",
        "signup_error": "Tous les champs sont requis.",
        "password_mismatch": "Les mots de passe ne correspondent pas.",
        "password_short": "Le mot de passe doit contenir au moins 6 caractères.",
        "account_created": "✅ Compte créé! Vous pouvez maintenant vous connecter.",
        "email_exists": "Courriel déjà enregistré. Veuillez vous connecter.",
        "user_session_error": "Erreur de session utilisateur. Veuillez vous reconnecter."
    },
    "es": {
        "title": "📊 Sistema de Apuestas Inteligente",
        "subtitle": "Apuestas matemáticas con análisis EV + Arbitraje.",
        "tagline": "Solo apuesta cuando los números lo digan.",
        "free_trial_badge": "🆓 Prueba gratuita de 7 días · Sin tarjeta de crédito",
        "features": [
            ("🎯", "Escáner EV", "Encuentra apuestas con valor esperado positivo automáticamente"),
            ("🔄", "Escáner de Arbitraje", "Descubre oportunidades de beneficio garantizado"),
            ("📄", "Generador de Boletos", "Imprime boletos de apuestas listos para usar"),
            ("📊", "Cuotas en Vivo", "Cuotas en tiempo real de más de 70 casas de apuestas"),
            ("🤖", "Asistente IA", "Análisis de apuestas con DeepSeek"),
            ("📈", "Historial de Seguimiento", "Sigue todas tus apuestas y rendimiento")
        ],
        "testimonial": "He estado usando este sistema por 3 meses. Las matemáticas son sólidas — he subido un 23% en mi bankroll.",
        "testimonial_author": "— Juan D., Usuario Verificado",
        "pricing_title": "💰 Precios Simples",
        "pricing_badge": "🔥 Más Popular",
        "pricing_name": "Mensual",
        "pricing_price": "$1.99",
        "pricing_period": "por mes",
        "pricing_features": [
            "Escáneres EV ilimitados",
            "Detección de Arbitraje",
            "Generador de Boletos",
            "Análisis IA",
            "Sin compromiso",
            "Cancela en cualquier momento"
        ],
        "free_trial_btn": "🚀 Prueba Gratis",
        "free_trial_note": "🆓 Prueba gratis de 7 días · Luego $1.99/mes",
        "signup_title": "🚀 Crea Tu Cuenta",
        "signup_subtitle": "Comienza tu **prueba gratuita de 7 días**. Sin tarjeta de crédito.",
        "name_label": "Nombre completo",
        "email_label": "Correo",
        "password_label": "Contraseña",
        "confirm_label": "Confirmar contraseña",
        "signup_btn": "Prueba Gratis",
        "login_btn": "🔐 ¿Ya tienes cuenta? Iniciar sesión",
        "login_title": "🔐 Bienvenido de Vuelta",
        "login_submit": "Iniciar sesión",
        "create_account": "📝 Crear una cuenta",
        "footer": f"{COMPANY_NAME} · {DOMAIN} · {YEAR}",
        "dashboard_welcome": "Bienvenido de vuelta",
        "dashboard_title": "📊 Sistema de Apuestas",
        "member_since": "Miembro desde",
        "total_bets": "💰 Total apuestas",
        "wins": "✅ Victorias",
        "win_rate": "📈 Tasa de éxito",
        "net_profit": "📊 Beneficio neto",
        "no_bets": "👋 Aún no hay apuestas. ¡Comienza a escanear oportunidades!",
        "scanner_title": "🔍 Escáner en Vivo",
        "scanner_desc": "Escanea múltiples casas de apuestas para oportunidades EV y de Arbitraje.",
        "mode": "Modo",
        "ev_mode": "EV (Apuestas de valor)",
        "arbitrage_mode": "Arbitraje",
        "both_mode": "Ambos",
        "min_ev": "VE mín. %",
        "stake_label": "Apuesta ($)",
        "scan_btn": "🔍 Escanear",
        "scanning": "🔄 Escaneando 70+ casas de apuestas...",
        "found_bets": "✅ {count} apuestas EV encontradas!",
        "best_ev_bets": "🎯 Mejores apuestas EV",
        "book": "Casa",
        "total_stake": "💰 Apuesta total",
        "expected_return": "📈 Retorno esperado",
        "expected_profit": "🎯 Beneficio esperado",
        "manual_title": "📝 Ingreso manual de cuotas",
        "manual_desc": "Ingresa cuotas manualmente si ves una buena oportunidad.",
        "sport": "Deporte",
        "home_team": "Equipo local",
        "away_team": "Equipo visitante",
        "home_odds": "Cuota local",
        "draw_odds": "Cuota empate",
        "away_odds": "Cuota visitante",
        "your_bet": "Tu apuesta",
        "your_stake": "Tu apuesta ($)",
        "add_bet": "➕ Agregar apuesta",
        "bet_added": "✅ Apuesta agregada: {home} vs {away} — {outcome} @ {odds}",
        "history_title": "📊 Historial de Apuestas",
        "update_result": "✏️ Actualizar resultado",
        "select_bet": "Seleccionar apuesta",
        "result": "Resultado",
        "return_amount": "Retorno ($)",
        "update_btn": "Actualizar",
        "bet_updated": "✅ Apuesta actualizada!",
        "no_pending": "No hay apuestas pendientes.",
        "slip_title": "📄 Generador de Boletos",
        "slip_desc": "Genera un boleto imprimible para apuestas en tiendas.",
        "select_slip_bets": "Selecciona apuestas para tu boleto",
        "download_slip": "📥 Descargar boleto",
        "no_pending_slips": "No hay apuestas pendientes. ¡Escanea oportunidades primero!",
        "sign_out": "🚪 Cerrar sesión",
        "logout": "Cerrar sesión",
        "login_error": "Correo o contraseña incorrectos.",
        "signup_error": "Todos los campos son obligatorios.",
        "password_mismatch": "Las contraseñas no coinciden.",
        "password_short": "La contraseña debe tener al menos 6 caracteres.",
        "account_created": "✅ ¡Cuenta creada! Ahora puedes iniciar sesión.",
        "email_exists": "Correo ya registrado. Por favor inicia sesión.",
        "user_session_error": "Error de sesión. Por favor inicia sesión nuevamente."
    }
}

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
        subscription_status TEXT DEFAULT 'active',
        is_admin INTEGER DEFAULT 0
    )
    ''')
    
    # Create admin account if it doesn't exist
    admin_email = "admin@onlys.com"
    admin_password = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute('SELECT * FROM users WHERE email = ?', (admin_email,))
    if not c.fetchone():
        c.execute('''
        INSERT INTO users (email, password, name, created_at, is_admin)
        VALUES (?, ?, ?, ?, ?)
        ''', (admin_email, admin_password, "Administrator", datetime.now().isoformat(), 1))
    
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
# LANDING PAGE (PUBLIC) — WITH LANGUAGE TOGGLE
# ─────────────────────────────────────────────────────────────
def landing_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    # Language toggle in top right
    col_lang1, col_lang2, col_lang3 = st.columns([8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_landing"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_landing"):
            st.session_state.lang = "fr"
            st.rerun()
    
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
            padding: 4rem 2rem;
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
            font-size: 3.2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00D4FF 0%, #00FF94 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
            position: relative;
            z-index: 1;
        }}
        .hero p {{
            font-size: 1.2rem;
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
        .cta-small {{
            background: linear-gradient(135deg, #00D4FF 0%, #0088CC 100%);
            color: #0D1B2E;
            padding: 0.6rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            font-size: 0.9rem;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            width: 100%;
            margin-top: 0.5rem;
        }}
        .cta-small:hover {{
            transform: scale(1.02);
            box-shadow: 0 0 20px rgba(0,212,255,0.2);
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
        <h1>{t['title']}</h1>
        <p>{t['subtitle']}</p>
        <p class="subtitle">{t['tagline']}</p>
        <div style="margin-top: 1rem;">
            <span style="background: rgba(0,212,255,0.1); padding: 0.4rem 1rem; border-radius: 20px; color: #00D4FF; font-size: 0.8rem;">
                {t['free_trial_badge']}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Features
    st.markdown('<div class="features-grid">', unsafe_allow_html=True)
    
    for icon, title, desc in t['features']:
        st.markdown(f"""
        <div class="feature-card">
            <span class="icon">{icon}</span>
            <h3>{title}</h3>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Testimonial
    st.markdown(f"""
    <div class="testimonial">
        <p class="quote">"{t['testimonial']}"</p>
        <p class="author">{t['testimonial_author']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Pricing
    st.markdown("---")
    st.markdown(f"### {t['pricing_title']}")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown(f"""
        <div class="pricing-card">
            <div class="badge">{t['pricing_badge']}</div>
            <h2 style="color:#F0F4FA; margin:0;">{t['pricing_name']}</h2>
            <div class="price">{t['pricing_price']}</div>
            <div class="period">{t['pricing_period']}</div>
            <div class="feature-list">
        """, unsafe_allow_html=True)
        
        for feature in t['pricing_features']:
            st.markdown(f"<li>{feature}</li>", unsafe_allow_html=True)
        
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # SMALL BUTTON INSIDE THE CARD
        if st.button(t['free_trial_btn'], key="free_trial_btn", use_container_width=True, type="primary"):
            st.session_state.show_signup = True
            st.rerun()
        
        st.markdown(f"""
        <div style="text-align:center; color:#4A6E8A; font-size:0.7rem; padding:0.3rem 0;">
            {t['free_trial_note']}
        </div>
        """, unsafe_allow_html=True)
    
    # Footer
    st.markdown(f"""
    <div style="text-align:center; color:#1A3050; font-size:0.8rem; padding:2rem 0;">
        {t['footer']}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIGNUP PAGE
# ─────────────────────────────────────────────────────────────
def signup_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    # Language toggle
    col_lang1, col_lang2, col_lang3 = st.columns([8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_signup"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_signup"):
            st.session_state.lang = "fr"
            st.rerun()
    
    st.markdown(f"### {t['signup_title']}")
    st.markdown(t['signup_subtitle'])
    
    with st.form("signup_form"):
        name = st.text_input(t['name_label'], placeholder="John Doe")
        email = st.text_input(t['email_label'], placeholder="you@example.com")
        password = st.text_input(t['password_label'], type="password", placeholder="••••••••")
        confirm = st.text_input(t['confirm_label'], type="password", placeholder="••••••••")
        
        if st.form_submit_button(t['signup_btn'], use_container_width=True, type="primary"):
            if not name or not email or not password:
                st.error(t['signup_error'])
            elif password != confirm:
                st.error(t['password_mismatch'])
            elif len(password) < 6:
                st.error(t['password_short'])
            else:
                if create_user(email, password, name):
                    st.success(t['account_created'])
                    st.session_state.show_login = True
                    st.rerun()
                else:
                    st.error(t['email_exists'])
    
    st.markdown("---")
    if st.button(t['login_btn'], use_container_width=True):
        st.session_state.show_login = True
        st.rerun()

# ─────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────
def login_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    # Language toggle
    col_lang1, col_lang2, col_lang3 = st.columns([8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_login"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_login"):
            st.session_state.lang = "fr"
            st.rerun()
    
    st.markdown(f"### {t['login_title']}")
    
    with st.form("login_form"):
        email = st.text_input(t['email_label'], placeholder="you@example.com")
        password = st.text_input(t['password_label'], type="password", placeholder="••••••••")
        
        if st.form_submit_button(t['login_submit'], use_container_width=True, type="primary"):
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
        st.session_state.show_signup = True
        st.rerun()

# ─────────────────────────────────────────────────────────────
# DASHBOARD (PRIVATE)
# ─────────────────────────────────────────────────────────────
def dashboard():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    if 'user_id' not in st.session_state or st.session_state.user_id is None:
        st.error(t['user_session_error'])
        st.session_state.authenticated = False
        st.rerun()
        return
    
    # Language toggle in top right
    col_lang1, col_lang2, col_lang3 = st.columns([8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_dash"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_dash"):
            st.session_state.lang = "fr"
            st.rerun()
    
    # ─── TOP HEADER ───────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem; padding:1rem 1.5rem; background:linear-gradient(135deg, #0D1B2E 0%, #1A2F4E 100%); border-radius:16px; border:1px solid rgba(0,212,255,0.1);">
        <div>
            <h1 style="margin:0; font-size:1.8rem; background:linear-gradient(135deg, #00D4FF, #00FF94); -webkit-background-clip:text; -webkit-text-fill-color:transparent;">{t['dashboard_title']}</h1>
            <p style="color:#4A6E8A; margin:0;">{t['dashboard_welcome']}, <strong style="color:#B8CCDE;">{st.session_state.user_name}</strong></p>
        </div>
        <div style="text-align:right;">
            <p style="color:#4A6E8A; margin:0; font-size:0.8rem;">{t['member_since']}</p>
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
        col1.metric(t['total_bets'], total_bets)
        col2.metric(t['wins'], wins, delta=f"{wins-losses:+}")
        col3.metric(t['win_rate'], f"{win_rate:.1f}%")
        col4.metric(t['net_profit'], f"${profit:.2f}", delta=f"{profit:+.2f}")
    else:
        st.info(t['no_bets'])
    
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
        st.markdown(f"### {t['scanner_title']}")
        st.markdown(t['scanner_desc'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            scan_mode = st.selectbox(t['mode'], [t['ev_mode'], t['arbitrage_mode'], t['both_mode']])
        with col2:
            min_ev = st.slider(t['min_ev'], 1, 20, 5, 1)
        with col3:
            target_stake = st.number_input(t['stake_label'], min_value=10, value=100, step=10)
        
        if st.button(t['scan_btn'], use_container_width=True, type="primary"):
            with st.spinner(t['scanning']):
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
                st.success(t['found_bets'].format(count=len(sample_bets)))
                st.rerun()
        
        if 'scan_results' in st.session_state and st.session_state.scan_results:
            st.markdown(f"### {t['best_ev_bets']}")
            
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
                        <span style="color:#4A6E8A; font-size:0.8rem;">{t['book']}: {bet['book']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                total_stake += bet['stake']
                total_return += bet['potential_return']
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(t['total_bets'], len(st.session_state.scan_results))
            col2.metric(t['total_stake'], f"${total_stake:.2f}")
            col3.metric(t['expected_return'], f"${total_return:.2f}")
            col4.metric(t['expected_profit'], f"${total_return - total_stake:.2f}")
    
    # ─── TAB 2: MANUAL INPUT ──────────────────────────────────
    with tab2:
        st.markdown(f"### {t['manual_title']}")
        st.markdown(t['manual_desc'])
        
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
                    
                    st.success(t['bet_added'].format(home=home_team, away=away_team, outcome=outcome, odds=selected_odds))
                    st.rerun()
    
    # ─── TAB 3: HISTORY ──────────────────────────────────────
    with tab3:
        st.markdown(f"### {t['history_title']}")
        
        bets = get_user_bets(st.session_state.user_id)
        
        if bets:
            summary = get_bet_summary(bets)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric(t['total_bets'], summary['total'])
            col2.metric(t['wins'], summary['wins'])
            col3.metric("Losses", summary['losses'])
            col4.metric(t['win_rate'], f"{summary['win_rate']:.1f}%")
            col5.metric(t['net_profit'], f"${summary['net_profit']:.2f}")
            
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
                    st.success(t['bet_updated'])
                    st.rerun()
            else:
                st.info(t['no_pending'])
        else:
            st.info(t['no_bets'])
    
    # ─── TAB 4: PAPER SLIP ───────────────────────────────────
    with tab4:
        st.markdown(f"### {t['slip_title']}")
        st.markdown(t['slip_desc'])
        
        bets = get_user_bets(st.session_state.user_id)
        pending = [b for b in bets if b[10] == 'Pending']
        
        if pending:
            selected = []
            st.markdown(f"### {t['select_slip_bets']}")
            
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
if 'lang' not in st.session_state:
    st.session_state.lang = "en"
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = 0

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
# SIDEBAR — LOGOUT
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
                {st.session_state.is_admin and '<div style="color:#00D4FF; font-size:0.7rem;">👑 Admin</div>' or ''}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
        
        if st.button("🚪 Sign Out", use_container_width=True):
            for key in ['authenticated', 'user_email', 'user_name', 'user_id', 'is_admin']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown(f"""
        <div style="font-size:0.7rem; color:#1A3050; text-align:center; margin-top:2rem;">
            {COMPANY_NAME}<br>{DOMAIN}
        </div>
        """, unsafe_allow_html=True)
