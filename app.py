import streamlit as st
import pandas as pd
import os
import io
import re
import zipfile
import numpy as np
from pathlib import Path
from PIL import Image
from sklearn.cluster import KMeans

# 1. Page Configuration
# NOTE: the "Clear cache?" popup that fired on Ctrl+C is a Streamlit developer
# shortcut (bare "c" key). It's disabled via .streamlit/config.toml
# (client.toolbarMode = "viewer"), which hides the developer tools entirely.
st.set_page_config(page_title="Excel Validator v2", layout="wide")
st.title("Glasses Import Validator 😎")

# ==========================================
# 🔒 LOCKED: MAIN MASTER LOADER (Tab 1)
# ==========================================
@st.cache_data
def load_master():
    """
    INDESTRUCTIBLE LOADER
    1. Tries Excel (.xlsx)
    2. If that fails, tries CSV with Auto-Separator.
    """
    current_dir = os.getcwd()
    candidates = [f for f in os.listdir(current_dir) if (f.endswith('.xlsx') or f.endswith('.csv')) and "mistakes" not in f and "name_master" not in f and not f.startswith('~$')]

    if not candidates:
        st.error("❌ No Master File found!"); st.stop()

    file_path = candidates[0]
    df = None

    try:
        df = pd.read_excel(file_path, dtype=str, engine='openpyxl')
    except Exception:
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
                    break
                except: continue
            if df is not None: break

    if df is None:
        st.error(f"❌ Could not read '{file_path}'."); st.stop()

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
# ==========================================
@st.cache_data
def load_name_master():
    """
    SURGICAL LOADER.
    Only loads columns 'name' and 'name_private'.
    """
    target_filename = "name_master_clean.xlsx"

    if not os.path.exists(target_filename):
        candidates = [f for f in os.listdir('.') if "name_master" in f and not f.startswith('~$')]
        if not candidates: return None
        target_filename = candidates[0]

    df = None

    def column_filter(col_name):
        if not isinstance(col_name, str): return False
        c = col_name.strip().lower()
        return c == "name" or "name_private" in c

    try:
        df = pd.read_excel(target_filename, dtype=str, engine='openpyxl', usecols=column_filter)
    except Exception:
        strategies = [{'sep': None, 'engine': 'python'}, {'sep': ',', 'engine': 'c'}, {'sep': ';', 'engine': 'c'}]
        for enc in ['utf-8', 'cp1252', 'latin1']:
            for strat in strategies:
                try:
                    df = pd.read_csv(target_filename, dtype=str, encoding=enc, on_bad_lines='skip', usecols=column_filter, **strat)
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
# 🏷️ IMAGE RENAMER (Tab 6)
# Source: github.com/bgal-png/Tool-Hub/blob/main/tools/image_renamer.py
# Renames glasses images to match canonical product list names.
# ==========================================

# Brand-agnostic matching: no brand map needed. We reduce both the source
# filename and each product-list line to their pure alphanumeric "core"
# (uppercased, separators stripped) and match when one core contains the other.
# This handles glued codes (GU3038, FT0926), separated codes (BOSS 1880),
# and concatenated colors (807IR vs 807/IR) without per-brand configuration.

PHOTO_SUFFIX_RE = re.compile(r"^P\d{1,3}$", re.IGNORECASE)  # P00, P01, ...
PHOTO_NUM_RE = re.compile(r"^\d{1,2}$")                     # 1-2 digit photo index
INVALID_FS_CHARS = set('<>:"/\\|?*')


def list_blob(s):
    """Reduce a string to uppercase alphanumerics only (drop spaces, /, -, &, etc.)."""
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def parse_list_entry(line):
    """A list line is usable if it's non-empty. Returns {'raw': line} or None.
    No brand parsing needed — matching works on the raw text."""
    line = line.strip()
    if not line:
        return None
    return {"raw": line}


def tokenize_source(filename):
    """Strip extension, normalize separators (_ - to space), split into tokens."""
    stem = Path(filename).stem
    return re.sub(r"[_\-]+", " ", stem).split()


def is_photo_token(tok):
    """True for trailing tokens that are photo indices (P00, 01, ...) rather than codes."""
    return bool(PHOTO_SUFFIX_RE.match(tok) or PHOTO_NUM_RE.match(tok))


def code_signature(text):
    """Concatenate the alphanumeric content of tokens that contain a digit
    (model + color codes), dropping pure brand-name words. e.g.
    'Dolce & Gabbana DG4477 252587' -> 'DG4477252587'."""
    parts = []
    for tok in text.split():
        if re.search(r"\d", tok):
            parts.append(re.sub(r"[^A-Z0-9]", "", tok.upper()))
    return "".join(parts)


