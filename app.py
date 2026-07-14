import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import cv2
import numpy as np
from PIL import Image, ImageTk
import fitz  # PyMuPDF


class PDFPageFinder:
    """Renders PDF pages and matches a query image snippet against them."""

    RENDER_DPI = 150 

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.page_count = len(self.doc)

    def _render_page(self, page_index: int) -> np.ndarray:
        """Render a PDF page to a grayscale numpy array."""
        page = self.doc[page_index]
        mat = fitz.Matrix(self.RENDER_DPI / 72, self.RENDER_DPI / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        return img

    def find_page(self, snippet_path: str, progress_callback=None):
        """
        Search all pages for the snippet image.
        Returns: (best_page_1indexed, score, match_location, page_image_bgr)
        """

        snippet_bgr = cv2.imread(snippet_path)
        if snippet_bgr is None:
            raise ValueError("Could not load snippet image. Check the file path.")

        snippet_gray = cv2.cvtColor(snippet_bgr, cv2.COLOR_BGR2GRAY)
        sh, sw = snippet_gray.shape

        best_score = -1
        best_page = -1
        best_loc = (0, 0)
        best_page_img = None

        for i in range(self.page_count):
            if progress_callback:
                progress_callback(i + 1, self.page_count)

            page_gray = self._render_page(i)
            ph, pw = page_gray.shape

            # Skip pages smaller than the snippet
            if ph < sh or pw < sw:
                continue

            # Template matching — TM_CCOEFF_NORMED gives 0..1 score
            result = cv2.matchTemplate(page_gray, snippet_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                best_page = i
                best_loc = max_loc
                best_page_img = page_gray  # keep for display

        if best_page == -1:
            raise RuntimeError("No pages could be compared (PDF may be too small).")

        # Convert best page to colour BGR for display
        best_page_bgr = cv2.cvtColor(best_page_img, cv2.COLOR_GRAY2BGR)

        # Draw a green rectangle around the match
        x, y = best_loc
        cv2.rectangle(best_page_bgr, (x, y), (x + sw, y + sh), (0, 200, 50), 3)

        return best_page + 1, best_score, best_loc, best_page_bgr

    def close(self):
        self.doc.close()


# ─────────────────────────────────────────────
#  GUI
# ─────────────────────────────────────────────

class App(tk.Tk):
    ACCENT = "#4F8EF7"
    BG = "#1E1E2E"
    CARD = "#2A2A3E"
    TEXT = "#E0E0F0"
    MUTED = "#888899"
    SUCCESS = "#4ADE80"
    WARN = "#FACC15"

    def __init__(self):
        super().__init__()
        self.title("PDF Page Finder")
        self.geometry("900x680")
        self.configure(bg=self.BG)
        self.resizable(True, True)

        self.pdf_path = tk.StringVar()
        self.snippet_path = tk.StringVar()
        self._finder: PDFPageFinder | None = None
        self._result_photo = None   # keep reference to avoid GC
        self._snippet_photo = None

        self._build_ui()

    # ── UI Construction ──────────────────────

    def _build_ui(self):
        # ── Header ──────────────────────────
        hdr = tk.Frame(self, bg=self.ACCENT, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📄  PDF Page Finder",
                 font=("Segoe UI", 18, "bold"),
                 bg=self.ACCENT, fg="white").pack()
        tk.Label(hdr, text="Upload a PDF book and a snippet — we'll find the page.",
                 font=("Segoe UI", 10), bg=self.ACCENT, fg="#D0DFFF").pack()

        # ── Two-column body ──────────────────
        body = tk.Frame(self, bg=self.BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)

        # Left panel — controls
        left = tk.Frame(body, bg=self.CARD, padx=16, pady=16, bd=0,
                        highlightthickness=1, highlightbackground="#3A3A5A")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._section(left, "① Select PDF Book")
        self._path_row(left, self.pdf_path, self._browse_pdf, "Choose PDF…")

        self._section(left, "② Select Image Snippet")
        self._path_row(left, self.snippet_path, self._browse_snippet, "Choose Image…")

        # Snippet preview
        self.snippet_label = tk.Label(left, bg=self.CARD, fg=self.MUTED,
                                      text="[snippet preview]",
                                      font=("Segoe UI", 9))
        self.snippet_label.pack(pady=(6, 0))

        # Search button
        self.search_btn = tk.Button(
            left, text="🔍  Find Page",
            font=("Segoe UI", 12, "bold"),
            bg=self.ACCENT, fg="white",
            activebackground="#3A78E0", activeforeground="white",
            relief="flat", cursor="hand2", pady=10,
            command=self._start_search
        )
        self.search_btn.pack(fill="x", pady=(20, 6))

        # Progress bar
        self.progress = ttk.Progressbar(left, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 6))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor=self.BG,
                        background=self.ACCENT, thickness=6)

        self.status_lbl = tk.Label(left, text="Ready.", font=("Segoe UI", 9),
                                   bg=self.CARD, fg=self.MUTED, wraplength=220,
                                   justify="left")
        self.status_lbl.pack(anchor="w")

        # Result box
        self._section(left, "③ Result")
        self.result_frame = tk.Frame(left, bg=self.BG, padx=10, pady=10,
                                     highlightthickness=1,
                                     highlightbackground="#3A3A5A")
        self.result_frame.pack(fill="x")
        self.page_lbl = tk.Label(self.result_frame, text="—",
                                 font=("Segoe UI", 28, "bold"),
                                 bg=self.BG, fg=self.SUCCESS)
        self.page_lbl.pack()
        tk.Label(self.result_frame, text="page number",
                 font=("Segoe UI", 9), bg=self.BG, fg=self.MUTED).pack()
        self.confidence_lbl = tk.Label(self.result_frame, text="",
                                       font=("Segoe UI", 9),
                                       bg=self.BG, fg=self.MUTED)
        self.confidence_lbl.pack()

        # Right panel — page preview
        right = tk.Frame(body, bg=self.CARD, padx=8, pady=8,
                         highlightthickness=1, highlightbackground="#3A3A5A")
        right.grid(row=0, column=1, sticky="nsew")
        tk.Label(right, text="Matched Page Preview",
                 font=("Segoe UI", 11, "bold"),
                 bg=self.CARD, fg=self.TEXT).pack(pady=(4, 6))

        self.preview_canvas = tk.Canvas(right, bg="#111122",
                                        highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.create_text(
            200, 200, text="Result will appear here.",
            fill=self.MUTED, font=("Segoe UI", 11), tags="placeholder"
        )

    def _section(self, parent, title):
        tk.Label(parent, text=title,
                 font=("Segoe UI", 10, "bold"),
                 bg=self.CARD, fg=self.TEXT).pack(anchor="w", pady=(12, 2))

    def _path_row(self, parent, var, cmd, btn_text):
        row = tk.Frame(parent, bg=self.CARD)
        row.pack(fill="x", pady=2)
        tk.Entry(row, textvariable=var, font=("Segoe UI", 9),
                 bg="#151525", fg=self.TEXT, insertbackground=self.TEXT,
                 relief="flat", bd=4).pack(side="left", fill="x", expand=True)
        tk.Button(row, text=btn_text, font=("Segoe UI", 9),
                  bg="#3A3A5A", fg=self.TEXT, relief="flat",
                  cursor="hand2", padx=8, command=cmd).pack(side="right")

    # ── File Browsing ────────────────────────

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select a PDF book",
            filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.pdf_path.set(path)
            self._status(f"PDF loaded: {os.path.basename(path)}")
            # Pre-load the finder
            if self._finder:
                self._finder.close()
            self._finder = PDFPageFinder(path)
            self._status(f"PDF loaded · {self._finder.page_count} pages")

    def _browse_snippet(self):
        path = filedialog.askopenfilename(
            title="Select snippet image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.tiff *.webp")])
        if path:
            self.snippet_path.set(path)
            self._show_snippet_preview(path)

    def _show_snippet_preview(self, path):
        img = Image.open(path)
        img.thumbnail((220, 120), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._snippet_photo = photo
        self.snippet_label.configure(image=photo, text="")

    # ── Search ───────────────────────────────

    def _start_search(self):
        pdf = self.pdf_path.get()
        snippet = self.snippet_path.get()

        if not pdf or not os.path.exists(pdf):
            messagebox.showwarning("Missing PDF", "Please select a valid PDF file first.")
            return
        if not snippet or not os.path.exists(snippet):
            messagebox.showwarning("Missing Snippet", "Please select a snippet image first.")
            return

        self.search_btn.configure(state="disabled", text="Searching…")
        self.page_lbl.configure(text="…", fg=self.WARN)
        self.confidence_lbl.configure(text="")
        self.progress["value"] = 0
        self._status("Searching…")

        # Run in background thread so UI stays responsive
        t = threading.Thread(target=self._search_worker, args=(pdf, snippet), daemon=True)
        t.start()

    def _search_worker(self, pdf, snippet):
        try:
            if self._finder is None or self._finder.pdf_path != pdf:
                if self._finder:
                    self._finder.close()
                self._finder = PDFPageFinder(pdf)

            def progress(current, total):
                pct = int(current / total * 100)
                self.after(0, self._update_progress, pct,
                           f"Scanning page {current} / {total}…")

            page_num, score, loc, page_img = self._finder.find_page(snippet, progress)

            self.after(0, self._show_result, page_num, score, page_img)

        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_progress(self, pct, msg):
        self.progress["value"] = pct
        self._status(msg)

    def _show_result(self, page_num, score, page_img_bgr):
        self.search_btn.configure(state="normal", text="🔍  Find Page")
        self.progress["value"] = 100

        confidence_pct = round(score * 100, 1)
        color = self.SUCCESS if confidence_pct >= 60 else self.WARN

        self.page_lbl.configure(text=str(page_num), fg=color)
        self.confidence_lbl.configure(
            text=f"Match confidence: {confidence_pct}%",
            fg=color
        )
        self._status(f"Done! Snippet found on page {page_num} "
                     f"(confidence {confidence_pct}%)")

        # Display on canvas
        self._draw_page_preview(page_img_bgr)

        if confidence_pct < 40:
            messagebox.showwarning(
                "Low Confidence",
                f"The best match is page {page_num}, but confidence is low "
                f"({confidence_pct}%).\n\nTry a larger or clearer snippet."
            )

    def _draw_page_preview(self, page_bgr):
        """Fit the matched page image into the preview canvas."""
        self.preview_canvas.update_idletasks()
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()
        if cw < 10 or ch < 10:
            cw, ch = 400, 500

        img_rgb = cv2.cvtColor(page_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        pil_img.thumbnail((cw - 10, ch - 10), Image.LANCZOS)

        photo = ImageTk.PhotoImage(pil_img)
        self._result_photo = photo

        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(
            cw // 2, ch // 2, anchor="center", image=photo
        )

    def _show_error(self, msg):
        self.search_btn.configure(state="normal", text="🔍  Find Page")
        self.progress["value"] = 0
        self.page_lbl.configure(text="✕", fg="#F87171")
        self._status(f"Error: {msg}")
        messagebox.showerror("Error", msg)

    def _status(self, msg: str):
        self.status_lbl.configure(text=msg)

    def on_close(self):
        if self._finder:
            self._finder.close()
        self.destroy()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
