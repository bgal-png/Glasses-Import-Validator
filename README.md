# 👓 Glasses Import Validator

**A robust quality assurance tool for validating glasses inventory data before import.**

## 🚀 Features

This application is divided into three powerful modules:

### 1. 📊 Data Validation (Tab 1)
* **Indestructible Loader:** Safely loads Master Data from Excel or CSV, handling encoding and separator errors automatically.
* **Smart Mapping:** Automatically detects and maps user columns to system IDs.
* **Whitespace Detective:** Flags invisible leading/trailing spaces and double spaces.
* **Format Checker:** Ensures data uses the correct separators (Pipes `|` vs Commas `,`).

### 2. 🖼️ Image Audit (Tab 2)
* **Path Cleaner:** Takes raw file paths (e.g., `C:\Users\...\Image.jpg`) and converts them to standardized filenames.
* **Orphan Check:** Identifies images that have no matching product in the Excel file.
* **Missing Check:** Identifies products in Excel that are missing an image.

### 3. 🧬 Syntax & Duplicate Guard (Tab 3)
* **Surgical Loader:** Rapidly loads the naming history database using memory-optimized techniques.
* **Duplicate Detection:** Prevents re-importing names that already exist.
* **Pattern Recognition:** Learns the "Skeleton" of valid names (e.g., `Ray-Ban 3025`) and flags any new or suspicious naming conventions (e.g., `ray ban 3025`).

## 🛠️ How to Use

1.  **Upload Master Files:** Ensure `master_clean.xlsx` and `name_master_clean.xlsx` are in the root folder.
2.  **Upload User File:** Drag and drop your new import Excel sheet.
3.  **Run Checks:** Go through Tabs 1, 2, and 3 in order.
4.  **Fix Errors:** Only export/upload your file when all tabs show **Green Success Balloons**.

---
*Built with Python & Streamlit.*