def match_filename(filename, entries, barcode_map=None):
    """Find the list entry whose alphanumeric core matches the filename's core.
    If the filename is a bare barcode (all digits, >= 8) and barcode_map is given,
    look it up there first and rename to that product's name. Otherwise tries the
    full filename, then strips trailing photo tokens and retries. A match must
    contain a digit (never matches on letters alone) unless it's an exact match.
    Returns matched entry + any leftover photo tokens."""
    tokens = tokenize_source(filename)
    if not tokens:
        return {"status": "error", "reason": "Empty filename after parsing"}

    # Barcode path: the filename is just a barcode (digits only, >= 8 chars).
    if barcode_map:
        stem_digits = re.sub(r"\D", "", Path(filename).stem)
        full_alnum = list_blob(" ".join(tokens))
        if stem_digits and stem_digits == full_alnum and len(stem_digits) >= 8:
            name = barcode_map.get(stem_digits)
            if name:
                return {"status": "matched", "entry": {"raw": name}, "leftover_tokens": []}
            return {"status": "no_match", "tokens": tokens}

    # Split off trailing photo-index tokens (kept for collision suffixes)
    core = list(tokens)
    leftover = []
    while len(core) > 1 and is_photo_token(core[-1]):
        leftover.insert(0, core.pop())

    # Full filename first (in case a 1-2 digit trailing token is really a sub-color),
    # then the photo-stripped core.
    for core_tokens, lo in [(tokens, []), (core, leftover)]:
        f_blob = list_blob(" ".join(core_tokens))
        if not f_blob:
            continue

        # Digit-containing cores (with a model number) match by substring.
        # Digit-less names (e.g. "Nocturna Frames Anima Black Grey") must match
        # a list entry EXACTLY — this avoids latching onto a bare brand word.
        has_digit = bool(re.search(r"\d", f_blob))

        matches = []
        for e in entries:
            e_blob = list_blob(e["raw"])
            if not e_blob:
                continue
            if has_digit:
                hit = f_blob in e_blob or e_blob in f_blob
            else:
                hit = f_blob == e_blob
            if hit:
                matches.append((len(e_blob), e))

        if matches:
            matches.sort(key=lambda x: x[0], reverse=True)
            best_len = matches[0][0]
            top = [e for ln, e in matches if ln == best_len]
            if len(top) > 1:
                return {"status": "ambiguous", "candidates": [e["raw"] for e in top]}
            return {"status": "matched", "entry": top[0], "leftover_tokens": lo}

    # PASS 2 (fallback): the entry's model+color "code signature" appears anywhere
    # in the filename. Handles filenames with extra junk the list lacks — leading
    # zeros, trailing variant codes, brand words missing, e.g.
    # "0DG4477__252587_7009.jpg" vs "Dolce & Gabbana DG4477 252587".
    f_full = list_blob(" ".join(tokens))
    sig_matches = []
    for e in entries:
        sig = code_signature(e["raw"])
        if sig and len(sig) >= 5 and sig in f_full:
            sig_matches.append((len(sig), e))
    if sig_matches:
        sig_matches.sort(key=lambda x: x[0], reverse=True)
        best_len = sig_matches[0][0]
        top = [e for ln, e in sig_matches if ln == best_len]
        if len(top) > 1:
            return {"status": "ambiguous", "candidates": [e["raw"] for e in top]}
        return {"status": "matched", "entry": top[0], "leftover_tokens": leftover}

    return {"status": "no_match", "tokens": tokens}


def safe_name(s):
    return "".join("_" if c in INVALID_FS_CHARS else c for c in s)


def target_name_for(entry, ext):
    base = entry["raw"].replace("/", "_")
    return safe_name(base) + ext


def extract_photo_suffix(filename):
    stem = Path(filename).stem
    m = re.search(r"[_\-]P(\d{2,3})$", stem, re.IGNORECASE)
    if m:
        return f"P{m.group(1)}"
    return None


def derive_photo_suffix(row):
    """Best-effort photo-number suffix for a matched row.
    Priority:
      1. A numeric token in the leftover (e.g. "_01" after the model/color)
      2. A trailing P-suffix in the original filename (P00, P01, ...)
    Returns a string like 'P01' or None."""
    for tok in (row.get("leftover_tokens") or []):
        m = re.match(r"^(\d{1,3})$", tok)
        if m:
            return f"P{int(m.group(1)):02d}"
    return extract_photo_suffix(row["source"])


def resolve_collisions(plan):
    groups = {}
    for row in plan:
        if row["status"] != "matched":
            continue
        groups.setdefault(row["target"], []).append(row)

    for target, rows in groups.items():
        if len(rows) < 2:
            continue
        existing = [derive_photo_suffix(r) for r in rows]
        if all(existing) and len(set(existing)) == len(existing):
            stem, ext = Path(target).stem, Path(target).suffix
            for r, sfx in zip(rows, existing):
                r["target"] = f"{stem} {sfx}{ext}"
                r["collision"] = f"used original suffix {sfx}"
        else:
            stem, ext = Path(target).stem, Path(target).suffix
            for i, r in enumerate(rows):
                r["target"] = f"{stem} P{i:02d}{ext}"
                r["collision"] = f"auto-suffix P{i:02d}"
    return plan


