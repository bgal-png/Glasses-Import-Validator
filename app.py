import streamlit as st
import pandas as pd
import os
import io

# 1. Page Configuration
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Excel Validator: Glasses Edition 👓")

# --- HELPER: ROBUST LOADER ---
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

    # Clean headers: remove newlines and spaces
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # Filter for 'Glasses'
    # We look for ANY column that contains "Items type"
    target_col = next((c for c in df.columns if "Items type" in c), None)
    
    if target_col:
        return df[df[target_col] == "Glasses"]
    else:
        st.error(f"❌ 'Items type' missing in Master. Found: {list(df.columns)}"); st.stop()

def clean_user_file(file, header_row=0):
    try:
        df = pd.read_excel(file, dtype=str, header=header_row)
    except:
        file.seek(0)
        df = pd.read_csv(file, dtype=str, sep=None, engine='python', header=header_row)
    
    # Clean headers
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
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

    # 4. AUTO-MAPPING (The "Blind" Fix)
    # We will try to map columns by fuzzy matching.
    # If it fails, we SKIP the column instead of crashing.
    
    # Define ideal pairs
    IDEAL_PAIRS = {
        "Glasses type": "Glasses type ID",
        "Manufacturer": "Manufacturer ID",
        "Glasses size: glasses width": "width ID",
        "Glasses size: temple length": "temple length ID",
        "Glasses size: lens height": "lens height ID",
        "Glasses size: lens width": "lens width ID",
        "Glasses size: bridge": "bridge ID",
        "Glasses shape": "Glasses shape ID",
        "Glasses other info": "other info ID",
        "Glasses frame type": "frame type ID",
        "Glasses frame color": "Frame Colour ID",
        "Glasses temple color": "Temple Colour ID",
        "Glasses main material": "main material ID",
        "Glasses lens color": "lens Colour ID",
        "Glasses lens material": "lens material ID",
        "Glasses lens effect": "lens effect ID",
        "Sunglasses filter": "Sunglasses filter ID",
        "Glasses genre": "Glasses gendre ID",
        "Glasses usable": "Glasses usable ID",
        "Glasses collection": "Glasses collection ID",
        "UV filter": "UV filter ID",
        "Items type": "Items type ID",
        "Items packing": "Items packing ID",
        "Glasses contain": "Glasses contain ID",
        "Sport glasses": "Sports Glasses ID",
        "Glasses frame color effect": "frame color effect ID",
        "Glasses other features": "other features ID",
        "SunGlasses RX lenses": "RX lenses ID",
        "Glasses clip-on lens color": "clip-on lens colour ID",
        "Brand": "Brand ID",
        "Producing company": "Producing company ID",
        "Glasses for your face shape": "face shape ID",
        "Glasses lenses no-orders": "no-orders ID"
    }
    
    active_map = {}
    user_cols = list(user_df.columns)
    master_cols = list(master_df.columns)
    
    st.write("---")
    st.write("### 🔗 Column Mapping Status")
    
    for master_key, partial_user_key in IDEAL_PAIRS.items():
        # Find Master Column
        real_master_col = next((c for c in master_cols if master_key in c), None)
        
        # Find User Column (Partial Match)
        real_user_col = next((c for c in user_cols if partial_user_key in c), None)
        
        if real_master_col and real_user_col:
            active_map[real_master_col] = real_user_col
        else:
            # st.warning(f"⚠️ Skipping '{master_key}' -> Could not find match in files.")
            pass
            
    st.success(f"✅ Successfully mapped {len(active_map)} columns.")

    # 5. VALIDATION LOGIC
    if st.button("🚀 Run Validation"):
        mistakes = []
        st.write("Checking data... please wait.")
        
        valid_values = {}
        # Pre-load Master Values
        for m_col in active_map.keys():
            valid_set = set(master_df[m_col].dropna().astype(str).str.strip().str.lower())
            valid_values[m_col] = valid_set

        progress_bar = st.progress(0)
        total_rows = len(user_df)
        
        for index, row in user_df.iterrows():
            if index % 10 == 0: progress_bar.progress(min(index / total_rows, 1.0))
            
            for m_col, u_col in active_map.items():
                cell_value = str(row[u_col]).strip()
                if cell_value.lower() in ['nan', '', 'none']: continue
                
                if cell_value.lower() not in valid_values[m_col]:
                    mistakes.append({
                        "Row #": index + 2 + header_row_idx,
                        "Column": u_col,
                        "Invalid Value": cell_value,
                        "Allowed Options (Example)": list(valid_values[m_col])[:3]
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
