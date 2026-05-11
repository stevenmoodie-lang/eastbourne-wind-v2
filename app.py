# --- CSS: MOBILE OPTIMIZATION FIXED ---
st.markdown("""
    <style>
        [data-testid="stHeader"], header { visibility: hidden; height: 0; }
        .stAppViewContainer { top: -35px !important; } /* Adjusted from -45px to prevent clipping */
        .stApp { background-color: #3d5a73; color: #f8f9fa; }
        .block-container { 
            padding-top: 1.5rem !important; /* Slightly more space for the title */
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .custom-title {
            text-align: center;
            font-size: 1.3rem; /* Reduced slightly to fit narrow screens */
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.2rem;
            line-height: 1.2;
        }
    </style>
    <div class="custom-title">Eastbourne Wind</div>
""", unsafe_allow_html=True)
