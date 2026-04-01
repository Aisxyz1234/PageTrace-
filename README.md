# PDF Page Finder

Upload a PDF book and a small image snippet cropped from any page.  
The app scans every page and tells you **which page the snippet belongs to**, with a live preview and match confidence score.

## How it works

1. Each PDF page is rendered to a grayscale image (at 150 DPI) using PyMuPDF.
2. OpenCV `matchTemplate` (normalised cross-correlation) slides your snippet across every page image.
3. The page with the highest match score wins.
4. The matched page is shown with a green bounding box around where the snippet was found.

---

## Setup (Visual Studio Code)

### 1. Prerequisites
- Python 3.10 or newer  
- Visual Studio Code with the Python extension

### 2. Create a virtual environment (recommended)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note for Linux**: `tkinter` may need a separate install:
> ```bash
> sudo apt install python3-tk
> ```

### 4. Run
- Press **F5** in VS Code (uses `.vscode/launch.json`), or
- Run from terminal:
  ```bash
  python app.py
  ```

---

## Usage

1. Click **Choose PDF…** → select your book PDF.
2. Click **Choose Image…** → select a screenshot or crop from any page.
3. Click **🔍 Find Page**.
4. The app scans all pages (progress bar shown) and displays:
   - The **page number**
   - A **confidence %** (≥ 60% = reliable match)
   - A **highlighted preview** of the matched page

---

## Tips for best results

| Do this | Avoid this |
|---|---|
| Crop a clear, text-rich region | Tiny snippets (< 50×50 px) |
| Use PNG screenshots for clean edges | Blurry phone photos |
| Include unique content (not page borders) | Pure white or blank areas |
| Use 150–200 DPI screenshots | Heavily compressed JPEGs |

---

## Dependencies

| Package | Purpose |
|---|---|
| `PyMuPDF` | Render PDF pages to images |
| `opencv-python` | Template matching (image search) |
| `Pillow` | Display images in the GUI |
| `numpy` | Array operations |
| `tkinter` | GUI (included in Python standard library) |

---

## Accuracy notes

- Works best with **digital/text PDFs** (not scanned books).
- For scanned books, ensure your snippet comes from the same scan (same DPI).
- If confidence is below 40%, try a larger or higher-quality snippet.