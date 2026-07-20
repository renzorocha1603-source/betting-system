# ─────────────────────────────────────────────────────────────
# CUSTOM CSS — Futuristic Cyber-Neon Dashboard Skin
# ─────────────────────────────────────────────────────────────
def get_custom_css():
    return """
    <style>
    /* ─────────────────────────────────────────────────────────
       GLOBAL RESET & DARK THEME
    ───────────────────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    /* Force dark background everywhere */
    html, body, .stApp, .stApp > div, .main, .block-container,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stHeader"],
    section[data-testid="stSidebar"],
    .st-emotion-cache-1y4p8pa {
        background: #0A0D14 !important;
        background-color: #0A0D14 !important;
    }
    
    /* Root variables */
    :root {
        --bg-primary: #0A0D14;
        --bg-secondary: #111827;
        --bg-card: #141C2B;
        --bg-input: #0D1520;
        --border-color: #1E2D45;
        --border-glow: rgba(0, 212, 255, 0.15);
        --text-primary: #E8EDF5;
        --text-secondary: #7A8BA0;
        --text-muted: #4A5A70;
        --cyan: #00D4FF;
        --cyan-glow: rgba(0, 212, 255, 0.3);
        --cyan-dark: #0099CC;
        --green: #00FF94;
        --green-glow: rgba(0, 255, 148, 0.2);
        --orange: #FF6B35;
        --orange-glow: rgba(255, 107, 53, 0.25);
        --purple: #7C3AED;
        --purple-glow: rgba(124, 58, 237, 0.25);
        --red: #FF3355;
        --card-radius: 12px;
        --transition-speed: 0.3s;
    }
    
    /* ─────────────────────────────────────────────────────────
       SCROLLBAR
    ───────────────────────────────────────────────────────── */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0A0D14;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00D4FF, #0099CC);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #00D4FF;
    }
    
    /* ─────────────────────────────────────────────────────────
       TOP BANNER — Scanner Status
    ───────────────────────────────────────────────────────── */
    .scanner-banner {
        background: linear-gradient(135deg, #111827 0%, #0D1520 100%);
        border: 1px solid #1E2D45;
        border-radius: 12px;
        padding: 0.8rem 1.5rem;
        margin-bottom: 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        position: relative;
        overflow: hidden;
    }
    .scanner-banner::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00D4FF, #00FF94, transparent);
        animation: scanline 3s ease-in-out infinite;
    }
    @keyframes scanline {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    .scanner-status {
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #00FF94;
        box-shadow: 0 0 20px rgba(0, 255, 148, 0.4);
        animation: pulse-dot 2s ease-in-out infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(0.8); }
    }
    .status-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 600;
        color: #00FF94;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .status-metrics {
        display: flex;
        gap: 2rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #7A8BA0;
    }
    .status-metrics span {
        color: #E8EDF5;
    }
    
    /* ─────────────────────────────────────────────────────────
       CYBER CARDS
    ───────────────────────────────────────────────────────── */
    .cyber-card {
        background: linear-gradient(145deg, #111827, #0D1520);
        border: 1px solid #1E2D45;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .cyber-card:hover {
        border-color: #00D4FF;
        box-shadow: 0 0 30px rgba(0, 212, 255, 0.05), inset 0 0 30px rgba(0, 212, 255, 0.02);
        transform: translateY(-2px);
    }
    .cyber-card::after {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle at top right, rgba(0, 212, 255, 0.03), transparent 70%);
        pointer-events: none;
    }
    .cyber-card .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #4A5A70;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .cyber-card .card-header .badge {
        background: rgba(0, 212, 255, 0.1);
        color: #00D4FF;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.6rem;
        border: 1px solid rgba(0, 212, 255, 0.15);
    }
    
    /* ─────────────────────────────────────────────────────────
       GLOWING METRICS
    ───────────────────────────────────────────────────────── */
    .metric-glow {
        display: flex;
        flex-direction: column;
        padding: 0.75rem 1rem;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 8px;
        border-left: 2px solid var(--cyan);
    }
    .metric-glow .label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.6rem;
        color: #4A5A70;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-glow .value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 700;
        color: #E8EDF5;
    }
    .metric-glow .value.cyan { color: #00D4FF; }
    .metric-glow .value.green { color: #00FF94; }
    .metric-glow .value.orange { color: #FF6B35; }
    .metric-glow .value.purple { color: #7C3AED; }
    
    /* ─────────────────────────────────────────────────────────
       DATA BLOCKS — Arbitrage Opportunities
    ───────────────────────────────────────────────────────── */
    .arb-block {
        background: linear-gradient(145deg, #111827, #0D1520);
        border: 1px solid #1E2D45;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        transition: all 0.3s ease;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.75rem;
    }
    .arb-block:hover {
        border-color: #00D4FF;
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.06);
    }
    .arb-block .match-info {
        display: flex;
        flex-direction: column;
        flex: 1;
        min-width: 150px;
    }
    .arb-block .match-info .teams {
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        font-weight: 600;
        color: #E8EDF5;
    }
    .arb-block .match-info .teams .vs {
        color: #4A5A70;
        font-weight: 400;
        margin: 0 0.4rem;
    }
    .arb-block .match-info .league {
        font-size: 0.65rem;
        color: #4A5A70;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .arb-block .odds-display {
        display: flex;
        gap: 1.25rem;
        align-items: center;
    }
    .arb-block .odds-display .odd-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 0.2rem 0.6rem;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 6px;
        min-width: 50px;
    }
    .arb-block .odds-display .odd-item .odd-label {
        font-size: 0.5rem;
        color: #4A5A70;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.06em;
    }
    .arb-block .odds-display .odd-item .odd-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.95rem;
        font-weight: 600;
        color: #E8EDF5;
    }
    .arb-block .odds-display .odd-item .odd-value.highlight {
        color: #00D4FF;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
    }
    .arb-block .profit-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        font-weight: 700;
        color: #00FF94;
        background: rgba(0, 255, 148, 0.1);
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        border: 1px solid rgba(0, 255, 148, 0.15);
        white-space: nowrap;
    }
    .arb-block .profit-badge.negative {
        color: #FF3355;
        border-color: rgba(255, 51, 85, 0.15);
        background: rgba(255, 51, 85, 0.08);
    }
    
    /* ─────────────────────────────────────────────────────────
       STREAMLIT OVERRIDES
    ───────────────────────────────────────────────────────── */
    /* Input fields */
    .stTextInput input, .stNumberInput input, .stSelectbox select,
    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {
        background: #0D1520 !important;
        border: 1px solid #1E2D45 !important;
        border-radius: 8px !important;
        color: #E8EDF5 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 0.6rem 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus,
    div[data-testid="stTextInput"] input:focus {
        border-color: #00D4FF !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.08), inset 0 0 20px rgba(0, 212, 255, 0.02) !important;
        outline: none !important;
    }
    
    /* Labels */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    div[data-testid="stTextInput"] label {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.6rem !important;
        color: #4A5A70 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }
    
    /* Buttons */
    .stButton button, div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #00D4FF, #0099CC) !important;
        color: #0A0D14 !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s ease !important;
        cursor: pointer !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.15) !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .stButton button:hover, div[data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 40px rgba(0, 212, 255, 0.25) !important;
    }
    .stButton button:active, div[data-testid="stFormSubmitButton"] button:active {
        transform: scale(0.98) !important;
    }
    /* Secondary / danger buttons */
    .stButton button[kind="secondary"] {
        background: transparent !important;
        color: #7A8BA0 !important;
        border: 1px solid #1E2D45 !important;
        box-shadow: none !important;
    }
    .stButton button[kind="secondary"]:hover {
        border-color: #00D4FF !important;
        color: #00D4FF !important;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.05) !important;
    }
    /* Download button */
    .stDownloadButton button {
        background: linear-gradient(135deg, #00FF94, #00CC77) !important;
        color: #0A0D14 !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 0 20px rgba(0, 255, 148, 0.15) !important;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 40px rgba(0, 255, 148, 0.25) !important;
    }
    
    /* Sliders */
    .stSlider div[data-baseweb="slider"] {
        background: #1E2D45 !important;
    }
    .stSlider div[data-baseweb="slider"] div {
        background: #00D4FF !important;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.2) !important;
    }
    
    /* Selectbox dropdown */
    div[data-baseweb="select"] > div {
        background: #0D1520 !important;
        border: 1px solid #1E2D45 !important;
        border-radius: 8px !important;
        color: #E8EDF5 !important;
    }
    div[data-baseweb="select"] ul {
        background: #0D1520 !important;
        border: 1px solid #1E2D45 !important;
    }
    div[data-baseweb="select"] li {
        color: #E8EDF5 !important;
    }
    div[data-baseweb="select"] li:hover {
        background: rgba(0, 212, 255, 0.08) !important;
    }
    
    /* Dataframes */
    .stDataFrame, .stTable {
        background: transparent !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .stDataFrame table, .stTable table {
        background: #0D1520 !important;
        border-collapse: collapse !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    .stDataFrame thead, .stTable thead {
        background: #111827 !important;
        border-bottom: 2px solid #1E2D45 !important;
    }
    .stDataFrame th, .stTable th {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.6rem !important;
        color: #4A5A70 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        padding: 0.7rem 1rem !important;
        text-align: left !important;
    }
    .stDataFrame td, .stTable td {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        color: #E8EDF5 !important;
        padding: 0.6rem 1rem !important;
        border-bottom: 1px solid rgba(30, 45, 69, 0.3) !important;
    }
    .stDataFrame tr:hover, .stTable tr:hover {
        background: rgba(0, 212, 255, 0.03) !important;
    }
    .stDataFrame tr:nth-child(even), .stTable tr:nth-child(even) {
        background: rgba(255, 255, 255, 0.02) !important;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #111827, #0D1520) !important;
        border: 1px solid #1E2D45 !important;
        border-radius: 10px !important;
        padding: 0.8rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="metric-container"]:hover {
        border-color: #00D4FF !important;
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.05) !important;
    }
    div[data-testid="metric-label"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.55rem !important;
        color: #4A5A70 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }
    div[data-testid="metric-value"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        color: #E8EDF5 !important;
    }
    
    /* Tabs */
    button[data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.65rem !important;
        letter-spacing: 0.06em !important;
        color: #4A5A70 !important;
        text-transform: uppercase !important;
        background: transparent !important;
        border-bottom: 2px solid transparent !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.3s ease !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #00D4FF !important;
        border-bottom-color: #00D4FF !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #E8EDF5 !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 0 !important;
        border-bottom: 1px solid #1E2D45 !important;
        background: transparent !important;
    }
    div[data-baseweb="tab-panel"] {
        padding-top: 1.5rem !important;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0A0D14 !important;
        border-right: 1px solid #1E2D45 !important;
        padding: 1rem 0 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #E8EDF5 !important;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stTextInput label {
        color: #4A5A70 !important;
    }
    
    /* Expanders */
    details {
        background: #111827 !important;
        border: 1px solid #1E2D45 !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    details summary {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.65rem !important;
        color: #7A8BA0 !important;
        cursor: pointer !important;
    }
    details summary:hover {
        color: #00D4FF !important;
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 8px !important;
        border: 1px solid #1E2D45 !important;
        background: #111827 !important;
        color: #E8EDF5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stAlert .stMarkdown {
        color: #E8EDF5 !important;
    }
    
    /* Success / Info / Warning / Error */
    .stSuccess { border-left: 3px solid #00FF94 !important; }
    .stInfo { border-left: 3px solid #00D4FF !important; }
    .stWarning { border-left: 3px solid #FF6B35 !important; }
    .stError { border-left: 3px solid #FF3355 !important; }
    
    /* ─────────────────────────────────────────────────────────
       CUSTOM CYBER COMPONENTS
    ───────────────────────────────────────────────────────── */
    .cyber-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, #1E2D45, transparent);
        margin: 1.5rem 0;
    }
    .cyber-divider-glow {
        height: 1px;
        background: linear-gradient(90deg, transparent, #00D4FF, transparent);
        margin: 1.5rem 0;
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
    }
    
    .glow-text-cyan {
        color: #00D4FF;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.15);
    }
    .glow-text-green {
        color: #00FF94;
        text-shadow: 0 0 20px rgba(0, 255, 148, 0.15);
    }
    .glow-text-orange {
        color: #FF6B35;
        text-shadow: 0 0 20px rgba(255, 107, 53, 0.15);
    }
    
    .cyber-tag {
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.55rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border: 1px solid;
    }
    .cyber-tag.cyan {
        color: #00D4FF;
        border-color: rgba(0, 212, 255, 0.2);
        background: rgba(0, 212, 255, 0.06);
    }
    .cyber-tag.green {
        color: #00FF94;
        border-color: rgba(0, 255, 148, 0.2);
        background: rgba(0, 255, 148, 0.06);
    }
    .cyber-tag.orange {
        color: #FF6B35;
        border-color: rgba(255, 107, 53, 0.2);
        background: rgba(255, 107, 53, 0.06);
    }
    
    /* Loading spinner override */
    .stSpinner {
        border-color: #00D4FF !important;
    }
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header {
        visibility: hidden !important;
        display: none !important;
    }
    
    /* ─────────────────────────────────────────────────────────
       RESPONSIVE FIXES
    ───────────────────────────────────────────────────────── */
    @media (max-width: 768px) {
        .scanner-banner {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
            padding: 0.8rem 1rem;
        }
        .status-metrics {
            flex-wrap: wrap;
            gap: 0.5rem 1rem;
        }
        .arb-block {
            flex-direction: column;
            align-items: stretch;
        }
        .arb-block .odds-display {
            justify-content: space-around;
        }
    }
    </style>
    """
