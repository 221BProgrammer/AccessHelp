# src/text/pdf_reader.py
import PyPDF2


class PDFReader:
    """
    Extracts text from PDF files.

    BUG FIXES
    ---------
    1. page.extract_text() returns None for scanned/image-only PDFs.
       Concatenating None raised TypeError. Now guarded with `or ""`.
    2. No error handling — corrupt or password-protected PDFs crashed
       the whole app. Now caught and returned as an error message string
       so the UI can display it gracefully.
    3. Empty result now returns a clear message instead of a silent
       empty string that confused users and the summarizer.
    """

    def extract_text(self, file) -> str:
        """
        Extract all text from a PDF file or file-like object.

        Parameters
        ----------
        file : str or file-like object
            Path to a PDF file, or a Streamlit UploadedFile object.

        Returns
        -------
        str
            Extracted text, or an explanatory message if extraction failed.
        """
        try:
            pdf  = PyPDF2.PdfReader(file)

            # Fix 1: check for password protection
            if pdf.is_encrypted:
                return (
                    "⚠️ This PDF is password-protected and cannot be read. "
                    "Please provide an unprotected PDF."
                )

            pages_text = []
            for page_num, page in enumerate(pdf.pages, start=1):
                # Fix 1: extract_text() returns None for image-only pages
                raw = page.extract_text()
                if raw:
                    pages_text.append(raw.strip())
                # (silently skip image-only pages rather than crashing)

            if not pages_text:
                # Fix 3: clear message instead of silent empty string
                return (
                    "⚠️ No readable text found in this PDF. "
                    "It may be a scanned image PDF. "
                    "Try using the OCR Scanner feature instead."
                )

            return "\n\n".join(pages_text)

        # Fix 2: handle corrupt / malformed PDFs
        except PyPDF2.errors.PdfReadError as e:
            return f"⚠️ Could not read PDF: {e}. The file may be corrupt."
        except Exception as e:
            return f"⚠️ Unexpected error reading PDF: {e}"