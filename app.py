import streamlit as st
import pandas as pd
import os
import io
import zipfile
import numpy as np
from PIL import Image
from sklearn.cluster import KMeans

# 1. Page Configuration
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Glasses Import Validator 😎")

# ==========================================
# 🔒 LOCKED: MAIN MASTER LOADER (Tab 1)
# RESTORED: The "Indestructible" Version
# ==========================================
@st.cache_data
def load_master():
    """
    TRULY INDESTRUCTIBLE LOADER
    1. Tries Excel (.xlsx)
    2. If that fails, tries CSV with Auto-Separator.
    3. If that fails, tries CSV with comma/semicolon explicitly.
    """
    current_dir = os.getcwd()
    # Exclude 'name_master' so we don't accidentally load the wrong file here
    candidates = [f for f in os.listdir(current_dir) if (f.endswith('.xlsx') or f.endswith('.csv')) and "mistakes" not in f and "name_master" not in f and not f.startswith('~$')]
    
    if not candidates:
        st.error("❌ No Master File found!"); st.stop()
    
    file_path = candidates[0]
    df = None
    
    # ATTEMPT 1: EXCEL (Standard)
    try:
        df = pd.read_excel(file_path, dtype=str, engine='openpyxl')
    except Exception:
        # ATTEMPT 2: CSV (Fallback loop)
        strategies = [
            {'sep': None, 'engine': 'python'}, # Auto-detect
            {'sep': ',', 'engine': 'c'},       # Standard Comma
            {'sep': ';', 'engine': 'c'},       # Semicolon
            {'sep': '\t', 'engine': 'c'}       # Tab
        ]
        
        for enc in ['utf-8', 'cp1252', 'latin1']:
            for strat in strategies:
                try:
                    df = pd.read_csv(
                        file_path, 
                        dtype=str, 
                        encoding=enc, 
                        on_bad_lines='skip', 
                        **strat
                    )
                    st.toast(f"ℹ️ Loaded '{file_path}' as CSV (Fallback).", icon="ℹ️")
                    break
                except:
                    continue
            if df is not None:
                break
    
    if df is None:
        st.error(f"❌ Could not read '{file_path}'. Tried Excel and all CSV formats.")
        st.stop()

    # Clean headers
    df.columns = df.columns.astype(str).str.replace(r'\s+', ' ', regex=True).str.strip()
    
    # Filter for 'Glasses'
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
    def column_filter(col_name):
        if not isinstance(col_name, str): return False
        c = col_name.strip().lower()
        return c == "name" or "name_private" in c

    # ATTEMPT 1: EXCEL (With Column Filter)
    try:
        df = pd.read_excel(
            target_filename, 
            dtype=str, 
            engine='openpyxl',
            usecols=column_filter
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
                        usecols=column_filter,
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
# 🎨 COLOR DETECTION HELPERS (Tab 4)
# ==========================================
COLOR_MAP = {
    "Black":       (0, 0, 0),
    "White":       (255, 255, 255),
    "Red":         (180, 30, 30),
    "Blue":        (30, 60, 180),
    "Brown":       (130, 80, 40),
    "Havana":      (140, 90, 50),
    "Gold":        (212, 175, 55),
    "Silver":      (180, 180, 185),
    "Ruthenium":   (140, 140, 145),
    "Rose Gold":   (190, 130, 110),
    "Green":       (40, 120, 50),
    "Grey":        (128, 128, 128),
    "Pink":        (220, 130, 150),
    "Purple":      (100, 40, 140),
    "Orange":      (220, 120, 30),
    "Yellow":      (220, 200, 50),
    "Ivory":       (240, 230, 210),
    "Turquoise":   (50, 180, 175),
    "Burgundy":    (130, 20, 40),
}

# Colors that are close enough to be considered compatible
COLOR_ALIASES = {
    "Havana": {"Brown", "Havana"},
    "Brown": {"Brown", "Havana"},
    "Silver": {"Silver", "Ruthenium", "Grey"},
    "Ruthenium": {"Silver", "Ruthenium", "Grey"},
    "Grey": {"Grey", "Silver", "Ruthenium"},
}

SKIP_COLORS = {"Transparent", "Multicolor", "Special"}

def rgb_to_color_name(rgb):
    """Map an RGB tuple to the nearest named color using Euclidean distance."""
    min_dist = float('inf')
    best = "Unknown"
    for name, ref_rgb in COLOR_MAP.items():
        dist = sum((a - b) ** 2 for a, b in zip(rgb, ref_rgb)) ** 0.5
        if dist < min_dist:
            min_dist = dist
            best = name
    return best

def extract_dominant_colors(image_bytes, n_colors=5):
    """
    Extract dominant colors from a background-free image.
    Filters out transparent and near-white pixels.
    Returns list of (color_name, percentage) sorted by dominance.
    """
    img = Image.open(io.BytesIO(image_bytes))

    # Resize for speed (max 150px on longest side)
    img.thumbnail((150, 150))

    # Convert to RGBA to handle transparency
    img = img.convert("RGBA")
    pixels = np.array(img)

    # Flatten to list of pixels
    flat = pixels.reshape(-1, 4)

    # Filter out transparent pixels (alpha < 10)
    opaque = flat[flat[:, 3] >= 10]

    # Filter out near-white background remnants (R>240, G>240, B>240)
    rgb_only = opaque[:, :3]
    mask = ~((rgb_only[:, 0] > 240) & (rgb_only[:, 1] > 240) & (rgb_only[:, 2] > 240))
    rgb_only = rgb_only[mask]

    if len(rgb_only) < 10:
        return [("White", 100.0)]

    # KMeans clustering
    k = min(n_colors, len(rgb_only))
    kmeans = KMeans(n_clusters=k, n_init=5, random_state=42)
    kmeans.fit(rgb_only)

    # Count pixels per cluster
    labels, counts = np.unique(kmeans.labels_, return_counts=True)
    total = counts.sum()

    # Map clusters to color names with percentages
    results = []
    for center, count in zip(kmeans.cluster_centers_, counts):
        name = rgb_to_color_name(tuple(int(c) for c in center))
        pct = round(count / total * 100, 1)
        results.append((name, pct))

    # Merge duplicate color names (multiple clusters mapping to same name)
    merged = {}
    for name, pct in results:
        merged[name] = merged.get(name, 0) + pct

    return sorted(merged.items(), key=lambda x: x[1], reverse=True)

def colors_match(expected_color, detected_colors):
    """
    Check if an expected color name is found in the detected colors.
    Uses aliases for compatible colors (e.g., Havana ≈ Brown).
    """
    expected = expected_color.strip()
    if expected in SKIP_COLORS:
        return None  # Cannot verify

    detected_names = {name for name, _ in detected_colors}

    # Direct match
    if expected in detected_names:
        return True

    # Alias match (e.g., Havana matches Brown)
    compatible = COLOR_ALIASES.get(expected, {expected})
    if compatible & detected_names:
        return True

    return False

# ==========================================
# 🚀 MAIN APP EXECUTION
# ==========================================

# LOAD DATA
with st.spinner("Loading Databases..."):
    master_df = load_master() # Original Indestructible Loader
    name_master_list = load_name_master() # Surgical Loader

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

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Data Validation", "🖼️ Image Checker", "🧬 Syntax & Duplicates", "🎨 Color Checker"])

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

    # ------------------------------------------
    # TAB 4: COLOR CHECKER
    # ------------------------------------------
    with tab4:
        st.subheader("🎨 Glasses Color Checker", help="Upload a ZIP of background-free product images to verify colors match the Excel data.")

        # Find color columns in user file
        COLOR_FIELDS = {
            "Glasses frame color": "Frame Colour ID",
            "Glasses lens color": "lens Colour ID",
            "Glasses temple color": "Temple Colour ID",
        }

        color_col_map = {}
        for label, user_key in COLOR_FIELDS.items():
            found = next((c for c in user_df.columns if user_key in c), None)
            if found:
                color_col_map[label] = found

        if not color_col_map:
            st.error("❌ No color ID columns found in the uploaded file (expected 'Frame Colour ID', 'lens Colour ID', 'Temple Colour ID').")
        else:
            st.write(f"🔗 Found **{len(color_col_map)}** color columns: {', '.join(color_col_map.keys())}")

            # Find the name column
            name_col = next((c for c in user_df.columns if "Glasses name" in c), user_df.columns[0])
            st.write(f"📂 **Matching images to column:** `{name_col}`")

            st.info("ℹ️ **Note:** 'Transparent', 'Multicolor', and 'Special' colors are skipped (cannot be verified from pixels). 'Havana' ≈ 'Brown' are treated as compatible.")

            zip_file = st.file_uploader("Upload ZIP of product images", type=['zip'], key="color_zip")

            if zip_file and st.button("🎨 Run Color Check", type="primary"):
                # Build lookup: product name -> row data
                name_lookup = {}
                for idx, row in user_df.iterrows():
                    raw_name = str(row[name_col]).strip()
                    if raw_name.lower() not in ['nan', '', 'none']:
                        name_lookup[raw_name.lower()] = (idx, row)

                # Extract images from ZIP
                results = []
                skipped = []
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    image_files = [f for f in zf.namelist()
                                   if not f.startswith('__MACOSX')
                                   and not f.startswith('.')
                                   and f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]

                    if not image_files:
                        st.error("❌ No valid image files found in ZIP.")
                    else:
                        progress = st.progress(0)
                        status_text = st.empty()

                        for i, img_path in enumerate(image_files):
                            progress.progress((i + 1) / len(image_files))

                            # Extract product name from filename
                            fname = img_path.split('/')[-1]
                            product_name = fname.rsplit('.', 1)[0] if '.' in fname else fname
                            product_name_clean = product_name.replace('_', '/').strip().lower()

                            status_text.text(f"Analyzing {i+1}/{len(image_files)}: {product_name}")

                            # Match to Excel row
                            if product_name_clean not in name_lookup:
                                skipped.append({"Image": fname, "Reason": "No matching product in Excel"})
                                continue

                            row_idx, row = name_lookup[product_name_clean]

                            # Extract dominant colors from image
                            try:
                                img_bytes = zf.read(img_path)
                                detected = extract_dominant_colors(img_bytes)
                            except Exception as e:
                                skipped.append({"Image": fname, "Reason": f"Could not process: {str(e)}"})
                                continue

                            detected_summary = ", ".join(f"{name} ({pct}%)" for name, pct in detected)

                            # Check each color field
                            for label, col_name in color_col_map.items():
                                raw_val = str(row[col_name]).strip()
                                if raw_val.lower() in ['nan', '', 'none']:
                                    continue

                                # Handle pipe-separated values
                                expected_colors = [v.strip() for v in raw_val.split('|')]

                                for expected in expected_colors:
                                    match_result = colors_match(expected, detected)

                                    if match_result is None:
                                        results.append({
                                            "Row": row_idx + 2,
                                            "Product": product_name,
                                            "Field": label,
                                            "Expected": expected,
                                            "Detected": detected_summary,
                                            "Status": "⏭️ SKIPPED"
                                        })
                                    elif match_result:
                                        results.append({
                                            "Row": row_idx + 2,
                                            "Product": product_name,
                                            "Field": label,
                                            "Expected": expected,
                                            "Detected": detected_summary,
                                            "Status": "✅ MATCH"
                                        })
                                    else:
                                        results.append({
                                            "Row": row_idx + 2,
                                            "Product": product_name,
                                            "Field": label,
                                            "Expected": expected,
                                            "Detected": detected_summary,
                                            "Status": "❌ MISMATCH"
                                        })

                        progress.empty()
                        status_text.empty()

                        # Display results
                        if results:
                            res_df = pd.DataFrame(results)

                            mismatches = res_df[res_df["Status"] == "❌ MISMATCH"]
                            matches = res_df[res_df["Status"] == "✅ MATCH"]
                            skipped_checks = res_df[res_df["Status"] == "⏭️ SKIPPED"]

                            c1, c2, c3 = st.columns(3)
                            c1.metric("Matches", len(matches))
                            c2.metric("Mismatches", len(mismatches))
                            c3.metric("Skipped", len(skipped_checks))

                            if len(mismatches) > 0:
                                st.error(f"❌ {len(mismatches)} color mismatches found!")
                                st.dataframe(
                                    mismatches.style.map(
                                        lambda x: 'background-color: #ffcccc; color: black;' if x == "❌ MISMATCH" else '',
                                        subset=['Status']
                                    ),
                                    use_container_width=True
                                )
                            else:
                                st.balloons()
                                st.success("✅ All verifiable colors match!")

                            with st.expander("Show all results"):
                                st.dataframe(res_df, use_container_width=True)
                        else:
                            st.warning("No color comparisons could be made.")

                        if skipped:
                            with st.expander(f"⚠️ {len(skipped)} images skipped"):
                                st.dataframe(pd.DataFrame(skipped), use_container_width=True)
