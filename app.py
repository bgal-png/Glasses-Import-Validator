import streamlit as st
import pandas as pd
import os
import io
import re

# 1. Page Configuration
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Excel Validator: Glasses Edition 👓")

# --- COLUMN MAPPING CONFIGURATION ---
# We use SINGLE SPACES here because the code below will auto-fix the user file to match this.
COLUMN_MAPPING = {
    "Glasses type": "Glasses type ID: 13",
    "Manufacturer": "Manufacturer ID: 9",
    "Glasses size: glasses width": "Glasses size: glasses width ID: 69",
    "Glasses size: temple length": "Glasses size: temple length ID: 70",
    "Glasses size: lens height": "Glasses size: lens height ID: 71",
    "Glasses size: lens width": "Glasses size: lens width ID: 72",
    "Glasses size: bridge": "Glasses size: bridge ID: 73",
    "Glasses shape": "Glasses shape ID: 25",
    "Glasses other info": "Glasses other info ID: 49",
    "Glasses frame type": "Glasses frame type ID: 50",
    "Glasses frame color": "Frame Colour ID: 26",
    "Glasses temple color": "Temple Colour ID: 39",
    "Glasses main material": "Glasses main material ID: 53",
    "Glasses lens color": "Glasses lens Colour ID: 28",
    "Glasses lens material": "Glasses lens material ID: 35",
    "Glasses lens effect": "Glasses lens effect ID: 37",
    "Sunglasses filter": "Sunglasses filter ID: 77",
    "Glasses genre": "Glasses gendre ID: 22",
    "Glasses usable": "Glasses usable ID: 51",
    "Glasses collection": "Glasses collection ID: 33",
    "UV filter": "UV filter ID: 60",
    "Items type": "Items type ID: 20",
    "Items packing": "Items packing ID: 21",
    "Glasses contain": "Glasses contain ID: 84",
    "Sport glasses": "Sports Glasses ID: 89",
    "Glasses frame color effect": "Glasses frame color effect ID: 92",
    "Glasses other features": "Glasses other features ID:99",
    "SunGlasses RX lenses": "SunGlasses RX lenses ID:108",
    "Glasses clip-on lens color": "Glasses clip-on lens colour ID:112",
    "Brand": "Brand ID:11",
    "Producing company": "Producing company ID:146",
    "Glasses for your face shape": "Glasses for your face shape ID:94",
    "Glasses lenses no-orders": "Glasses lenses no-orders ID:103"
}

# --- HELPER: NORMALIZE HEADERS ---
def normalize_headers(df):
    """
    Magic Function: Replaces newlines, tabs, and multiple spaces 
    with a single clean space.
    """
    # Regex '\s+' means "one or more whitespace characters"
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    return df

@st.cache_data
def load_master():
    """Smart Loader: Scans folder for ANY Excel/CSV file."""
    current_dir = os.getcwd()
    candidates = [f for f in os.listdir(current_dir) if (f.endswith('.xlsx') or f.endswith('.csv')) and "mistakes" not in f and not f.startswith('~$')]
    
    if not candidates:
        st.error("❌ No Master File found!"); st.stop()
    
    file_path = candidates[0]
    df = None
    
    try:
        if file_path.endswith('.csv'):
            for enc in ['utf-8', 'cp1252', 'latin1']:
                try: df = pd.read_csv(file_path, dtype=str, sep=None, engine='python', encoding=enc); break
                except: continue
        else:
            df = pd.read_excel(file_path, dtype=str, engine='openpyxl')
    except Exception as e:
        st.error(f"❌ Failed to load '{file_path}': {e}"); st.stop()
        
    if df is None: st.error("❌ Could not read file."); st.stop()

    # Apply Normalization
    df = normalize_headers(df)
    
    if "Items type" in df.columns:
        return df[df["Items type"] == "Glasses"]
    else:
        st.error(f"❌ 'Items type' missing. Found: {list(df.columns)}"); st.stop()

def clean_user_file(file, header_row=0):
    try:
        df = pd.read_excel(file, dtype=str, header=header_row)
    except:
        file.seek(0)
        df = pd.read_csv(file, dtype=str, sep=None, engine='python', header=header_row)
    
    # Apply Normalization
    df = normalize_headers(df)
    return df

# 2. LOAD MASTER
master_df = load_master()
st.success(f"✅ Master File Loaded ({len(master_df)} rows).")

# 3. UPLOAD SECTION
st.divider()
st.subheader("1. Upload File")

col_upload, col_settings = st.columns([2, 1])
with col_settings:
    header_row_idx = st.number_input("Header Row Number", min_value=0, max_value=10, value=0)
with col_upload:
    uploaded_file = st.file_uploader("Choose Excel File", type=['xlsx'])

if uploaded_file:
    user_df = clean_user_file(uploaded_file, header_row=header_row_idx)
    st.info(f"User file loaded: {len(user_df)} rows.")

    # 4. STRUCTURE CHECK
    missing_master = [col for col in COLUMN_MAPPING.keys() if col not in master_df.columns]
    missing_user = [col for col in COLUMN_MAPPING.values() if col not in user_df.columns]

    if missing_master:
        st.error(f"❌ CRITICAL: Master File is missing: {missing_master}")
        st.stop()
    if missing_user:
        st.error(f"❌ CRITICAL: User File is missing: {missing_user}")
        
        # DEBUG: Show user exactly what the code sees
        with st.expander("🕵️ Debug: What headers do I see?"):
            st.write("I normalized your headers to this:")
            st.code(list(user_df.columns))
        st.stop()

    st.success("✅ Structure Validated!")

    # 5. VALIDATION LOGIC
    if st.button("🚀 Run Validation"):
        mistakes = []
        st.write("Checking data... please wait.")
        
        valid_values = {}
        for master_col in COLUMN_MAPPING.keys():
            valid_set = set(master_df[master_col].dropna().astype(str).str.strip().str.lower())
            valid_values[master_col] = valid_set

        progress_bar = st.progress(0)
        total_rows = len(user_df)
        
        for index, row in user_df.iterrows():
            if index % 10 == 0: progress_bar.progress(min(index / total_rows, 1.0))
            
            for master_col, user_col in COLUMN_MAPPING.items():
                cell_value = str(row[user_col]).strip()
                if cell_value.lower() in ['nan', '', 'none']: continue
                
                if cell_value.lower() not in valid_values[master_col]:
                    mistakes.append({
                        "Row #": index + 2 + header_row_idx,
                        "Column": user_col,
                        "Invalid Value": cell_value,
                        "Allowed Options (Example)": list(valid_values[master_col])[:3]
                    })

        progress_bar.empty()

        if mistakes:
            st.error(f"Found {len(mistakes)} Invalid Values!")
            results_df = pd.DataFrame(mistakes)
            st.dataframe(results_df, use_container_width=True)
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, index=False)
            st.download_button("📥 Download Error Report", buffer, "validation_errors.xlsx")
        else:
            st.balloons()
            st.success("✅ Amazing! No invalid values found.")
