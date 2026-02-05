import streamlit as st
import pandas as pd
from thefuzz import fuzz
import io

# 1. Page Configuration
st.set_page_config(page_title="Excel Spellchecker", layout="wide")
st.title("My Excel Spellchecker (Fuzzy + Exclusions)")

# --- HELPER FUNCTION TO CLEAN HEADERS ---
def clean_headers(df):
    """Removes newlines and extra spaces from column names."""
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    return df

# 2. Load Master File (Cached)
@st.cache_data
def load_master():
    df = pd.read_excel("master.xlsx", dtype=str)
    df = clean_headers(df)
    return df

try:
    master_df = load_master()
    st.success("Master Database Loaded Successfully.")
except Exception as e:
    st.error(f"Could not find 'master.xlsx'. Make sure it is in the folder! Error: {e}")
    st.stop()

# 3. User Upload Section
st.divider()
st.subheader("1. Upload your file")
uploaded_file = st.file_uploader("Choose your Excel file", type=['xlsx'])

if uploaded_file:
    # Load user data and CLEAN HEADERS
    user_df = pd.read_excel(uploaded_file, dtype=str)
    user_df = clean_headers(user_df)
    
    st.info(f"Uploaded file has {len(user_df)} rows.")

    # 4. Settings Section
    st.divider()
    st.subheader("2. Settings")
    
    col1, col2 = st.columns(2)
    with col1:
        # Select ID Column
        id_col = st.selectbox("Which column contains the Unique ID?", master_df.columns)
    with col2:
        # Slider for Fuzzy Matching
        threshold = st.slider("Fuzzy Match Threshold (0-100)", min_value=50, max_value=100, value=85)

    # --- IGNORE COLUMNS SECTION ---
    default_ignore = ["Glasses name", "Meta description", "XML description", "Glasses model", "Glasses color code"]
    # Only keep defaults that actually exist in the uploaded file
    valid_defaults = [c for c in default_ignore if c in user_df.columns]
    
    ignore_cols = st.multiselect(
        "Select columns to IGNORE during spellcheck:",
        options=user_df.columns,
        default=valid_defaults
    )

    # --- SAFETY CHECK ---
    if id_col not in user_df.columns:
        st.error(f"⚠️ Error: The column '{id_col}' exists in the Master file but NOT in your uploaded file.")
        st.stop()
    
    # Button to trigger check
    if st.button("Run Spellcheck Comparison"):
        
        st.write("Checking... please wait.")
        
        # DEBUG: Show user what is being ignored
        if ignore_cols:
            st.caption(f"🙈 Ignoring these columns: {', '.join(ignore_cols)}")

        mistakes = []
        master_indexed = master_df.set_index(id_col)
        
        # --- ROBUST LOGIC CHANGE ---
        # Create a specific list of columns to check right now. 
        # We exclude the ID column and any Ignored columns immediately.
        columns_to_check = [c for c in user_df.columns if c != id_col and c not in ignore_cols]
        
        for index, user_row in user_df.iterrows():
            user_id = user_row[id_col]
            
            # Check if ID exists in Master
            if user_id not in master_indexed.index:
                mistakes.append({
                    "Row #": index + 2,
                    "ID": user_id,
                    "Column": "ID Check",
                    "Error Type": "ID Missing",
                    "Your Value": user_id,
                    "Master Value": "Not Found"
                })
                continue 

            # Get Master row
            master_row = master_indexed.loc[user_id]
            if isinstance(master_row, pd.DataFrame):
                master_row = master_row.iloc[0]

            # Compare ONLY the allowed columns
            for column in columns_to_check:
                
                # Check if column exists in Master to compare
                if column in master_df.columns:
                    val_user = str(user_row[column]).strip()
                    val_master = str(master_row[column]).strip()
                    
                    # 1. Exact Match
                    if val_user == val_master:
                        continue 

                    # 2. Case Mismatch
                    if val_user.lower() == val_master.lower():
                        mistakes.append({
                            "Row #": index + 2,
                            "ID": user_id,
                            "Column": column,
                            "Error Type": "Case Mismatch",
                            "Your Value": val_user,
                            "Master Value": val_master
                        })
                        continue

                    # 3. Fuzzy Match
                    match_score = fuzz.ratio(val_user.lower(), val_master.lower())
                    
                    if match_score >= threshold:
                        mistakes.append({
                            "Row #": index + 2,
                            "ID": user_id,
                            "Column": column,
                            "Error Type": f"Typo ({match_score}%)",
                            "Your Value": val_user,
                            "Master Value": val_master
                        })
                    else:
                        mistakes.append({
                            "Row #": index + 2,
                            "ID": user_id,
                            "Column": column,
                            "Error Type": "Wrong Value",
                            "Your Value": val_user,
                            "Master Value": val_master
                        })

        # --- OUTPUT RESULTS ---
        if mistakes:
            st.error(f"Found {len(mistakes)} discrepancies!")
            results_df = pd.DataFrame(mistakes)
            results_df = results_df.sort_values(by=["Error Type", "Row #"])
            st.dataframe(results_df, use_container_width=True)
            
            # Download Button
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, index=False, sheet_name='Mistakes')
                
            st.download_button(
                label="📥 Download Mistakes Report",
                data=buffer,
                file_name="spellcheck_mistakes.xlsx",
                mime="application/vnd.ms-excel"
            )
            
        else:
            st.balloons()
            st.success("Perfect Match! No mistakes found.")
