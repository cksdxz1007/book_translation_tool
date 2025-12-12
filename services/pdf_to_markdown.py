import fitz  # PyMuPDF
import logging
import os

logger = logging.getLogger(__name__)

def convert_pdf_to_markdown(pdf_path, start_page=None, end_page=None):
    """
    Converts a PDF file to a single Markdown string using PyMuPDF (fitz).
    Attempts basic structure detection (paragraphs, simple headers based on font size).

    Args:
        pdf_path (str): Path to the PDF file.
        start_page (int, optional): The 1-indexed start page. Defaults to first page.
        end_page (int, optional): The 1-indexed end page (inclusive). Defaults to last page.

    Returns:
        str: The converted Markdown text, or None if an error occurs.
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"Error opening PDF file '{pdf_path}': {e}")
        return None

    markdown_text = ""
    num_pages = doc.page_count

    # Validate and set page range
    s_page = (start_page - 1) if start_page and 1 <= start_page <= num_pages else 0
    e_page = (end_page) if end_page and start_page <= end_page <= num_pages else num_pages
    if e_page > num_pages: e_page = num_pages # ensure end_page is not out of bounds
    if s_page >= e_page: # if start page is beyond end page after adjustment, or no valid pages
        logger.warning(f"Invalid page range specified (start: {start_page}, end: {end_page}) for PDF with {num_pages} pages. No pages will be processed.")
        doc.close()
        return ""

    logger.info(f"Converting PDF '{pdf_path}' from page {s_page + 1} to {e_page} to Markdown.")

    # Heuristic parameters (these might need tuning)
    # Base font size for considering something a paragraph (can be an average or common size)
    # For now, we'll look at size variations
    # last_font_size = 0
    # paragraph_spacing_threshold = 5 # Arbitrary threshold for vertical spacing between blocks to indicate new paragraph
    # last_y1 = 0

    for page_num in range(s_page, e_page):
        page = doc.load_page(page_num)
        blocks = page.get_text("blocks", sort=True) # Get text blocks, sorted by y-coordinate
        markdown_text += f"<!-- Page {page_num + 1} -->\n\n" # Add a comment for page number

        # Simplistic approach: treat each block as a paragraph for now.
        # More advanced: analyze font size/style for headers, line spacing for paragraphs etc.
        current_paragraph_lines = []
        last_block_y1 = 0
        min_line_height_for_new_paragraph = 10 # Heuristic for paragraph break from block spacing

        for i, block in enumerate(blocks):
            x0, y0, x1, y1, text_content, block_no, block_type = block
            text_content = text_content.strip()
            if not text_content:
                continue

            # Attempt to detect if this block starts a new paragraph based on vertical spacing
            # This is a very basic heuristic.
            if i > 0 and (y0 - last_block_y1) > min_line_height_for_new_paragraph:
                if current_paragraph_lines:
                    markdown_text += " ".join(current_paragraph_lines).replace('\n', ' ') + "\n\n"
                    current_paragraph_lines = []
            
            current_paragraph_lines.append(text_content.replace('\n', ' ')) # Replace newlines within a block with spaces
            last_block_y1 = y1

        # Add any remaining paragraph
        if current_paragraph_lines:
            markdown_text += " ".join(current_paragraph_lines).replace('\n', ' ') + "\n\n"

    doc.close()
    return markdown_text.strip()

if __name__ == '__main__':
    # Example Usage (for testing this module directly)
    logging.basicConfig(level=logging.INFO)
    # Create a dummy PDF for testing if you don't have one handy
    # Or replace with a path to an actual PDF
    test_pdf_path = "test_document.pdf" # Replace with your test PDF path
    
    # Check if test_pdf_path exists, otherwise skip example
    if os.path.exists(test_pdf_path):
        logger.info(f"Testing PDF to Markdown conversion with: {test_pdf_path}")
        md_output = convert_pdf_to_markdown(test_pdf_path, start_page=1, end_page=1)
        if md_output:
            print("\n--- Markdown Output ---")
            print(md_output)
            print("\n-----------------------")
            
            # Save to a file for inspection
            with open("converted_output.md", "w", encoding="utf-8") as f:
                f.write(md_output)
            logger.info("Saved Markdown output to converted_output.md")
        else:
            logger.error("Markdown conversion failed or produced no output.")
    else:
        logger.warning(f"Test PDF file '{test_pdf_path}' not found. Skipping example usage.")
        logger.info("To test, create a PDF named 'test_document.pdf' or change the path in the script.") 