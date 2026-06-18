CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
    }

    .main-header {
        background: linear-gradient(135deg, #0f766e 0%, #1e293b 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
    }

    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.025em;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
        font-weight: 400;
    }

    .metric-card {
        background: rgba(240, 253, 250, 0.65);
        border: 1px solid rgba(16, 185, 129, 0.18);
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
    }

    .weather-banner {
        background: linear-gradient(90deg, #f0fdfa 0%, #ecfdf5 100%);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        border-left: 5px solid #0f766e;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
        font-size: 1.05rem;
        color: #0f766e;
        font-weight: 500;
    }

    .plan-section {
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(16, 185, 129, 0.15);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }

    .plan-section:hover {
        transform: translateY(-2px);
        border-color: rgba(16, 185, 129, 0.3);
    }

    .plan-section h4 {
        margin: 0 0 0.3rem 0;
        color: #0f766e;
        font-weight: 600;
    }

    .disclaimer-box {
        background: #fffbeb;
        border: 1px solid #fef3c7;
        border-radius: 10px;
        padding: 1rem;
        font-size: 0.85rem;
        color: #b45309;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.01);
    }

    .health-points-bar {
        background: #e2e8f0;
        border-radius: 20px;
        height: 12px;
        overflow: hidden;
        margin-top: 0.5rem;
    }

    .health-points-fill {
        background: linear-gradient(90deg, #0d9488, #10b981);
        height: 100%;
        border-radius: 20px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    div[data-testid="stSidebar"] {
        background: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }

    .stButton > button {
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05) !important;
    }

    .stButton > button[kind="primary"] {
        background: #0f766e !important;
        border-color: #0f766e !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #0d9488 !important;
        border-color: #0d9488 !important;
        box-shadow: 0 4px 12px rgba(13, 148, 136, 0.2) !important;
    }
</style>
"""