def render_image_renamer(user_df):
    """Streamlit UI for the image renamer (rendered inside Tab 6)."""
    st.subheader("🏷️ Glasses Image Renamer")
    st.write(
        "Rename glasses product images to match canonical names from your product list. "
        "Source filenames use short brand codes; list entries use full brand names. "
        "The tool maps between them and replaces `/` with `_` for Windows compatibility."
    )

    if "ren_uploader_key" not in st.session_state:
        st.session_state["ren_uploader_key"] = 0

    # Pull the product list from the uploaded validation file's "Glasses name" column
    name_col = next((c for c in user_df.columns if "Glasses name" in c), user_df.columns[0])
    file_names = (
        user_df[name_col].dropna().astype(str).str.strip()
        .loc[lambda s: ~s.str.lower().isin(["nan", "", "none"])]
        .tolist()
    )

    # Build a barcode -> product name lookup (for photos named with just a barcode).
    # Barcodes are normalized to digits only (strips trailing NBSP / whitespace).
    barcode_col = next((c for c in user_df.columns if "barcode" in c.lower()), None)
    barcode_map = {}
    if barcode_col:
        for _, brow in user_df.iterrows():
            bc = re.sub(r"\D", "", str(brow[barcode_col]))
            nm = str(brow[name_col]).strip()
            if bc and nm and nm.lower() not in ("nan", "", "none"):
                barcode_map.setdefault(bc, nm)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        uploaded_images = st.file_uploader(
            "Upload images (.jpg / .png)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"ren_images_{st.session_state['ren_uploader_key']}",
        )
        if uploaded_images:
            if st.button("🗑️ Clear all uploaded images", use_container_width=True, key="ren_clear"):
                st.session_state["ren_uploader_key"] += 1
                st.rerun()

    with col_b:
        use_file_list = st.checkbox(
            f"Use product list from uploaded file's `{name_col}` column ({len(file_names)} names)",
            value=True,
            key="ren_use_file",
        )
        if use_file_list:
            list_text = "\n".join(file_names)
            with st.expander(f"📋 Preview list from file ({len(file_names)} names)"):
                st.text("\n".join(file_names) if file_names else "(no names found)")
        else:
            list_text = st.text_area(
                "Product list — one per line",
                height=200,
                placeholder=(
                    "Marc Jacobs MJ 882/S 12J/HA\n"
                    "Hugo Boss BOSS 1880/G/S 807/IR\n"
                    "Missoni MIS 0266 ZI9\n"
                    "Tom Ford FT0926 01E"
                ),
                key="ren_list",
            )

    if not uploaded_images:
        st.info("Upload one or more images above to begin.")
        return
    if not list_text.strip():
        if use_file_list:
            st.warning(f"No names found in the `{name_col}` column of the uploaded file.")
        else:
            st.info("Paste a product list to continue.")
        return

    raw_lines = [ln for ln in list_text.splitlines() if ln.strip()]
    entries = []
    list_warnings = []
    for ln in raw_lines:
        parsed = parse_list_entry(ln)
        if parsed is None:
            list_warnings.append(ln)
        else:
            entries.append(parsed)

    if list_warnings:
        with st.expander(f"⚠️ {len(list_warnings)} unparseable list lines"):
            for w in list_warnings:
                st.write(f"`{w}`")

    if not entries:
        st.error("No valid list entries parsed. Check the format.")
        return

    if barcode_map:
        st.caption(f"🔖 Barcode lookup ready ({len(barcode_map)} barcodes) — photos named with just a barcode will be matched too.")

    plan = []
    for f in uploaded_images:
        result = match_filename(f.name, entries, barcode_map)
        row = {"source": f.name, "status": result["status"], "_file": f}
        if result["status"] == "matched":
            entry = result["entry"]
            ext = Path(f.name).suffix
            row["target"] = target_name_for(entry, ext)
            row["matched_entry"] = entry["raw"]
            row["leftover_tokens"] = result.get("leftover_tokens", [])
        else:
            row["target"] = None
            row["matched_entry"] = None
            row["reason"] = result
        plan.append(row)

    plan = resolve_collisions(plan)

    matched_entry_raws = {row["matched_entry"] for row in plan if row["status"] == "matched"}
    missing_entries = [e["raw"] for e in entries if e["raw"] not in matched_entry_raws]

    n_total = len(plan)
    n_matched = sum(1 for r in plan if r["status"] == "matched")
    n_unmatched = n_total - n_matched
    n_collisions = sum(1 for r in plan if r.get("collision"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total files", n_total)
    c2.metric("Matched", n_matched)
    c3.metric("Unmatched", n_unmatched)
    c4.metric("Collisions resolved", n_collisions)

    st.subheader("Preview")
    matched_rows = [r for r in plan if r["status"] == "matched"]
    if matched_rows:
        df = pd.DataFrame([
            {
                "Source": r["source"],
                "→": "→",
                "Target": r["target"],
                "Note": r.get("collision", ""),
                "Already correct": r["source"] == r["target"],
            }
            for r in matched_rows
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("No files matched any list entry.")

    unmatched_rows = [r for r in plan if r["status"] != "matched"]
    if unmatched_rows:
        with st.expander(f"⚠️ {len(unmatched_rows)} unmatched files"):
            for r in unmatched_rows:
                reason = r.get("reason", {}).get("status", "unknown")
                detail = ""
                if reason == "no_match":
                    detail = " (no list entry matches this model/color code)"
                elif reason == "ambiguous":
                    cands = r.get("reason", {}).get("candidates", [])
                    detail = f" (matches multiple entries: {', '.join(cands)})"
                elif reason == "error":
                    detail = " (could not read filename)"
                st.write(f"`{r['source']}` — {reason}{detail}")

    if missing_entries:
        with st.expander(f"⚠️ {len(missing_entries)} list entries with no matching file"):
            for e in missing_entries:
                st.write(f"`{e}`")

    st.divider()
    actionable = [r for r in matched_rows if r["source"] != r["target"]]
    if not actionable:
        st.success("✅ All matched files already have the correct names — nothing to rename.")
        return

    st.caption(
        f"{len(actionable)} files will be renamed. The output is a ZIP containing all "
        "renamed images plus a `rename_log.csv` for auditing."
    )

    if st.button("📦 Build renamed ZIP", type="primary", key="ren_build"):
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in matched_rows:
                file_bytes = r["_file"].getvalue()
                zf.writestr(r["target"], file_bytes)
            log_df = pd.DataFrame([
                {
                    "source": r["source"],
                    "target": r["target"] if r["status"] == "matched" else "",
                    "status": r["status"],
                    "matched_entry": r.get("matched_entry") or "",
                    "note": r.get("collision", ""),
                }
                for r in plan
            ])
            zf.writestr("rename_log.csv", log_df.to_csv(index=False))
        zip_buf.seek(0)
        st.download_button(
            "⬇ Download ZIP",
            data=zip_buf,
            file_name="renamed_glasses.zip",
            mime="application/zip",
            key="ren_dl",
        )
        st.success(f"ZIP ready — {len(matched_rows)} files included.")

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

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["📊 Data Validation", "🖼️ Image Checker", "🧬 Syntax & Duplicates", "🎨 Color Checker", "🚫 Banned Brands", "🏷️ Image Renamer"])

    # ------------------------------------------
    # TAB 1: DATA VALIDATION
    # ------------------------------------------
    with tab1:
        # Keywords used to match required columns in user file
        # (handles line breaks / whitespace in headers)
        REQUIRED_COLUMN_KEYWORDS = [
            "Glasses name",
            "Meta description",
            "XML description",
            "Combination",
            "Barcode",
            "Glasses type ID",
            "Manufacturer ID",
            "temple length ID",
            "lens height ID",
            "lens width ID",
            "bridge ID",
            "Glasses shape ID",
            "frame type ID",
            "Frame Colour ID",
            "Temple Colour ID",
            "main material ID",
            "gendre ID",
            "Items type ID",
            "Items packing ID",
            "Glasses contain ID",
            "Glasses model ID",
            "color code ID",
            "Brand ID",
            "HS Code",
            "Item description",
            "Case length",
            "Case height",
            "Case width",
            "Case weight",
            "Glasses weight",
            "origin country",
            "Producing company ID",
        ]

        # Columns only required for Sunglasses (detected from Meta description)
        SUNGLASSES_REQUIRED_KEYWORDS = [
            "lens Colour ID",
            "lens material ID",
            "lens effect ID",
            "Sunglasses filter ID",
        ]

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
        unmapped_pairs = []
        user_cols = list(user_df.columns)
        master_cols = list(master_df.columns)
        for mk, uk in IDEAL_PAIRS.items():
            rmc = next((c for c in master_cols if mk in c), None)
            ruc = next((c for c in user_cols if uk in c), None)
            if rmc and ruc:
                active_map[rmc] = ruc
            else:
                unmapped_pairs.append((mk, uk, rmc, ruc))

        st.write(f"🔗 Mapped **{len(active_map)}** / {len(IDEAL_PAIRS)} columns.")

        if unmapped_pairs:
            with st.expander(f"⚠️ {len(unmapped_pairs)} unmapped column pair(s)"):
                for mk, uk, rmc, ruc in unmapped_pairs:
                    missing = []
                    if not rmc: missing.append(f"master: `{mk}`")
                    if not ruc: missing.append(f"user file: `{uk}`")
                    st.write(f"- **{mk}** ← → **{uk}** — missing in {', '.join(missing)}")

        # Match required columns to actual user file columns
        required_col_map = {}
        for keyword in REQUIRED_COLUMN_KEYWORDS:
            matched = next((c for c in user_cols if keyword.lower() in c.lower()), None)
            if matched:
                required_col_map[keyword] = matched

        # Match sunglasses-only required columns
        sunglasses_col_map = {}
        for keyword in SUNGLASSES_REQUIRED_KEYWORDS:
            matched = next((c for c in user_cols if keyword.lower() in c.lower()), None)
            if matched:
                sunglasses_col_map[keyword] = matched

        # Find the Meta description column (used to detect glasses type)
        meta_col = next((c for c in user_cols if "meta description" in c.lower()), None)

        all_required_count = len(REQUIRED_COLUMN_KEYWORDS) + len(SUNGLASSES_REQUIRED_KEYWORDS)
        all_found_count = len(required_col_map) + len(sunglasses_col_map)
        st.write(f"🔒 Found **{all_found_count}** / {all_required_count} required columns (incl. {len(sunglasses_col_map)} sunglasses-only).")

        # Show unmatched required columns as warning
        unmatched = [kw for kw in REQUIRED_COLUMN_KEYWORDS if kw not in required_col_map]
        unmatched += [f"{kw} (sunglasses only)" for kw in SUNGLASSES_REQUIRED_KEYWORDS if kw not in sunglasses_col_map]
        if unmatched:
            with st.expander(f"⚠️ {len(unmatched)} required columns not found in file"):
                for u in unmatched:
                    st.write(f"- `{u}`")

        if st.button("🚀 Run Validation", type="primary"):
            mistakes = []
            empty_cells = []

            # --- EMPTY REQUIRED FIELDS CHECK ---
            for idx, row in user_df.iterrows():
                # Detect glasses type from Meta description
                meta_val = str(row[meta_col]).strip().lower() if meta_col else ""
                is_sunglasses = meta_val.startswith("sunglasses")

                # Always-required columns
                for keyword, u_col in required_col_map.items():
                    raw_val = str(row[u_col]).strip()
                    if raw_val.lower() in ['nan', '', 'none']:
                        empty_cells.append({"Row": idx+2, "Column": u_col, "Error": "Empty Required Field"})

                # Sunglasses-only required columns
                if is_sunglasses:
                    for keyword, u_col in sunglasses_col_map.items():
                        raw_val = str(row[u_col]).strip()
                        if raw_val.lower() in ['nan', '', 'none']:
                            empty_cells.append({"Row": idx+2, "Column": u_col, "Error": "Empty Required Field (Sunglasses)"})

            # --- CONTENT VALIDATION ---
            # Build case-insensitive lookup map: lowercase -> exact master casing
            valid_values_ci = {}
            for m_col in active_map.keys():
                raw = master_df[m_col].dropna().astype(str)
                exploded = raw.str.split(r',+').explode().str.strip()
                mapping = {}
                for v in exploded:
                    if v and v.lower() not in mapping:
                        mapping[v.lower()] = v  # keep first-seen casing from master
                valid_values_ci[m_col] = mapping

            # --- WHITESPACE CHECK (all columns) ---
            import re
            # Matches ANY whitespace char incl. NBSP, tab, etc.
            WS_CHARS = r"[\s ​ ﻿]"
            for idx, row in user_df.iterrows():
                for u_col in user_cols:
                    raw_val = str(row[u_col])
                    if raw_val.lower() in ['nan', '', 'none']: continue

                    ws_issues = []
                    # Leading/trailing: any whitespace char (incl. NBSP)
                    if re.match(WS_CHARS, raw_val): ws_issues.append("Leading Space")
                    if re.search(WS_CHARS + r"$", raw_val): ws_issues.append("Trailing Space")
                    # Double whitespace anywhere
                    if re.search(WS_CHARS + r"{2,}", raw_val): ws_issues.append("Double Spaces")
                    # Whitespace around pipe separator
                    if re.search(r"\|\s|\s\|", raw_val): ws_issues.append("Space around Separator")
                    # NBSP anywhere (often invisible)
                    if " " in raw_val: ws_issues.append("Non-Breaking Space (NBSP)")

                    for ws in ws_issues:
                        # Show raw value with whitespace made visible
                        visible = raw_val.replace(" ", "[NBSP]").replace("\t", "[TAB]")
                        mistakes.append({"Row": idx+2, "Column": u_col, "Error": "Whitespace", "Value": ws, "Content": visible})

            # --- CONTENT VALIDATION (mapped columns only) ---
            progress_bar = st.progress(0)
            total_rows = len(user_df)
            for idx, row in user_df.iterrows():
                if idx % 10 == 0: progress_bar.progress(min(idx / total_rows, 1.0))
                for m_col, u_col in active_map.items():
                    raw_val = str(row[u_col])
                    if raw_val.lower() in ['nan', '', 'none']: continue

                    clean_val = raw_val.strip()
                    parts = [v.strip() for v in clean_val.split('|')]
                    ci_map = valid_values_ci[m_col]
                    for p in parts:
                        if not p:
                            continue
                        if p.lower() not in ci_map:
                            mistakes.append({"Row": idx+2, "Column": u_col, "Error": "Invalid Content", "Value": p, "Content": raw_val, "Allowed": list(ci_map.values())[:3]})
                        elif p != ci_map[p.lower()]:
                            mistakes.append({"Row": idx+2, "Column": u_col, "Error": "Case Mismatch", "Value": p, "Content": raw_val, "Expected": ci_map[p.lower()]})

            progress_bar.empty()

            # --- DISPLAY RESULTS ---
            # Empty fields section
            if empty_cells:
                st.error(f"🔒 Found {len(empty_cells)} empty required fields!")
                st.dataframe(pd.DataFrame(empty_cells), use_container_width=True)
            else:
                st.success("✅ All required fields are filled!")

            st.divider()

            # Content validation section
            if mistakes:
                st.error(f"Found {len(mistakes)} content/whitespace issues!")
                st.dataframe(pd.DataFrame(mistakes), use_container_width=True)
            else:
                st.balloons(); st.success("✅ Content validation clean!")

    # ------------------------------------------
    # TAB 2: IMAGE CHECKER
    # ------------------------------------------
    with tab2:
        st.subheader("🖼️ Image Name vs. Excel Checker", help="To get images paths go to the folder containing images -> Select all (Ctrl + A) -> Right click -> Copy as paths")

        target_col_name = "Glasses name"
        found_col = next((c for c in user_df.columns if target_col_name.lower() in c.lower()), user_df.columns[0])
        st.write(f"📂 **Using Excel Column:** `{found_col}`")

        # Excel names: preserve order, track duplicates with row numbers
        excel_names_list = []  # (row_num, original_name, normalized_name)
        for idx, val in user_df[found_col].dropna().astype(str).items():
            clean = val.strip()
            if clean.lower() in ['nan', '', 'none']: continue
            excel_names_list.append((idx + 2, clean, clean.lower()))

        excel_total = len(excel_names_list)
        excel_unique = {n[2] for n in excel_names_list}

        # Excel duplicates (same name in multiple rows)
        from collections import Counter
        excel_name_counts = Counter(n[2] for n in excel_names_list)
        excel_duplicates = {name: cnt for name, cnt in excel_name_counts.items() if cnt > 1}

        st.write(f"📋 **{excel_total}** names in Excel column (**{len(excel_unique)}** unique).")

        pasted_paths = st.text_area("Paste File Paths Here", height=300)

        if st.button("🔍 Check Images"):
            if not pasted_paths.strip():
                st.warning("Paste paths first!")
            else:
                # Parse pasted paths
                lines = [l.strip() for l in pasted_paths.split('\n') if l.strip()]
                img_entries = []  # list of normalized names (with duplicates preserved)
                for line in lines:
                    fname = line.replace('"', '').split('\\')[-1].split('/')[-1]
                    cname = fname.rsplit('.', 1)[0] if '.' in fname else fname
                    norm = cname.replace('_', '/').strip().lower()
                    if norm:
                        img_entries.append(norm)

                img_total = len(img_entries)
                img_set = set(img_entries)

                # Image duplicates (same image filename pasted multiple times)
                img_counts = Counter(img_entries)
                img_duplicates = {name: cnt for name, cnt in img_counts.items() if cnt > 1}

                # Match logic
                matched = excel_unique & img_set
                missing = [n for n in excel_names_list if n[2] not in img_set]  # rows missing image
                extra = sorted(img_set - excel_unique)  # images without matching name

                # ---- SUMMARY ----
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("Names in Excel", excel_total)
                c2.metric("Images Provided", img_total)
                c3.metric("Matched", f"{len(matched)} / {len(excel_unique)}")

                # ---- MISSING IMAGES ----
                if missing:
                    st.error(f"❌ {len(missing)} name(s) without image")
                    st.dataframe(
                        pd.DataFrame([{"Row": r, "Name": n} for r, n, _ in missing]),
                        use_container_width=True
                    )
                else:
                    st.success("✅ Every name has a matching image.")

                # ---- DUPLICATE IMAGE PATHS ----
                if img_duplicates:
                    st.warning(f"⚠️ {len(img_duplicates)} duplicate image path(s) detected")
                    st.dataframe(
                        pd.DataFrame([{"Image": k, "Times Pasted": v} for k, v in img_duplicates.items()]),
                        use_container_width=True
                    )

                # ---- DUPLICATE NAMES IN EXCEL ----
                if excel_duplicates:
                    with st.expander(f"⚠️ {len(excel_duplicates)} duplicate name(s) in Excel"):
                        st.dataframe(
                            pd.DataFrame([{"Name": k, "Occurrences": v} for k, v in excel_duplicates.items()]),
                            use_container_width=True
                        )

                # ---- EXTRA IMAGES ----
                if extra:
                    with st.expander(f"⚠️ {len(extra)} extra image(s) with no matching Excel name"):
                        st.dataframe(pd.DataFrame(extra, columns=["Extra Image"]), use_container_width=True)

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

                # Count how many times each name appears within the uploaded file itself
                from collections import Counter
                clean_series = user_df[target_user_col].dropna().astype(str).str.strip()
                clean_series = clean_series[~clean_series.str.lower().isin(["nan", "", "none"])]
                in_file_counts = Counter(clean_series.tolist())

                report = []
                duplicate_indices = []  # original df indices of duplicate rows (either kind)

                for idx, name in user_df[target_user_col].dropna().astype(str).items():
                    clean_name = name.strip()
                    row_num = idx + 2

                    # In-file duplicate (same name appears in more than one row)
                    if in_file_counts.get(clean_name, 0) > 1:
                        report.append({"Row": row_num, "Name": clean_name, "Issue": "🔁 IN-FILE DUPLICATE", "Details": f"Appears {in_file_counts[clean_name]}× in this file."})
                        duplicate_indices.append(idx)

                    if clean_name in valid_names_set:
                        report.append({"Row": row_num, "Name": clean_name, "Issue": "❌ DUPLICATE", "Details": "Name already exists in master file."})
                        duplicate_indices.append(idx)
                        continue

                    my_skel = get_skeleton(clean_name)
                    if my_skel not in valid_skeletons:
                        report.append({"Row": row_num, "Name": clean_name, "Issue": "⚠️ SUSPICIOUS SYNTAX", "Details": f"New Pattern: {my_skel}"})

                if report:
                    st.error(f"Found {len(report)} Issues!")
                    res_df = pd.DataFrame(report)

                    def _style_issue(x):
                        if x == "❌ DUPLICATE":
                            return 'background-color: #ffcccc; color: black;'  # red — in master
                        if x == "🔁 IN-FILE DUPLICATE":
                            return 'background-color: #ffd9b3; color: black;'  # orange — within file
                        return 'background-color: #fff4cc; color: black;'      # yellow — syntax

                    st.dataframe(res_df.style.map(_style_issue, subset=['Issue']), use_container_width=True)

                    # Export duplicate rows (in-file + master) in the original file format
                    dup_idx_unique = sorted(set(duplicate_indices))
                    if dup_idx_unique:
                        export_df = user_df.loc[dup_idx_unique]
                        buf = io.BytesIO()
                        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                            export_df.to_excel(writer, index=False)
                        buf.seek(0)
                        st.download_button(
                            f"⬇ Download {len(dup_idx_unique)} duplicate rows (same format)",
                            data=buf,
                            file_name="duplicate_items.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dup_export",
                        )
                    else:
                        st.info("No duplicate rows to export (only suspicious-syntax issues found).")
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

    # ------------------------------------------
    # TAB 5: BANNED BRANDS
    # ------------------------------------------
    with tab5:
        st.subheader("🚫 Banned Brands Checker")
        st.info("Checks which brands in your file are banned on specific websites. Alensa.ua shows brands that are **not** on the allowed list.")

        # ---- BANNED / ALLOWED LISTS ----
        SITE_BANNED = {
            # ── Czech sites ──
            "Čočky-kontaktni.cz": {
                "type": "banned",
                "brands": {"Calvin Klein", "Dolce & Gabbana", "Chiara Ferragni", "Jimmy Choo", "Lacoste", "Marisio", "Missoni", "Montblanc", "Persol", "Meller", "Celine"},
            },
            "Čočky-online.cz": {
                "type": "banned",
                "brands": {"Gucci", "Chiara Ferragni", "Christian Dior", "Julbo", "Just Cavalli", "Montblanc", "Meller", "Celine"},
            },
            "Čočky-optika.cz": {
                "type": "banned",
                "brands": {"Givenchy", "Havaianas", "Christian Dior", "Julbo", "Just Cavalli", "Kate Spade", "Meller", "Celine"},
            },
            "Alensa.cz": {
                "type": "banned",
                "brands": {"Meller", "Celine"},
            },
            "Kontaktni.cz": {
                "type": "banned",
                "brands": {"Meller", "Celine"},
            },
            # ── Poland ──
            "Alensa.pl": {
                "type": "banned",
                "brands": {"Hawkers", "Meller", "Celine"},
            },
            # ── Greece ──
            "Alensa.gr": {
                "type": "banned",
                "brands": {"Hawkers", "Meller", "Celine"},
            },
            "Mataki.gr": {
                "type": "banned",
                "brands": {"Hawkers", "Meller", "Celine"},
            },
            # ── France ──
            "Alensa.fr": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Spain ──
            "Alensa.es": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            "Lentes-de-contacto.es": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            "Lentes-shop.es": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Italy ──
            "Alensa.it": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            "Adrialenti.it": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            "Lenti-ottica.it": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Croatia ──
            "Alensa.hr": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            "Adrialece.hr": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Slovenia ──
            "Alensa.si": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            "Moje-lece.si": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Serbia ──
            "Alensa.rs": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Bosnia ──
            "Adrialece.ba": {
                "type": "banned",
                "brands": {"Hawkers", "Celine"},
            },
            # ── Portugal ──
            "Alensa.pt": {
                "type": "banned",
                "brands": {"Meller", "Celine"},
            },
            # ── Romania ──
            "Contact-lentile.ro": {
                "type": "banned",
                "brands": {"Ana Hickman", "Morel", "Celine"},
            },
            "Videt.ro": {
                "type": "banned",
                "brands": {"Ana Hickman", "Morel", "Celine"},
            },
            "Xlentile.ro": {
                "type": "banned",
                "brands": {"Ana Hickman", "Morel", "Celine"},
            },
            # ── Madagascar ──
            "vallis.mg": {
                "type": "banned",
                "brands": {"Desiree", "Celine"},
            },
            # ── International ──
            "Adrial.eu": {
                "type": "banned",
                "brands": {"Desiree", "Celine"},
            },
            "Alensa.com": {
                "type": "banned",
                "brands": {"Hawkers", "Meller", "Celine"},
            },
            # ── Norway ──
            "Alensa.no": {
                "type": "banned",
                "brands": {
                    "Adidas", "Alexander McQueen", "Balenciaga", "Beron", "Boss by Hugo Boss",
                    "Burberry", "Calvin Klein", "Carolina Herrera", "Carrera", "Celine",
                    "Chloe", "Christian Dior", "David Beckham", "Dolce & Gabbana", "Dsquared2",
                    "Giorgio Armani", "Gucci", "Hugo by Hugo Boss", "Jimmy Choo", "Kate Spade",
                    "Love Moschino", "Marc Jacobs", "Maui Jim", "Max Mara", "Missoni",
                    "Miu Miu", "Montblanc", "Moschino", "Oakley", "Persol",
                    "Police", "Polo Ralph Lauren", "Prada", "Prada Linea Rossa", "Ralph Lauren",
                    "Ray-Ban", "Saint Laurent", "Serengeti", "Swarovski", "Tiffany & Co.",
                    "Tom Ford", "Tommy Hilfiger", "Versace", "Victoria Beckham",
                },
            },
            # ── Ukraine ──
            "Alensa.ua": {
                "type": "allowed",
                "brands": {"Crullé", "Marisio", "Kimikado", "Lewish", "Beron", "Válle", "Polaroid"},
            },
        }

        # Find Brand column in user file
        brand_col = next((c for c in user_df.columns if "brand" in c.lower() and "id" not in c.lower()), None)
        if not brand_col:
            brand_col = next((c for c in user_df.columns if "brand" in c.lower()), None)

        if not brand_col:
            st.error("❌ No Brand column found in the uploaded file.")
        else:
            st.write(f"📂 **Using column:** `{brand_col}`")

            # Get unique brands from user file (handle pipe-separated values)
            user_brands_raw = user_df[brand_col].dropna().astype(str).str.strip()
            user_brands = set()
            for val in user_brands_raw:
                for b in val.split('|'):
                    b = b.strip()
                    if b and b.lower() not in ['nan', '', 'none']:
                        user_brands.add(b)

            st.write(f"🏷️ Found **{len(user_brands)}** unique brands in file.")

            # ---- CHECK EACH SITE ----
            any_issues = False
            for site, config in SITE_BANNED.items():
                site_type = config["type"]
                site_brands = config["brands"]

                if site_type == "banned":
                    # Case-insensitive match
                    flagged = sorted([b for b in user_brands if b.lower() in {s.lower() for s in site_brands}])
                    allowed_present = None
                    label = "banned"
                else:
                    # Allowed list — flag brands NOT in the allowed set
                    allowed_lower = {s.lower() for s in site_brands}
                    flagged = sorted([b for b in user_brands if b.lower() not in allowed_lower])
                    allowed_present = sorted([b for b in user_brands if b.lower() in allowed_lower])
                    label = "not allowed"

                if allowed_present is not None:
                    # Allowlist site — combine both sections into one card
                    header = f"⚠️ **{site}** — {len(flagged)} not allowed / {len(allowed_present)} allowed" if flagged else f"✅ **{site}** — {len(allowed_present)} allowed brand(s) present"
                    if flagged:
                        any_issues = True
                    with st.expander(header, expanded=bool(flagged)):
                        if flagged:
                            st.markdown("**🚫 Not allowed:**")
                            cols = st.columns(4)
                            for i, brand in enumerate(flagged):
                                cols[i % 4].error(brand)
                            st.divider()
                        st.markdown("**✅ Allowed:**")
                        cols = st.columns(4)
                        for i, brand in enumerate(allowed_present):
                            cols[i % 4].success(brand)
                elif flagged:
                    any_issues = True
                    with st.expander(f"⚠️ **{site}** — {len(flagged)} brand(s) {label}", expanded=True):
                        cols = st.columns(4)
                        for i, brand in enumerate(flagged):
                            cols[i % 4].error(brand)
                else:
                    st.success(f"✅ **{site}** — No issues")

            if not any_issues:
                st.balloons()
                st.success("✅ No banned or restricted brands found across all sites!")

    # ------------------------------------------
    # TAB 6: IMAGE RENAMER
    # ------------------------------------------
    with tab6:
        render_image_renamer(user_df)
