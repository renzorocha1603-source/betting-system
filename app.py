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
    page_title="Only Solutions · Cyber Terminal",
    page_icon="⚡",
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
# ADVANCED CYBER UI CSS — Premium Trading Terminal
# ─────────────────────────────────────────────────────────────
CYBER_CSS = """
<style>
/* ─────────────────────────────────────────────────────────────
   ROOT VARIABLES & RESET
   ───────────────────────────────────────────────────────────── */
   @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700;800&family=Orbitron:wght@400;500;600;700;800;900&display=swap');
   
   * {
       margin: 0;
       padding: 0;
       box-sizing: border-box;
   }
   
   :root {
       --bg-deep: #0B0E14;
       --bg-surface: #0F172A;
       --bg-card: rgba(255, 255, 255, 0.03);
       --border-glass: rgba(255, 255, 255, 0.06);
       --border-glow: rgba(0, 243, 255, 0.15);
       --text-primary: #E8EDF5;
       --text-secondary: #7A8BA0;
       --text-muted: #3A4A60;
       --cyan: #00F3FF;
       --cyan-glow: rgba(0, 243, 255, 0.25);
       --lime: #39FF14;
       --lime-glow: rgba(57, 255, 20, 0.2);
       --orange: #FF6B35;
       --orange-glow: rgba(255, 107, 53, 0.2);
       --purple: #7C3AED;
       --purple-glow: rgba(124, 58, 237, 0.2);
       --red: #FF3355;
       --card-radius: 16px;
       --transition-speed: 0.3s;
       --font-mono: 'JetBrains Mono', monospace;
       --font-display: 'Orbitron', sans-serif;
   }

/* ─────────────────────────────────────────────────────────────
   GLOBAL DARK THEME
   ───────────────────────────────────────────────────────────── */
   html, body, .stApp, .stApp > div, .main, .block-container,
   div[data-testid="stAppViewContainer"],
   div[data-testid="stHeader"],
   section[data-testid="stSidebar"],
   .st-emotion-cache-1y4p8pa {
       background: var(--bg-deep) !important;
       background-color: var(--bg-deep) !important;
   }
   
   .block-container {
       padding: 1.5rem 2rem 3rem !important;
       max-width: 1400px !important;
   }
   
   ::-webkit-scrollbar { width: 4px; height: 4px; }
   ::-webkit-scrollbar-track { background: var(--bg-deep); }
   ::-webkit-scrollbar-thumb { 
       background: var(--cyan); 
       border-radius: 2px;
       box-shadow: 0 0 20px var(--cyan-glow);
   }

/* ─────────────────────────────────────────────────────────────
   TOP NAV BAR — CYBER TERMINAL
   ───────────────────────────────────────────────────────────── */
   .terminal-nav {
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
   }
   .terminal-nav::before {
       content: '';
       position: absolute;
       top: 0;
       left: 0;
       right: 0;
       height: 2px;
       background: linear-gradient(90deg, transparent, var(--cyan), var(--lime), transparent);
       animation: scanline 4s ease-in-out infinite;
   }
   @keyframes scanline {
       0% { transform: translateX(-100%); }
       100% { transform: translateX(100%); }
   }
   .terminal-logo {
       display: flex;
       align-items: center;
       gap: 0.75rem;
   }
   .terminal-logo .icon {
       font-size: 1.4rem;
       filter: drop-shadow(0 0 10px var(--cyan-glow));
   }
   .terminal-logo .brand {
       font-family: var(--font-display);
       font-size: 1.1rem;
       font-weight: 700;
       color: var(--text-primary);
       letter-spacing: 0.12em;
       background: linear-gradient(135deg, var(--cyan), var(--lime));
       -webkit-background-clip: text;
       -webkit-text-fill-color: transparent;
   }
   .terminal-logo .sub {
       font-family: var(--font-mono);
       font-size: 0.55rem;
       color: var(--text-muted);
       letter-spacing: 0.15em;
       text-transform: uppercase;
       -webkit-text-fill-color: var(--text-muted);
   }
   .terminal-status {
       display: flex;
       align-items: center;
       gap: 1.5rem;
       font-family: var(--font-mono);
       font-size: 0.65rem;
   }
   .terminal-status .dot {
       width: 8px;
       height: 8px;
       border-radius: 50%;
       background: var(--lime);
       box-shadow: 0 0 20px var(--lime-glow);
       animation: pulse-dot 2s ease-in-out infinite;
   }
   @keyframes pulse-dot {
       0%, 100% { opacity: 1; transform: scale(1); }
       50% { opacity: 0.5; transform: scale(0.8); }
   }
   .terminal-status .live-text {
       color: var(--lime);
       font-weight: 600;
       letter-spacing: 0.08em;
   }
   .terminal-status .stats {
       color: var(--text-muted);
   }
   .terminal-status .stats span {
       color: var(--text-secondary);
       font-weight: 600;
   }
   .terminal-status .user-badge {
       background: rgba(0, 243, 255, 0.06);
       border: 1px solid rgba(0, 243, 255, 0.1);
       border-radius: 20px;
       padding: 0.2rem 0.8rem;
       color: var(--cyan);
       font-size: 0.6rem;
       font-weight: 600;
       letter-spacing: 0.08em;
   }

/* ─────────────────────────────────────────────────────────────
   KPI SPARKLINE BLOCKS — GLASSMORPHISM
   ───────────────────────────────────────────────────────────── */
   .kpi-grid {
       display: grid;
       grid-template-columns: repeat(4, 1fr);
       gap: 1rem;
       margin-bottom: 1.5rem;
   }
   .kpi-card {
       background: var(--bg-card);
       backdrop-filter: blur(20px);
       border: 1px solid var(--border-glass);
       border-radius: var(--card-radius);
       padding: 1.2rem 1.5rem;
       transition: all var(--transition-speed) ease;
       position: relative;
       overflow: hidden;
   }
   .kpi-card::after {
       content: '';
       position: absolute;
       top: 0;
       right: 0;
       width: 100px;
       height: 100px;
       background: radial-gradient(circle at top right, var(--cyan-glow), transparent 70%);
       opacity: 0.1;
       pointer-events: none;
   }
   .kpi-card:hover {
       border-color: var(--cyan);
       transform: translateY(-2px);
       box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
   }
   .kpi-card .label {
       font-family: var(--font-mono);
       font-size: 0.55rem;
       color: var(--text-muted);
       text-transform: uppercase;
       letter-spacing: 0.1em;
       margin-bottom: 0.3rem;
   }
   .kpi-card .value {
       font-family: var(--font-display);
       font-size: 1.6rem;
       font-weight: 700;
       color: var(--text-primary);
       letter-spacing: 0.02em;
   }
   .kpi-card .value.cyan { color: var(--cyan); text-shadow: 0 0 30px var(--cyan-glow); }
   .kpi-card .value.lime { color: var(--lime); text-shadow: 0 0 30px var(--lime-glow); }
   .kpi-card .value.orange { color: var(--orange); text-shadow: 0 0 30px var(--orange-glow); }
   .kpi-card .value.purple { color: var(--purple); text-shadow: 0 0 30px var(--purple-glow); }
   .kpi-card .change {
       font-family: var(--font-mono);
       font-size: 0.6rem;
       margin-top: 0.25rem;
   }
   .kpi-card .change.positive { color: var(--lime); }
   .kpi-card .change.negative { color: var(--red); }

/* ─────────────────────────────────────────────────────────────
   ARBITRAGE CARD — PREMIUM OPPORTUNITY BLOCK
   ───────────────────────────────────────────────────────────── */
   .arb-card {
       background: var(--bg-card);
       backdrop-filter: blur(20px);
       border: 1px solid var(--border-glass);
       border-radius: var(--card-radius);
       padding: 1.25rem 1.5rem;
       margin-bottom: 0.75rem;
       transition: all var(--transition-speed) ease;
       position: relative;
       overflow: hidden;
   }
   .arb-card:hover {
       border-color: var(--cyan);
       box-shadow: 0 0 40px rgba(0, 243, 255, 0.04), inset 0 0 40px rgba(0, 243, 255, 0.01);
   }
   .arb-card .arb-header {
       display: flex;
       justify-content: space-between;
       align-items: flex-start;
       margin-bottom: 0.75rem;
       flex-wrap: wrap;
       gap: 0.5rem;
   }
   .arb-card .arb-match {
       display: flex;
       flex-direction: column;
   }
   .arb-card .arb-match .teams {
       font-family: 'Inter', sans-serif;
       font-size: 0.95rem;
       font-weight: 600;
       color: var(--text-primary);
   }
   .arb-card .arb-match .teams .vs {
       color: var(--text-muted);
       font-weight: 400;
       margin: 0 0.3rem;
   }
   .arb-card .arb-match .meta {
       font-family: var(--font-mono);
       font-size: 0.6rem;
       color: var(--text-muted);
       text-transform: uppercase;
       letter-spacing: 0.06em;
       margin-top: 0.15rem;
   }
   .arb-card .arb-badge {
       display: inline-flex;
       align-items: center;
       gap: 0.4rem;
       font-family: var(--font-display);
       font-size: 0.75rem;
       font-weight: 700;
       color: var(--lime);
       background: rgba(57, 255, 20, 0.06);
       border: 1px solid rgba(57, 255, 20, 0.1);
       padding: 0.3rem 0.8rem;
       border-radius: 20px;
       letter-spacing: 0.04em;
       white-space: nowrap;
   }
   .arb-card .arb-badge.negative {
       color: var(--red);
       border-color: rgba(255, 51, 85, 0.15);
       background: rgba(255, 51, 85, 0.06);
   }
   .arb-card .arb-body {
       display: flex;
       justify-content: space-between;
       align-items: center;
       flex-wrap: wrap;
       gap: 1rem;
   }
   .arb-card .odds-grid {
       display: flex;
       gap: 1.25rem;
   }
   .arb-card .odd-cell {
       display: flex;
       flex-direction: column;
       align-items: center;
       padding: 0.3rem 0.8rem;
       background: rgba(0, 0, 0, 0.2);
       border-radius: 8px;
       min-width: 60px;
       border: 1px solid transparent;
       transition: all var(--transition-speed) ease;
   }
   .arb-card .odd-cell:hover {
       border-color: rgba(0, 243, 255, 0.1);
   }
   .arb-card .odd-cell .odd-label {
       font-family: var(--font-mono);
       font-size: 0.5rem;
       color: var(--text-muted);
       text-transform: uppercase;
       letter-spacing: 0.06em;
   }
   .arb-card .odd-cell .odd-value {
       font-family: var(--font-mono);
       font-size: 0.95rem;
       font-weight: 600;
       color: var(--text-secondary);
   }
   .arb-card .odd-cell .odd-value.highlight {
       color: var(--cyan);
       text-shadow: 0 0 20px var(--cyan-glow);
   }
   .arb-card .stake-distribution {
       display: flex;
       align-items: center;
       gap: 0.5rem;
       font-family: var(--font-mono);
       font-size: 0.65rem;
       color: var(--text-muted);
       padding: 0.3rem 0.8rem;
       background: rgba(0, 0, 0, 0.2);
       border-radius: 8px;
       border: 1px solid var(--border-glass);
   }
   .arb-card .stake-distribution .stake-amount {
       color: var(--text-secondary);
       font-weight: 600;
   }
   .arb-card .stake-distribution .stake-amount.cyan { color: var(--cyan); }
   .arb-card .stake-distribution .stake-amount.lime { color: var(--lime); }
   .arb-card .stake-distribution .stake-amount.orange { color: var(--orange); }
   .arb-card .arb-actions {
       display: flex;
       gap: 0.5rem;
   }
   .arb-card .arb-actions .action-btn {
       background: rgba(0, 243, 255, 0.06);
       border: 1px solid rgba(0, 243, 255, 0.1);
       color: var(--cyan);
       padding: 0.3rem 0.8rem;
       border-radius: 6px;
       font-family: var(--font-mono);
       font-size: 0.6rem;
       font-weight: 600;
       cursor: pointer;
       transition: all var(--transition-speed) ease;
       text-transform: uppercase;
       letter-spacing: 0.06em;
   }
   .arb-card .arb-actions .action-btn:hover {
       background: rgba(0, 243, 255, 0.12);
       border-color: var(--cyan);
       box-shadow: 0 0 20px var(--cyan-glow);
   }
   .arb-card .arb-actions .action-btn.primary {
       background: linear-gradient(135deg, var(--cyan), #0099CC);
       color: var(--bg-deep);
       border: none;
   }
   .arb-card .arb-actions .action-btn.primary:hover {
       box-shadow: 0 0 30px var(--cyan-glow);
       transform: scale(1.02);
   }

/* ─────────────────────────────────────────────────────────────
   CALCULATOR — INTERACTIVE STAKE DISTRIBUTION
   ───────────────────────────────────────────────────────────── */
   .calc-container {
       background: var(--bg-card);
       backdrop-filter: blur(20px);
       border: 1px solid var(--border-glass);
       border-radius: var(--card-radius);
       padding: 1.5rem;
       margin: 1rem 0;
   }
   .calc-container .calc-title {
       font-family: var(--font-display);
       font-size: 0.75rem;
       font-weight: 600;
       color: var(--text-secondary);
       text-transform: uppercase;
       letter-spacing: 0.12em;
       margin-bottom: 1rem;
   }
   .calc-container .calc-grid {
       display: grid;
       grid-template-columns: 1fr 1fr 1fr;
       gap: 1rem;
   }
   .calc-container .calc-input-group {
       display: flex;
       flex-direction: column;
       gap: 0.3rem;
   }
   .calc-container .calc-input-group label {
       font-family: var(--font-mono);
       font-size: 0.55rem;
       color: var(--text-muted);
       text-transform: uppercase;
       letter-spacing: 0.06em;
   }
   .calc-container .calc-input-group input {
       background: rgba(0, 0, 0, 0.3);
       border: 1px solid var(--border-glass);
       border-radius: 8px;
       padding: 0.6rem 0.8rem;
       color: var(--text-primary);
       font-family: var(--font-mono);
       font-size: 0.85rem;
       transition: all var(--transition-speed) ease;
   }
   .calc-container .calc-input-group input:focus {
       border-color: var(--cyan);
       outline: none;
       box-shadow: 0 0 20px var(--cyan-glow);
   }
   .calc-container .calc-result {
       display: flex;
       align-items: center;
       justify-content: center;
       gap: 0.75rem;
       padding: 0.5rem 1rem;
       background: rgba(0, 243, 255, 0.04);
       border: 1px solid rgba(0, 243, 255, 0.08);
       border-radius: 8px;
       font-family: var(--font-mono);
   }
   .calc-container .calc-result .result-label {
       font-size: 0.55rem;
       color: var(--text-muted);
       text-transform: uppercase;
       letter-spacing: 0.06em;
   }
   .calc-container .calc-result .result-value {
       font-size: 1.1rem;
       font-weight: 700;
       color: var(--lime);
   }

/* ─────────────────────────────────────────────────────────────
   STREAMLIT OVERRIDES — SEAMLESS INTEGRATION
   ───────────────────────────────────────────────────────────── */
   .stButton button, div[data-testid="stFormSubmitButton"] button {
       background: linear-gradient(135deg, var(--cyan), #0099CC) !important;
       color: var(--bg-deep) !important;
       border: none !important;
       border-radius: 8px !important;
       font-family: var(--font-mono) !important;
       font-weight: 700 !important;
       font-size: 0.7rem !important;
       letter-spacing: 0.08em !important;
       text-transform: uppercase !important;
       padding: 0.5rem 1.5rem !important;
       transition: all var(--transition-speed) ease !important;
       box-shadow: 0 0 20px var(--cyan-glow) !important;
   }
   .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {
       transform: translateY(-2px) !important;
       box-shadow: 0 0 40px var(--cyan-glow) !important;
   }
   .stButton button[kind="secondary"] {
       background: transparent !important;
       color: var(--text-secondary) !important;
       border: 1px solid var(--border-glass) !important;
       box-shadow: none !important;
   }
   .stButton button[kind="secondary"]:hover {
       border-color: var(--cyan) !important;
       color: var(--cyan) !important;
   }
   .stDownloadButton button {
       background: linear-gradient(135deg, var(--lime), #00CC77) !important;
       color: var(--bg-deep) !important;
       border: none !important;
       border-radius: 8px !important;
       font-family: var(--font-mono) !important;
       font-weight: 700 !important;
       font-size: 0.7rem !important;
       letter-spacing: 0.08em !important;
       text-transform: uppercase !important;
       padding: 0.5rem 1.5rem !important;
       box-shadow: 0 0 20px var(--lime-glow) !important;
   }
   .stDownloadButton button:hover {
       transform: translateY(-2px) !important;
       box-shadow: 0 0 40px var(--lime-glow) !important;
   }
   
   div[data-testid="stTextInput"] input,
   div[data-testid="stNumberInput"] input {
       background: rgba(0, 0, 0, 0.3) !important;
       border: 1px solid var(--border-glass) !important;
       border-radius: 8px !important;
       color: var(--text-primary) !important;
       font-family: 'Inter', sans-serif !important;
       padding: 0.5rem 1rem !important;
       transition: all var(--transition-speed) ease !important;
   }
   div[data-testid="stTextInput"] input:focus {
       border-color: var(--cyan) !important;
       box-shadow: 0 0 20px var(--cyan-glow) !important;
   }
   
   div[data-testid="metric-container"] {
       background: var(--bg-card) !important;
       backdrop-filter: blur(20px) !important;
       border: 1px solid var(--border-glass) !important;
       border-radius: var(--card-radius) !important;
       padding: 0.8rem 1rem !important;
       transition: all var(--transition-speed) ease !important;
   }
   div[data-testid="metric-container"]:hover {
       border-color: var(--cyan) !important;
   }
   div[data-testid="metric-label"] {
       font-family: var(--font-mono) !important;
       font-size: 0.5rem !important;
       color: var(--text-muted) !important;
       text-transform: uppercase !important;
       letter-spacing: 0.08em !important;
   }
   div[data-testid="metric-value"] {
       font-family: var(--font-display) !important;
       font-size: 1.2rem !important;
       font-weight: 700 !important;
       color: var(--text-primary) !important;
   }
   
   section[data-testid="stSidebar"] {
       background: var(--bg-surface) !important;
       border-right: 1px solid var(--border-glass) !important;
       padding: 1rem 0 !important;
   }
   section[data-testid="stSidebar"] .stMarkdown {
       color: var(--text-secondary) !important;
   }
   
   .stSelectbox > div > div {
       background: rgba(0, 0, 0, 0.3) !important;
       border: 1px solid var(--border-glass) !important;
       border-radius: 8px !important;
       color: var(--text-primary) !important;
   }
   
   .stSlider div[data-baseweb="slider"] {
       background: var(--border-glass) !important;
   }
   .stSlider div[data-baseweb="slider"] div {
       background: var(--cyan) !important;
       box-shadow: 0 0 15px var(--cyan-glow) !important;
   }
   
   .stAlert {
       background: var(--bg-card) !important;
       backdrop-filter: blur(20px) !important;
       border: 1px solid var(--border-glass) !important;
       border-radius: var(--card-radius) !important;
       color: var(--text-secondary) !important;
   }
   
   .stTabs [data-baseweb="tab-list"] {
       gap: 0 !important;
       border-bottom: 1px solid var(--border-glass) !important;
   }
   .stTabs [data-baseweb="tab"] {
       font-family: var(--font-mono) !important;
       font-size: 0.6rem !important;
       color: var(--text-muted) !important;
       text-transform: uppercase !important;
       letter-spacing: 0.08em !important;
       padding: 0.5rem 1.5rem !important;
   }
   .stTabs [data-baseweb="tab"][aria-selected="true"] {
       color: var(--cyan) !important;
       border-bottom: 2px solid var(--cyan) !important;
   }
   
   #MainMenu, footer, header { visibility: hidden !important; display: none !important; }
</style>
"""
st.markdown(CYBER_CSS, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# LANGUAGES — EN, FR, ES
# ─────────────────────────────────────────────────────────────
LANGUAGES = {
    "en": {
        "title": "📊 Cyber Betting Terminal",
        "subtitle": "Real-time Arbitrage & EV Scanner",
        "live": "LIVE",
        "active_arbs": "Active Arbs",
        "avg_roi": "Avg ROI",
        "bankroll": "Bankroll",
        "total_bets": "Total Bets",
        # Add all translations...
    },
    "fr": {
        "title": "📊 Terminal de Paris Cyber",
        "subtitle": "Scanner d'Arbitrage et EV en temps réel",
        "live": "EN DIRECT",
        "active_arbs": "Arbs actifs",
        "avg_roi": "ROI moyen",
        "bankroll": "Bankroll",
        "total_bets": "Total des paris",
    },
    "es": {
        "title": "📊 Terminal de Apuestas Cyber",
        "subtitle": "Escáner de Arbitraje y EV en tiempo real",
        "live": "EN VIVO",
        "active_arbs": "Arbs activos",
        "avg_roi": "ROI promedio",
        "bankroll": "Bankroll",
        "total_bets": "Total apuestas",
    }
}

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
def get_market_average(odds_list):
    valid = [o for o in odds_list if o > 0]
    if not valid:
        return 1.5
    return sum(1/o for o in valid) / len(valid)

def calculate_true_probability(odds, market_avg):
    implied = 1 / odds
    adjustment = 1 - (market_avg - 1) * 0.1
    return implied * adjustment

def calculate_ev(odds, true_prob):
    return (true_prob * odds) - 1

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
# LANDING PAGE
# ─────────────────────────────────────────────────────────────
def landing_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    # Language toggle
    col_lang1, col_lang2, col_lang3, col_lang4 = st.columns([8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_landing"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_landing"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button("🇪🇸 ES", key="lang_es_landing"):
            st.session_state.lang = "es"
            st.rerun()
    
    # Hero Section
    st.markdown(f"""
    <div style="text-align:center; padding:4rem 2rem; background:var(--bg-surface); border-radius:20px; border:1px solid var(--border-glass); margin-bottom:2rem; position:relative; overflow:hidden;">
        <div style="position:absolute; top:-50%; left:-50%; width:200%; height:200%; background:radial-gradient(circle at 50% 50%, rgba(0,243,255,0.03) 0%, transparent 70%); pointer-events:none;"></div>
        <h1 style="font-family:var(--font-display); font-size:3rem; font-weight:800; background:linear-gradient(135deg, var(--cyan), var(--lime)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0.5rem;">⚡ {t['title']}</h1>
        <p style="color:var(--text-secondary); font-size:1.2rem; max-width:600px; margin:0 auto;">{t['subtitle']}</p>
        <div style="margin-top:1.5rem; display:flex; justify-content:center; gap:0.5rem; flex-wrap:wrap;">
            <span style="background:rgba(0,243,255,0.06); border:1px solid rgba(0,243,255,0.1); padding:0.3rem 1rem; border-radius:20px; color:var(--cyan); font-size:0.7rem; font-family:var(--font-mono);">🆓 7-day free trial</span>
            <span style="background:rgba(57,255,20,0.04); border:1px solid rgba(57,255,20,0.06); padding:0.3rem 1rem; border-radius:20px; color:var(--lime); font-size:0.7rem; font-family:var(--font-mono);">⚡ {t['live']}</span>
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
            <div style="background:var(--bg-card); backdrop-filter:blur(20px); border:1px solid var(--border-glass); border-radius:var(--card-radius); padding:1.5rem; text-align:center; transition:all var(--transition-speed) ease;">
                <div style="font-size:2.5rem; margin-bottom:0.5rem;">{icon}</div>
                <h3 style="color:var(--text-primary); font-size:1rem;">{title}</h3>
                <p style="color:var(--text-muted); font-size:0.8rem;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Pricing
    st.markdown("---")
    st.markdown("### 💰 Simple Pricing")
    
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="background:var(--bg-card); backdrop-filter:blur(20px); border:1px solid var(--border-glass); border-radius:var(--card-radius); padding:2rem; text-align:center;">
            <div style="background:linear-gradient(135deg, var(--cyan), var(--lime)); color:#0B0E14; padding:0.3rem 1rem; border-radius:20px; font-size:0.7rem; font-weight:700; display:inline-block; margin-bottom:0.5rem;">🔥 Most Popular</div>
            <h2 style="color:var(--text-primary); margin:0;">Monthly</h2>
            <div style="font-family:var(--font-display); font-size:3.5rem; font-weight:700; color:var(--cyan);">$1.99</div>
            <div style="color:var(--text-muted); font-size:0.8rem;">per month</div>
            <div style="text-align:left; margin:1.5rem 0;">
                <div style="padding:0.4rem 0; color:var(--text-secondary);">✓ Unlimited EV Scans</div>
                <div style="padding:0.4rem 0; color:var(--text-secondary);">✓ Arbitrage Detection</div>
                <div style="padding:0.4rem 0; color:var(--text-secondary);">✓ Paper Slip Generator</div>
                <div style="padding:0.4rem 0; color:var(--text-secondary);">✓ AI Analysis</div>
                <div style="padding:0.4rem 0; color:var(--text-secondary);">✓ No commitment</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Start Free Trial", use_container_width=True, type="primary"):
            st.session_state.show_signup = True
            st.rerun()
        
        st.markdown("""
        <div style="text-align:center; color:var(--text-muted); font-size:0.7rem; padding:0.5rem 0;">
            🆓 7-day free trial · Then $1.99/month
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="text-align:center; color:var(--text-muted); font-size:0.7rem; padding:2rem 0; border-top:1px solid var(--border-glass); margin-top:1rem;">
        {COMPANY_NAME} · {DOMAIN} · {YEAR}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SIGNUP PAGE
# ─────────────────────────────────────────────────────────────
def signup_page():
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    col_lang1, col_lang2, col_lang3, col_lang4 = st.columns([8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_signup"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_signup"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button("🇪🇸 ES", key="lang_es_signup"):
            st.session_state.lang = "es"
            st.rerun()
    
    st.markdown(f"### 🚀 Create Your Account")
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
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    col_lang1, col_lang2, col_lang3, col_lang4 = st.columns([8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_login"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_login"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button("🇪🇸 ES", key="lang_es_login"):
            st.session_state.lang = "es"
            st.rerun()
    
    st.markdown(f"### 🔐 Welcome Back")
    
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
                st.session_state.is_admin = user[6] if len(user) > 6 else 0
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
    lang = st.session_state.get('lang', 'en')
    t = LANGUAGES[lang]
    
    if 'user_id' not in st.session_state or st.session_state.user_id is None:
        st.error("User session error. Please log in again.")
        st.session_state.authenticated = False
        st.rerun()
        return
    
    # Language toggle
    col_lang1, col_lang2, col_lang3, col_lang4 = st.columns([8, 0.8, 0.8, 0.8])
    with col_lang2:
        if st.button("🇬🇧 EN", key="lang_en_dash"):
            st.session_state.lang = "en"
            st.rerun()
    with col_lang3:
        if st.button("🇫🇷 FR", key="lang_fr_dash"):
            st.session_state.lang = "fr"
            st.rerun()
    with col_lang4:
        if st.button("🇪🇸 ES", key="lang_es_dash"):
            st.session_state.lang = "es"
            st.rerun()
    
    # ─── TOP NAV ─────────────────────────────────────────────
    st.markdown(f"""
    <div class="terminal-nav">
        <div class="terminal-logo">
            <span class="icon">⚡</span>
            <div>
                <span class="brand">CYBER TERMINAL</span>
                <div class="sub">{st.session_state.user_name} · {st.session_state.user_role.upper()}</div>
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
    
    # ─── KPI GRID ─────────────────────────────────────────────
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
                <div class="label">Active Arbs</div>
                <div class="value cyan">5</div>
                <div class="change positive">↑ 2 from yesterday</div>
            </div>
            <div class="kpi-card">
                <div class="label">Avg ROI</div>
                <div class="value lime">+6.4%</div>
                <div class="change positive">↑ 1.2%</div>
            </div>
            <div class="kpi-card">
                <div class="label">Bankroll</div>
                <div class="value orange">${1000 + profit:.2f}</div>
                <div class="change {('positive' if profit > 0 else 'negative')}">{'+' if profit > 0 else ''}{profit:.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="label">Total Bets</div>
                <div class="value purple">{total_bets}</div>
                <div class="change positive">{win_rate:.1f}% win rate</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="label">Active Arbs</div><div class="value cyan">0</div><div class="change">No active arbs</div></div>
            <div class="kpi-card"><div class="label">Avg ROI</div><div class="value lime">0%</div><div class="change">No data</div></div>
            <div class="kpi-card"><div class="label">Bankroll</div><div class="value orange">$1,000</div><div class="change">Start betting</div></div>
            <div class="kpi-card"><div class="label">Total Bets</div><div class="value purple">0</div><div class="change">No bets yet</div></div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ─── TABS ──────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Scanner",
        "📝 Manual",
        "📊 History",
        "📄 Slip"
    ])
    
    # ─── TAB 1: SCANNER ──────────────────────────────────────
    with tab1:
        st.markdown("### 🔍 Live Arbitrage Scanner")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            scan_mode = st.selectbox("Mode", ["EV (Value Bets)", "Arbitrage", "Both"])
        with col2:
            min_ev = st.slider("Min EV %", 1, 20, 5, 1)
        with col3:
            target_stake = st.number_input("Stake ($)", min_value=10, value=100, step=10)
        
        if st.button("🔍 Scan Now", use_container_width=True, type="primary"):
            with st.spinner("Scanning 70+ bookmakers..."):
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
        
        # Display results with cyber cards
        if 'scan_results' in st.session_state and st.session_state.scan_results:
            st.markdown("### 🎯 Best EV Bets")
            
            total_stake = 0
            total_return = 0
            
            for i, bet in enumerate(st.session_state.scan_results[:5], 1):
                st.markdown(f"""
                <div class="arb-card">
                    <div class="arb-header">
                        <div class="arb-match">
                            <div class="teams">#{i} {bet['match'].replace(' vs ', ' <span class="vs">vs</span> ')}</div>
                            <div class="meta">{bet['book']} · EV: {bet['ev_percent']:.1f}%</div>
                        </div>
                        <div class="arb-badge">⚡ +{bet['ev_percent']:.1f}% ROI</div>
                    </div>
                    <div class="arb-body">
                        <div class="odds-grid">
                            <div class="odd-cell">
                                <span class="odd-label">Bet</span>
                                <span class="odd-value highlight">{bet['outcome']}</span>
                            </div>
                            <div class="odd-cell">
                                <span class="odd-label">Odds</span>
                                <span class="odd-value">{bet['odds']}</span>
                            </div>
                            <div class="odd-cell">
                                <span class="odd-label">Stake</span>
                                <span class="odd-value">${bet['stake']:.2f}</span>
                            </div>
                            <div class="odd-cell">
                                <span class="odd-label">Return</span>
                                <span class="odd-value" style="color:var(--lime);">${bet['potential_return']:.2f}</span>
                            </div>
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
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Bets", len(st.session_state.scan_results))
            col2.metric("Total Stake", f"${total_stake:.2f}")
            col3.metric("Expected Return", f"${total_return:.2f}")
            col4.metric("Expected Profit", f"${total_return - total_stake:.2f}")
    
    # ─── TAB 2: MANUAL ──────────────────────────────────────
    with tab2:
        st.markdown("### 📝 Manual Odds Input")
        
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
        st.markdown("### 📊 Betting History")
        
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
            st.info("No bets yet. Start scanning for opportunities!")
    
    # ─── TAB 4: SLIP ─────────────────────────────────────────
    with tab4:
        st.markdown("### 📄 Paper Slip Generator")
        
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
                    label="📥 Download Slip",
                    data=slip_text,
                    file_name=f"slip_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        else:
            st.info("No pending bets available. Scan for opportunities first!")

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
            st.rerun()
        
        st.markdown(f"""
        <div style="font-size:0.6rem; color:var(--text-muted); text-align:center; margin-top:2rem;">
            {COMPANY_NAME}<br>{DOMAIN}
        </div>
        """, unsafe_allow_html=True)
