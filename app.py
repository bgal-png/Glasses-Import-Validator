import streamlit as st
import pandas as pd
import os
import io

# 1. Page Configuration
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Excel Validator: Glasses Edition 👓")

# ==========================================
# 🔒 LOCKED: MAIN MASTER LOADER (Tab 1)
# ==========================================
@st.cache_data
def load_master():
    """TRULY INDESTRUCTIBLE LOADER for Main Data"""
    current_dir = os.getcwd()
    candidates = [f for f in os.listdir(current_dir) if (f.endswith('.xlsx') or f.endswith('.csv')) and "mistakes" not in f and "name_master" not in f and not f.startswith('~$')]
    
    if not candidates:
        st.error("❌ No Master File found!"); st.stop()
    
    file_path = candidates[0]
    df = None
    
    # ATTEMPT 1: EXCEL
    try:
        df = pd.read_excel(file_path, dtype=str, engine='openpyxl')
    except Exception:
        # ATTEMPT 2: CSV
        strategies = [
            {'sep': None, 'engine': 'python'}, 
            {'sep': ',', 'engine': 'c'}, 
            {'sep': ';', 'engine': 'c'}, 
            {'sep': '\t', 'engine': 'c'}
        ]
        for enc in ['utf-8', 'cp1252', 'latin1']:
            for strat in strategies:
                try:
                    df = pd.read_csv(file_path, dtype=str, encoding=enc, on_bad_lines='skip', **strat)
                    st.toast(f"ℹ️ Loaded '{file_path}' as CSV (Fallback).", icon="ℹ️")
                    break
                except: continue
            if df is not None: break
    
    if df is None:
        st.error(f"❌ Could not read '{file_path}'. Tried Excel and all CSV formats.")
        st.stop()

    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    target_col = next((c for c in df.columns if "Items type" in c), None)
    
    if target_col:
        return df[df[target_col] == "Glasses"]
    else:
        st.error("❌ 'Items type' column missing in Master File."); st.stop()

# ==========================================
# ⚡ SURGICAL LOADER: NAME MASTER (Tab 3)
# optimized for speed & memory
# ==========================================
@st.cache_data
def load_name_master():
    """
    SURGICAL LOADER.
    Only loads columns 'name' and 'name_private'.
    Ignores everything else to run fast.
    """
    target_filename = "name_master_clean.xlsx"
    
    if not os.path.exists(target_filename):
        candidates = [f for f in os.listdir('.') if "name_master" in f and not f.startswith('~$')]
        if not candidates: return None
        target_filename = candidates[0]

    df = None

    # DEFINING THE FILTER:
    # We use a lambda function to tell Pandas WHICH columns to keep.
    # This prevents loading the other 40+ columns into RAM.
    def column_filter(col_name):
        if not isinstance(col_name, str): return False
        c = col_name.strip().lower()
        # We only want 'name' (exact) or 'name_private' (contains)
        return c == "name" or "name_private" in c

    # ATTEMPT 1: EXCEL (With Column Filter)
    try:
        df = pd.read_excel(
            target_filename, 
            dtype=str, 
            engine='openpyxl',
            usecols=column_filter # <--- This makes it "Surgical"
        )
    except Exception:
        # ATTEMPT 2: CSV (With Column Filter)
        strategies = [{'sep': None, 'engine': 'python'}, {'sep': ',', 'engine': 'c'}, {'sep': ';', 'engine': 'c'}]
        for enc in ['utf-8', 'cp1252', 'latin1']:
            for strat in strategies:
                try:
                    df = pd.read_csv(
                        target_filename, 
                        dtype=str, 
                        encoding=enc, 
                        on_bad_lines='skip', 
                        usecols=column_filter, # <--- "Surgical" here too
                        **strat
                    )
                    break
                except: continue
            if df is not None: break

    if df is None: return None

    # Clean Headers
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()

    # 1. FILTER: Column 'name_private' must contain "glasses"
    private_col = next((c for c in df.columns if "name_private" in c), None)
    if not private_col: return None
        
    filtered_df = df[df[private_col].str.contains("glasses", case=False, na=False)]
    
    # 2. TARGET: Column 'name'
    name_col = next((c for c in df.columns if "name" == c or "name" == c.strip()), None)
    if not name_col: return None
         
    return filtered_df[name_col].dropna().unique().tolist()

