import streamlit as st
import pandas as pd
import os
import io

# 1. Page Configuration
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Excel Validator: Glasses Edition 👓")

# --- COLUMN MAPPING CONFIGURATION ---
# Key = Master File Column Name (The Source of Truth)
# Value = User File Column Name (The Column to Check)
COLUMN_MAPPING = {
    "Glasses type": "Glasses type ID: 13",
    "Manufacturer": "Manufacturer ID: 9",
    "Glasses size: glasses width": "Glasses size: glasses width ID: 69",
    "Glasses size: temple length": "Glasses size: temple length ID: 70",
    "Glasses size: lens height": "Glasses size: lens height ID: 71",
    "Glasses size: lens width": "Glasses size: lens width ID: 72",
    "Glasses size: bridge": "Glasses size: bridge ID: 73",
    "Glasses shape": "Glasses shape ID: 25",             # <--- UPDATED
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

# --- HELPER FUNCTIONS ---
@st.cache_data
def load_master():
    """Robust loader for Master File."""
    file_path = "master.xlsx"
    if not os.path.exists(file_path):
        st.error("❌ 'master.xlsx' not found."); st.stop()
        
    df = None
    try:
        df = pd.read_excel(file_path, dtype=str, engine='openpyxl')
    except:
        try:
            # Try CSV fallback
            df = pd.read_csv(file_path, dtype=str, sep=None, engine='python')
        except Exception:
            st.error("❌ Could not load Master file."); st.stop()
            
    df.columns = df.columns.str.strip()
    
    if "Items type" in df.columns:
        return df[df["Items type"] == "Glasses"]
    else:
        st.error("❌ 'Items type' column missing in Master."); st.stop()

def clean_user_file(file, header_row=0):
    try:
        df = pd.read_excel(file, dtype=str, header=header_row)
    except:
        file.seek(0)
        df = pd.read_csv(file, dtype=str, sep=None, engine='python', header=header_row)
    
    df.columns = df.columns.astype(str).str.strip()
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
        st.error(f"❌ CRITICAL: Master File is missing: {missing_master}"); st.stop()
    if missing_user:
        st.error(f"❌ CRITICAL: User File is missing: {missing_user}"); st.stop()

    st.success("✅ Structure Validated!")

    # 5. VALIDATION LOGIC
    if st.button("🚀 Run Validation"):
        
        mistakes = []
        st.write("Checking data... please wait.")
        
        # Pre-process Master Data into Sets for instant lookup
        # This makes the check extremely fast (O(1) complexity)
        valid_values = {}
        for master_col in COLUMN_MAPPING.keys():
            # Create a set of all valid values for this column
            # We convert to lowercase to make it case-insensitive if needed, 
            # but for now we keep it exact or lowercase for comparison.
            valid_set = set(master_df[master_col].dropna().str.strip().str.lower())
            valid_values[master_col] = valid_set

        # Progress Bar
        progress_bar = st.progress(0)
        
        # Loop through User Rows
        total_rows = len(user_df)
        
        for index, row in user_df.iterrows():
            # Update progress every 10 rows
            if index % 10 == 0:
                progress_bar.progress(min(index / total_rows, 1.0))
            
            # Check every column in the map
            for master_col, user_col in COLUMN_MAPPING.items():
                
                # Get the value from user file
                cell_value = str(row[user_col]).strip()
                
                # Ignore empty cells (NaN or empty string)
                if cell_value.lower() == 'nan' or cell_value == "":
                    continue
                
                # CHECK: Is this value in the Master Set?
                # We check case-insensitive match
                if cell_value.lower() not in valid_values[master_col]:
                    mistakes.append({
                        "Row #": index + 2 + header_row_idx, # Adjust for 0-index and header
                        "Column": user_col,
                        "Invalid Value": cell_value,
                        "Expected From": master_col
                    })

        progress_bar.empty()

        # 6. OUTPUT REPORT
        if mistakes:
            st.error(f"Found {len(mistakes)} Invalid Values!")
            
            results_df = pd.DataFrame(mistakes)
            st.dataframe(results_df, use_container_width=True)
            
            # Download Button
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, index=False, sheet_name='Errors')
                
            st.download_button(
                label="📥 Download Error Report",
                data=buffer,
                file_name="validation_errors.xlsx",
                mime="application/vnd.ms-excel"
            )
        else:
            st.balloons()
            st.success("✅ Amazing! No invalid values found. All data matches the Master File options.")
