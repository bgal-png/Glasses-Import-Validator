import streamlit as st
import pandas as pd
from thefuzz import fuzz
import io

# 1. Page Configuration
st.set_page_config(page_title="Excel Spellchecker", layout="wide")
st.title("Excel Spellchecker (Strict Structure)")

# --- CONFIGURATION ---
# Columns to strictly ignore
IGNORE_LIST = [
    "Glasses name",
    "Meta description",
    "XML description",
    "Glasses model",
    "Glasses color code"
]

# --- HELPER: LOAD DATA ---
@st.cache_data(show_spinner=False)
def load_data(file_path):
    """
    Loads Excel and cleans headers.
    """
    # Load all data as string to preserve IDs like '007'
    df = pd.read_excel(file_path, dtype=str)
    
    # Clean headers: remove hidden spaces
    df.columns = df.columns.str.strip()
    return df

# 2. Load Master File
with st.spinner("Loading Master Database..."):
    try:
        master_df = load_data("master.xlsx")
        st.success("✅ Master Database Loaded.")
    except Exception as e:
        st.error(f"❌ Error loading master file: {e}")
        st.stop()

# 3. User Upload
st.divider()
st.subheader("1. Upload your file")
uploaded_file = st.file_uploader("Choose your Excel file", type=['xlsx'])

if uploaded_file:
    with st.spinner("Reading uploaded file..."):
        user_df = load_data(uploaded_file)
    
    st.info(f"Uploaded file has {len(user_df)} rows.")

    # 4. Settings
    st.divider()
    st.subheader("2. Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        # Find shared columns
        common_cols = [c for c in master_df.columns if c in user_df.columns]
        if not common_cols:
            st.error("No matching columns found! Check your headers.")
            st.stop()
        id_col = st.selectbox("Unique ID Column", common_cols)
        
    with col2:
        threshold = st.slider("Fuzzy Match Strictness", 50, 100, 85)

    # 5. Run Comparison
    if st.button("Run Spellcheck Comparison"):
        
        # VISUAL FEEDBACK: Show spinner while processing
        with st.spinner("Checking for mistakes... this may take a moment."):
            
            mistakes = []
            master_indexed = master_df.set_index(id_col)
            
            # Define columns to check (User Columns MINUS Id MINUS Ignore List)
            cols_to_check = [
                c for c in user_df.columns 
                if c != id_col and c not in IGNORE_LIST
            ]
            
            # Loop Rows
            for index, user_row in user_df.iterrows():
                user_id = user_row[id_col]
                
                # Check ID
                if user_id not in master_indexed.index:
                    mistakes.append({
                        "Row": index + 2,
                        "ID": user_id,
                        "Column": "ID Check",
                        "Error": "ID Missing",
                        "Your Value": user_id,
                        "Master Value": "---"
                    })
                    continue 

                # Get Master Row
                master_row = master_indexed.loc[user_id]
                if isinstance(master_row, pd.DataFrame):
                    master_row = master_row.iloc[0]

                # Check Columns
                for col in cols_to_check:
                    # Skip if master doesn't have this column
                    if col not in master_df.columns:
                        continue

                    val_user = str(user_row[col]).strip()
                    val_master = str(master_row[col]).strip()

                    # Exact Match
                    if val_user == val_master:
                        continue 

                    # Case Mismatch
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

                    # Fuzzy Match
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

        # --- OUTPUT ---
        if mistakes:
            st.error(f"Found {len(mistakes)} issues.")
            res_df = pd.DataFrame(mistakes)
            st.dataframe(res_df, use_container_width=True)
            
            # Download
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                res_df.to_excel(writer, index=False)
                
            st.download_button("📥 Download Report", buffer, "mistakes.xlsx")
        else:
            st.success("✅ Perfect Match! No mistakes found.")
            st.balloons()
