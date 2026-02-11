import streamlit as st
import pandas as pd

# 1. Page Configuration
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Excel Validator: Glasses Edition 👓")

# --- COLUMN MAPPING CONFIGURATION ---
# Key = Master File Column Name
# Value = User File Column Name
COLUMN_MAPPING = {
    "Glasses type": "Glasses type",
    "Manufacturer": "Manufacturer",
    "Glasses size: glasses width": "Glasses size: glasses width",
    "Glasses size: temple length": "Glasses size: temple length",
    "Glasses size: lens height": "Glasses size: lens height",
    "Glasses size: lens width": "Glasses size: lens width",
    "Glasses size: bridge": "Glasses size: bridge",
    "Glasses shape": "Glasses shape",
    "Glasses other info": "Glasses other info",
    "Glasses frame type": "Glasses frame type",
    "Glasses frame color": "Frame Colour",
    "Glasses temple color": "Temple Colour",
    "Glasses main material": "Glasses main material",
    "Glasses lens Color": "Glasses lens Colour",
    "Glasses lens material": "Glasses lens material",
    "Glasses lens effect": "Glasses lens effect",
    "Sunglasses filter": "Sunglasses filter",
    "Glasses genre": "Glasses gendre",
    "Glasses usable": "Glasses usable",
    "Glasses collection": "Glasses collection",
    "UV filter": "UV filter",
    "Items type": "Items type",
    "Items packing": "Items packing",
    "Glasses contain": "Glasses contain",
    "Sport Glasses": "Sports Glasses",
    "Glasses frame color effect": "Glasses frame color effect",
    "Glasses other features": "Glasses other features",
    "SunGlasses RX lenses": "SunGlasses RX lenses",
    "Glasses clip-on lens colour": "Glasses clip-on lens colour",
    "Brand": "Brand",
    "Producing company": "Producing company",
    "Glasses for your face shape": "Glasses for your face shape",
    "Glasses lenses no-orders": "Glasses lenses no-orders"
}

# --- HELPER: LOAD & CLEAN ---
@st.cache_data
def load_master():
    df = pd.read_excel("master.xlsx", dtype=str)
    # Clean headers (strip spaces)
    df.columns = df.columns.str.strip()
    
    # Filter for 'Glasses' only (Column V in Excel, 'Items type' here)
    if "Items type" in df.columns:
        df = df[df["Items type"] == "Glasses"]
    return df

def clean_user_file(file):
    df = pd.read_excel(file, dtype=str)
    df.columns = df.columns.str.strip()
    return df

# 2. LOAD MASTER
try:
    master_df = load_master()
    st.success(f"✅ Master File Loaded. ({len(master_df)} rows of 'Glasses')")
except Exception as e:
    st.error(f"❌ Error loading Master: {e}")
    st.stop()

# 3. UPLOAD USER FILE
st.divider()
st.subheader("1. Upload File to Validate")
uploaded_file = st.file_uploader("Choose Excel File", type=['xlsx'])

if uploaded_file:
    user_df = clean_user_file(uploaded_file)
    st.info(f"User file loaded: {len(user_df)} rows.")

    # 4. STRUCTURE CHECK (Sanity Check)
    # Before we compare data, let's make sure the columns exist!
    missing_master = []
    missing_user = []

    for master_col, user_col in COLUMN_MAPPING.items():
        if master_col not in master_df.columns:
            missing_master.append(master_col)
        if user_col not in user_df.columns:
            missing_user.append(user_col)
    
    if missing_master:
        st.error(f"❌ CRITICAL: The Master File is missing these columns: {missing_master}")
        st.stop()
        
    if missing_user:
        st.error(f"❌ CRITICAL: Your Uploaded File is missing these columns: {missing_user}")
        st.stop()
        
    st.success("✅ Structure Validated! All required columns exist in both files.")
    
    # Placeholder for the next step
    if st.button("Start Validation"):
        st.write("Validation logic coming next...")