# ==========================================
# 🧠 HELPER FUNCTIONS
# ==========================================
def clean_user_file(file):
    try: df = pd.read_excel(file, dtype=str, header=0)
    except: file.seek(0); df = pd.read_csv(file, dtype=str, sep=None, engine='python', header=0)
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    return df

def get_skeleton(text):
    if not isinstance(text, str): return ""
    skeleton = ""
    for char in text:
        if char.isupper(): skeleton += "A"
        elif char.islower(): skeleton += "a"
        elif char.isdigit(): skeleton += "0"
        else: skeleton += char 
    return skeleton

# ==========================================
# 🚀 MAIN APP EXECUTION
# ==========================================

# LOAD DATA
with st.spinner("Loading Databases..."):
    master_df = load_master() 
    name_master_list = load_name_master()

st.success(f"✅ Main Master Loaded ({len(master_df)} rows).")

if name_master_list:
    st.success(f"✅ Name Master Loaded ({len(name_master_list)} validated names).")
else:
    st.warning("⚠️ 'name_master_clean.xlsx' not found. Tab 3 will be disabled.")

# UPLOAD USER FILE
st.divider()
st.subheader("1. Upload User File")
uploaded_file = st.file_uploader("Choose Excel File", type=['xlsx'])

if uploaded_file:
    user_df = clean_user_file(uploaded_file)
    st.info(f"User file loaded: {len(user_df)} rows.")

    tab1, tab2, tab3 = st.tabs(["📊 Data Validation", "🖼️ Image Checker", "🧬 Syntax & Duplicates"])

    # ------------------------------------------
    # TAB 1: DATA VALIDATION
    # ------------------------------------------
    with tab1:
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
        for mk, uk in IDEAL_PAIRS.items():
            rmc = next((c for c in master_cols if mk in c), None)
            ruc = next((c for c in user_cols if uk in c), None)
            if rmc and ruc: active_map[rmc] = ruc
        
        st.write(f"🔗 Mapped **{len(active_map)}** columns.")

        if st.button("🚀 Run Validation", type="primary"):
            mistakes = []
            valid_values = {}
            for m_col in active_map.keys():
                raw = master_df[m_col].dropna().astype(str)
                exploded = raw.str.split(r',+').explode()
                clean_set = set(exploded.str.strip().str.lower())
                if "" in clean_set: clean_set.remove("")
                valid_values[m_col] = clean_set

            progress_bar = st.progress(0)
            total_rows = len(user_df)
            for idx, row in user_df.iterrows():
                if idx % 10 == 0: progress_bar.progress(min(idx / total_rows, 1.0))
                for m_col, u_col in active_map.items():
                    raw_val = str(row[u_col])
                    if raw_val.lower() in ['nan', '', 'none']: continue
                    
                    ws_issues = []
                    if raw_val.startswith(" "): ws_issues.append("Leading Space")
                    if raw_val.endswith(" "): ws_issues.append("Trailing Space")
                    if "  " in raw_val: ws_issues.append("Double Spaces")
                    if "| " in raw_val or " |" in raw_val: ws_issues.append("Space around Separator")
                    for ws in ws_issues:
                        mistakes.append({"Row": idx+2, "Column": u_col, "Error": "Whitespace", "Value": ws, "Content": raw_val})

                    clean_val = raw_val.strip()
                    parts = [v.strip() for v in clean_val.split('|')]
                    for p in parts:
                        if p and p.lower() not in valid_values[m_col]:
                             mistakes.append({"Row": idx+2, "Column": u_col, "Error": "Invalid Content", "Value": p, "Content": raw_val, "Allowed": list(valid_values[m_col])[:3]})
            
            progress_bar.empty()
            if mistakes:
                st.error(f"Found {len(mistakes)} Issues!")
                st.dataframe(pd.DataFrame(mistakes), use_container_width=True)
            else: st.balloons(); st.success("✅ Clean!")

    # ------------------------------------------
    # TAB 2: IMAGE CHECKER
    # ------------------------------------------
    with tab2:
        st.subheader("🖼️ Image Name vs. Excel Checker", help="To get images paths go to the folder containing images -> Select all (Ctrl + A) -> Right click -> Copy as paths")
        
        target_col_name = "Glasses name" 
        found_col = next((c for c in user_df.columns if target_col_name.lower() in c.lower()), user_df.columns[0])
        st.write(f"📂 **Using Excel Column:** `{found_col}`")
        excel_names = set(user_df[found_col].dropna().astype(str).str.strip().str.lower().tolist())

        pasted_paths = st.text_area("Paste File Paths Here", height=300)
        
        if st.button("🔍 Check Images"):
            if not pasted_paths.strip(): st.warning("Paste paths first!")
            else:
                lines = pasted_paths.split('\n')
                found_imgs = set()
                for line in lines:
                    if not line.strip(): continue
                    fname = line.split('\\')[-1] 
                    cname = fname.rsplit('.', 1)[0] if '.' in fname else fname
                    found_imgs.add(cname.replace('_', '/').strip().lower())

                miss = [n for n in excel_names if n not in found_imgs]
                extra = [n for n in found_imgs if n not in excel_names]

                c1, c2 = st.columns(2)
                with c1:
                    st.error(f"❌ Missing ({len(miss)})"); 
                    if miss: st.dataframe(pd.DataFrame(miss, columns=["Missing"]), use_container_width=True)
                with c2:
                    st.warning(f"⚠️ Extra ({len(extra)})"); 
                    if extra: st.dataframe(pd.DataFrame(extra, columns=["Extra"]), use_container_width=True)

    # ------------------------------------------
    # TAB 3: SYNTAX & DUPLICATES
    # ------------------------------------------
    with tab3:
        st.subheader("🧬 Syntax & Duplicate Checker")
        
        if not name_master_list:
            st.error("❌ 'name_master_clean.xlsx' was not found or could not be read.")
        else:
            st.write(f"✅ Comparison Database: **{len(name_master_list)}** valid glasses loaded.")
            
            user_name_col_idx = next((i for i, c in enumerate(user_df.columns) if "Glasses name" in c), 0)
            target_user_col = st.selectbox("Select Name Column in User File", user_df.columns, index=user_name_col_idx)
            
            if st.button("🧬 Analyze Syntax & Duplicates"):
                st.write("Analyzing patterns...")
                
                valid_names_set = set(n.strip() for n in name_master_list)
                valid_skeletons = set(get_skeleton(n) for n in name_master_list)
                
                report = []
                
                for idx, name in user_df[target_user_col].dropna().astype(str).items():
                    clean_name = name.strip()
                    row_num = idx + 2
                    
                    if clean_name in valid_names_set:
                        report.append({"Row": row_num, "Name": clean_name, "Issue": "❌ DUPLICATE", "Details": "Name already exists in master file."})
                        continue 
                    
                    my_skel = get_skeleton(clean_name)
                    if my_skel not in valid_skeletons:
                        report.append({"Row": row_num, "Name": clean_name, "Issue": "⚠️ SUSPICIOUS SYNTAX", "Details": f"New Pattern: {my_skel}"})
                
                if report:
                    st.error(f"Found {len(report)} Issues!")
                    res_df = pd.DataFrame(report)
                    st.dataframe(res_df.style.applymap(lambda x: 'background-color: #ffcccc; color: black;' if x == "❌ DUPLICATE" else 'background-color: #fff4cc; color: black;', subset=['Issue']), use_container_width=True)
                else: st.balloons(); st.success("✅ Perfect! No duplicates and all syntax patterns look familiar.")
