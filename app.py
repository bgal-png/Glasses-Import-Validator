import streamlit as st
import pandas as pd
from thefuzz import fuzz
import io

# 1. Page Configuration
st.set_page_config(page_title="Excel Spellchecker", layout="wide")
st.title("Excel Spellchecker (Strict Structure Mode)")

# --- CONFIGURATION: COLUMNS TO IGNORE ---
# The code will strictly ignore these columns.
# Ensure these names match your Excel headers exactly (case-sensitive).
IGNORE_LIST = [
    "Glasses name",
    "Meta description",
    "XML description",
    "Glasses model",
    "Glasses color code"
]

# --- HELPER: LOAD & STANDARDIZE ---
def load_data(file):
    """
    Loads the file and trims whitespace from headers
    to ensure 'Price ' matches 'Price'.
    """
    df = pd.read_excel(file, dtype=str)
    # 1. Strip whitespace from column names
    df.columns = df.columns.str.strip()
    return df

# 2. Load Master File
try:
    master_df = load_data("master.xlsx")
    st.success("✅ Master Database Loaded.")
except Exception as e:
    st.error(f"❌ Could not find 'master.xlsx'. Error: {e}")
    st.stop()

# 3. User Upload
st.divider()
st.subheader("1. Upload your file")
uploaded_file = st.file_uploader("Choose your Excel file", type=['xlsx'])

if uploaded_file:
    # Load user data
    user_df = load_data(uploaded_file)
    st.info(f"Uploaded file has {len(user_df)} rows.")

    # 4. Settings
    st.divider()
    st.subheader("2. Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        # Find common columns for ID selection
        common_cols = [c for c in master_df.columns if c in user_df.columns]
        if not common_cols:
            st.error("No matching columns found. Are the headers identical?")
            st.stop()
        id_col = st.selectbox("Unique ID Column", common_cols)
        
    with col2:
        threshold = st.slider("Fuzzy Match Strictness", 50, 100, 85)

    # Display what we are ignoring (for confirmation)
    # We only list columns that actually exist in the file to avoid confusion
    active_ignores = [col for col in IGNORE_LIST if col in user_df.columns]
    if active_ignores:
        st.caption(f"🚫 **Automatically Ignoring:** {', '.join(active_ignores)}")

    # 5. The Check
    if st.button("Run Spellcheck Comparison"):
        st.write("Checking... please wait.")
        
        mistakes = []
        
        # Optimize Master for Lookup
        master_indexed = master_df.set_index(id_col)
        
        # --- CRITICAL STEP: DEFINE COLUMNS TO CHECK ---
        # We assume structure is identical, so we take User columns
        # and subtract the ID column and the Ignore List.
        columns_to_check = [
            col for col in user_df.columns 
            if col != id_col and col not in IGNORE_LIST
        ]
        
        # Loop through every row in User file
        for index, user_row in user_df.iterrows():
            user_id = user_row[id_col]
            
            # 1. Does ID exist in Master?
            if user_id not in master_indexed.index:
                mistakes.append({
                    "Row": index + 2,
                    "ID": user_id,
                    "Column": "ID Check",
                    "Error": "ID Missing in Master",
                    "Your Value": user_id,
                    "Master Value": "---"
                })
                continue # Skip to next row

            # 2. Get the Master Data for this ID
            master_row = master_indexed.loc[user_id]
            # Handle duplicates (just in case)
            if isinstance(master_row, pd.DataFrame):
                master_row = master_row.iloc[0]

            # 3. Compare ONLY the valid columns
            for col in columns_to_check:
                # Safety check: ensure column exists in Master (it should, if structure is identical)
                if col not in master_df.columns:
                    continue
                    
                val_user = str(user_row[col]).strip()
                val_master = str(master_row[col]).strip()

                # EXACT MATCH (Pass)
                if val_user == val_master:
                    continue

                # CASE MISMATCH (Error)
                if val_user.lower() == val_master.lower():
                    mistakes.append({
                        "Row": index + 2,
                        "ID": user_id,
                        "Column": col,
                        "Error": "Case Mismatch",
                        "Your Value": val_user,
                        "Master Value": val_master
                    })
                    continue

                # FUZZY CHECK (Error)
                score = fuzz.ratio(val_user.lower(), val_master.lower())
                
                if score >= threshold:
                    mistakes.append({
                        "Row": index + 2,
                        "ID": user_id,
                        "Column": col,
                        "Error": f"Typo ({score}%)",
                        "Your Value": val_user,
                        "Master Value": val_master
                    })
                else:
                    mistakes.append({
                        "Row": index + 2,
                        "ID": user_id,
                        "Column": col,
                        "Error": "Wrong Value",
                        "Your Value": val_user,
                        "Master Value": val_master
                    })

        # --- OUTPUT RESULTS ---
        if mistakes:
            st.error(f"Found {len(mistakes)} issues.")
            res_df = pd.DataFrame(mistakes)
            st.dataframe(res_df, use_container_width=True)
            
            # Download Logic
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False)
                
            st.download_button("📥 Download Report", buffer, "mistakes.xlsx")
            
        else:
            st.success("✅ Perfect Match! No mistakes found.")
            st.balloons()
