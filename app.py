import streamlit as st
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Excel Spellchecker", layout="wide")
st.title("My Excel Spellchecker")

# --- HELPER FUNCTION TO CLEAN HEADERS ---
def clean_headers(df):
    """Removes newlines and extra spaces from column names."""
    df.columns = [str(c).replace("\n", " ").strip() for c in df.columns]
    return df

# 2. Load Master File (Cached)
@st.cache_data
def load_master():
    # Load as string to preserve data like '00123'
    df = pd.read_excel("master.xlsx", dtype=str)
    # CLEAN THE HEADERS IMMEDIATELY
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
    
    # Select ID Column from Master headers
    id_col = st.selectbox("Which column contains the Unique ID?", master_df.columns)

    # --- SAFETY CHECK: Does this column exist in the User file? ---
    if id_col not in user_df.columns:
        st.error(f"⚠️ Error: The column '{id_col}' exists in the Master file but NOT in your uploaded file.")
        st.warning(f"Your uploaded columns are: {list(user_df.columns)}")
        st.stop() # Stop here, don't run the rest of the code
    
    # Button to trigger check
    if st.button("Run Spellcheck Comparison"):
        
        st.write("Checking... please wait.")
        
        # --- THE COMPARISON LOGIC ---
        mistakes = []
        
        # Optimize: Set ID as index for faster lookups (replaces the slow loop)
        # We create copies so we don't mess up the original display data
        master_indexed = master_df.set_index(id_col)
        
        # Loop through User file
        for index, user_row in user_df.iterrows():
            user_id = user_row[id_col]
            
            # Check if ID exists in Master
            if user_id not in master_indexed.index:
                mistakes.append({
                    "Row #": index + 2,
                    "ID": user_id,
                    "Column": "ID Check",
                    "Issue": "This ID does not exist in the Master file."
                })
                continue 

            # Get the matching Master row
            master_row = master_indexed.loc[user_id]
            
            # Handle duplicates in master (if multiple rows have same ID, take the first one)
            if isinstance(master_row, pd.DataFrame):
                master_row = master_row.iloc[0]

            # Compare columns
            for column in user_df.columns:
                if column == id_col:
                    continue 
                
                # Check if column exists in Master to compare
                if column in master_df.columns:
                    val_user = str(user_row[column]).strip()
                    val_master = str(master_row[column]).strip()
                    
                    if val_user != val_master:
                        mistakes.append({
                            "Row #": index + 2,
                            "ID": user_id,
                            "Column": column,
                            "Your Value": val_user,
                            "Master Value": val_master
                        })

        # --- OUTPUT RESULTS ---
        if mistakes:
            st.error(f"Found {len(mistakes)} discrepancies!")
            results_df = pd.DataFrame(mistakes)
            st.dataframe(results_df, use_container_width=True)
        else:
            st.balloons()
            st.success("Perfect Match! No mistakes found.")