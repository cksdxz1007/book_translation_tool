import argparse
import os
import logging
import sys

# --- Debug sys.path ---
print(f"Initial sys.path: {sys.path}")

# --- Path removal for testing ---
epub_optimizer_path = '/Users/cynningli/Desktop/epub_optimizer'
if epub_optimizer_path in sys.path:
    sys.path.remove(epub_optimizer_path)
    print(f"Temporarily removed {epub_optimizer_path} from sys.path for testing.")
print(f"sys.path after potential removal: {sys.path}")
# --- End Path removal ---

# Add project root to Python path to allow sibling module imports
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    print(f"Modified sys.path, added {PROJECT_ROOT}")
else:
    # If it's already there but not at the front, remove and re-add at front
    if sys.path[0] != PROJECT_ROOT:
        sys.path.remove(PROJECT_ROOT)
        sys.path.insert(0, PROJECT_ROOT)
        print(f"Modified sys.path, moved {PROJECT_ROOT} to front")
    else:
        print(f"Project root {PROJECT_ROOT} already at the front of sys.path")

# --- Debug sys.path ---
print(f"Final sys.path for imports: {sys.path}")
# --- End Debug ---

print("Attempting to import project modules (step 2: text_splitter, translator)...")
try:
    from text_splitter import get_pdf_page_count 
    print("Successfully imported from text_splitter.")
    from translator import TranslationService, translate_book
    print("Successfully imported from translator.")
    # from result_generator import merge_translated_chunks, save_result
    # from pdf_to_markdown import convert_pdf_to_markdown
    # from markdown_beautifier import beautify_markdown
    # from markdown_splitter import split_markdown_into_chunks
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import one or more project modules.")
    print(f"ImportError details: {e}")
    print(f"Python's current module search path (sys.path): {sys.path}")
    print(f"Current working directory (os.getcwd()): {os.getcwd()}")
    print(f"Project root (calculated as SCRIPT_DIR): {PROJECT_ROOT}")
    print("Details in original except block...")
    sys.exit(1)
print("If this point is reached without critical error, basic script structure and sys.path are likely okay for the active imports.")

# Placeholder for other modules not yet tested
# class TranslationService: pass # Now imported
# def translate_book(): pass # Now imported
# def get_pdf_page_count(): return 1 # Now imported
def merge_translated_chunks(): pass
def save_result(): pass
def convert_pdf_to_markdown(): pass
def beautify_markdown(): pass
def split_markdown_into_chunks(): return []


# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="CLI tool to translate PDF files with caching.")
    
    # File arguments
    parser.add_argument("--file_path", type=str, required=True, help="Path to the PDF file to translate.")
    parser.add_argument("--output_dir", type=str, default="cli_output_data", help="Directory to save translated files. Default: cli_output_data")

    # Cache specific arguments
    parser.add_argument("--cache_dir_name", type=str, default=".cache", 
                        help="Subdirectory name within output_dir for cache files. Default: .cache")
    parser.add_argument("--disable_cache", action='store_true', 
                        help="Disable using the cache entirely (neither read nor write). Overrides --force_translate for reading.")
    parser.add_argument("--force_translate", action='store_true', 
                        help="Force re-translation of all chunks, ignoring existing cache entries. New translations will still be cached unless --disable_cache is also set.")

    # Service configuration: either by name or by direct params
    group = parser.add_argument_group('Service Configuration (choose one method)')
    method_group = group.add_mutually_exclusive_group(required=True)
    method_group.add_argument("--service_config_name", type=str, 
                               help="Name of the service from ~/.config/manzh/services.json.")
    method_group.add_argument("--service_type", type=str,
                               help="Service type (e.g., ollama, siliconflow, openrouter, deepseek, openai_compatible_chat, third_party_completion). Required if not using service_config_name.")

    # Direct service parameters (used if --service_type is specified)
    parser.add_argument("--model_name", type=str, help="Model name for the service.")
    parser.add_argument("--api_key", type=str, help="API key for the service (if required).")
    parser.add_argument("--ollama_url", type=str, help="URL for Ollama service (if type is ollama).")
    parser.add_argument("--openai_base_url", type=str, help="Base URL for OpenAI-compatible services (e.g. SiliconFlow, OpenRouter).")
    parser.add_argument("--legacy_api_url", type=str, help="Full URL for legacy third-party completion services.")
    parser.add_argument("--prompt_template", type=str, help="Custom prompt template for translation.")

    # Translation parameters
    parser.add_argument("--source_lang", type=str, default="auto", help="Source language. Default: auto")
    parser.add_argument("--target_lang", type=str, default="Chinese", help="Target language. Default: Chinese")
    parser.add_argument("--start_page", type=int, default=1, help="Start page for translation (1-indexed). Default: 1")
    parser.add_argument("--end_page", type=int, help="End page for translation (1-indexed, inclusive). Default: all pages.")
    parser.add_argument("--max_markdown_chunk_size", type=int, default=2000, help="Maximum character size for Markdown chunks. Default: 2000")

    args = parser.parse_args()

    # Validate file path
    if not os.path.isfile(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        return

    # --- BEGINNING OF FILE CLEANUP LOGIC ---
    logger.info(f"Checking for and deleting existing output files in '{os.path.abspath(args.output_dir)}'...")
    original_pdf_basename_no_ext = os.path.splitext(os.path.basename(args.file_path))[0]
    
    # Determine page range string for filenames
    # Use total_pages for end_page if not specified, this needs to be fetched early or assumed for cleanup
    # For simplicity in cleanup, we might not have total_pages yet. 
    # If args.end_page is None, it means all pages. We need a placeholder or to fetch total_pages earlier.
    # Let's assume for now if end_page is None, we can't perfectly predict the old filename for deletion
    # unless we fetch total_pages. A safer approach is to list files and match pattern if end_page is dynamic.
    # However, since we usually specify it or it defaults, let's try to build the name.
    # For now, if end_page is not set, we won't attempt to delete specific translated files, only cache and debug.

    page_range_str = f"{args.start_page}-{args.end_page}" if args.end_page else f"{args.start_page}-all"
    
    # Build base names for different output files
    # Note: The actual end_page might differ if args.end_page is None and total_pages is used later.
    # This cleanup is best-effort based on provided args.start_page and args.end_page.
    # If args.end_page is None, the page_range_str will be like "1-all".
    # Later, when get_pdf_page_count is called, the actual end_page will be determined.
    # The filename for translated files includes this actual page range.
    # For cleanup, we will construct the stem based on args.start_page and args.end_page as they are *given*.
    # This means if args.end_page is None, we won't be able to perfectly match previously generated files
    # that used the *actual* total_pages in their name. We'll log this.

    if args.end_page is None:
        logger.warning("args.end_page is not specified. Cleanup of main .txt/.pdf files will be skipped as exact old filename cannot be determined without total page count.")
        # We can still clean up debug files and potentially the cache file if its naming is consistent.
        files_to_delete_stems = [] # No main files
    else:
        # Only attempt to delete main translated files if end_page is explicitly set.
        base_output_stem = f"{original_pdf_basename_no_ext}_translated_{args.start_page}-{args.end_page}_{args.target_lang}"
        files_to_delete_stems = [
            base_output_stem + ".txt",
            base_output_stem + ".pdf",
        ]

    # Add debug files
    files_to_delete_stems.extend([
        "debug_initial.md",
        "debug_beautified.md"
    ])

    for stem in files_to_delete_stems:
        file_to_delete = os.path.join(args.output_dir, stem)
        if os.path.isfile(file_to_delete): # Ensure it's a file, not a directory
            try:
                os.remove(file_to_delete)
                logger.info(f"Deleted existing file: {file_to_delete}")
            except OSError as e:
                logger.warning(f"Could not delete existing file: {file_to_delete}. Error: {e}")
        elif os.path.exists(file_to_delete): # It exists but is not a file (e.g. a directory with same name)
             logger.warning(f"Path exists but is not a file, skipping deletion: {file_to_delete}")

    # Cache file cleanup (its name doesn't depend on page range or target_lang)
    if not args.disable_cache: # Only try to delete cache if cache is potentially active
        cache_dir_to_check = os.path.join(args.output_dir, args.cache_dir_name)
        cache_file_to_delete = os.path.join(cache_dir_to_check, f"{os.path.basename(args.file_path)}.cache.json")
        if os.path.isfile(cache_file_to_delete):
            try:
                os.remove(cache_file_to_delete)
                logger.info(f"Deleted existing cache file: {cache_file_to_delete}")
            except OSError as e:
                logger.warning(f"Could not delete existing cache file: {cache_file_to_delete}. Error: {e}")
        # Note: We are not deleting the cache directory itself, only the specific cache file.
    # --- END OF FILE CLEANUP LOGIC ---

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    logger.info(f"Output will be saved to: {os.path.abspath(args.output_dir)}")

    # Determine cache file path
    cache_file_path = None
    original_pdf_basename = os.path.basename(args.file_path)
    if not args.disable_cache:
        # Construct cache path: <output_dir>/<cache_dir_name>/<original_pdf_basename>.cache.json
        specific_cache_dir = os.path.join(args.output_dir, args.cache_dir_name)
        # The _save_translation_cache function in translator.py will create specific_cache_dir if it doesn't exist.
        cache_file_path = os.path.join(specific_cache_dir, f"{original_pdf_basename}.cache.json")
        logger.info(f"Using cache file: {cache_file_path}")
        if args.force_translate:
            logger.info("Forcing re-translation, existing cache entries will be ignored for reading but cache will be updated.")
    else:
        logger.info("Cache is disabled for this run.")

    # Initialize TranslationService
    translation_service = None
    try:
        if args.service_config_name:
            logger.info(f"Initializing translation service using configuration: '{args.service_config_name}'")
            translation_service = TranslationService(
                service_name_from_config=args.service_config_name,
                default_source_language=args.source_lang, # CLI can override config's default lang
                default_target_language=args.target_lang  # CLI can override config's default lang
            )
            # If a custom prompt template is given via CLI, it overrides the one from config (if any) or the default
            if args.prompt_template:
                translation_service.prompt_template = args.prompt_template

        elif args.service_type:
            logger.info(f"Initializing translation service using direct parameters for type: '{args.service_type}'")
            translation_service = TranslationService(
                service_type=args.service_type,
                model_name=args.model_name,
                api_key=args.api_key,
                ollama_url=args.ollama_url,
                openai_compatible_base_url=args.openai_base_url,
                legacy_completion_api_url=args.legacy_api_url,
                custom_prompt_template=args.prompt_template,
                default_source_language=args.source_lang,
                default_target_language=args.target_lang
            )
        else:
            # This case should not be reached due to mutually_exclusive_group requirement,
            # but as a safeguard:
            logger.error("Must specify either --service_config_name or --service_type.")
            return

    except ValueError as e:
        logger.error(f"Error initializing TranslationService: {e}")
        return
    except Exception as e: # Catch any other unexpected errors during init
        logger.error(f"Unexpected error initializing TranslationService: {e}")
        return

    # PDF Processing
    try:
        total_pages = get_pdf_page_count(args.file_path)
        start_page = args.start_page
        end_page = args.end_page if args.end_page is not None else total_pages

        if not (1 <= start_page <= total_pages):
            logger.error(f"Start page ({start_page}) is out of range (1-{total_pages}).")
            return
        if not (start_page <= end_page <= total_pages):
            logger.error(f"End page ({end_page}) is out of range (start_page: {start_page} - total_pages: {total_pages}).")
            return
        
        logger.info(f"Processing PDF: '{args.file_path}', Pages: {start_page} to {end_page}")
        
        # --- New PDF to Markdown Processing Workflow ---
        logger.info("Step 1: Converting PDF to Markdown...")
        initial_markdown = convert_pdf_to_markdown(args.file_path, start_page=start_page, end_page=end_page)
        if not initial_markdown:
            logger.warning("PDF to Markdown conversion resulted in no content.")
            return
        logger.info(f"Initial Markdown length: {len(initial_markdown)}")

        logger.info("Step 2: Beautifying Markdown...")
        beautified_markdown = beautify_markdown(initial_markdown)
        if not beautified_markdown:
            logger.warning("Markdown beautification resulted in no content.")
            return
        logger.info(f"Beautified Markdown length: {len(beautified_markdown)}")
        
        # Save intermediate files for debugging if needed
        with open(os.path.join(args.output_dir, "debug_initial.md"), "w", encoding="utf-8") as f:
            f.write(initial_markdown)
        with open(os.path.join(args.output_dir, "debug_beautified.md"), "w", encoding="utf-8") as f:
            f.write(beautified_markdown)

        logger.info(f"Step 3: Splitting beautified Markdown into chunks (max size: {args.max_markdown_chunk_size})...")
        chunks = split_markdown_into_chunks(beautified_markdown, max_chunk_size=args.max_markdown_chunk_size)
        # --- End of New Workflow ---

        if not chunks:
            logger.warning("No text chunks extracted from the PDF for the specified page range after Markdown processing.")
            return
        logger.info(f"Extracted {len(chunks)} Markdown chunks for translation.")

    except Exception as e:
        logger.error(f"Error processing PDF file: {e}")
        return

    # Translation
    try:
        translated_chunks = translate_book(
            chunks,
            translation_service,
            target_language=args.target_lang,
            source_language=args.source_lang,
            cache_file_path=cache_file_path,         # Pass cache file path
            force_translate=args.force_translate,    # Pass force_translate flag
            original_pdf_filename=original_pdf_basename # Pass original PDF name for cache metadata
        )
        
        if not translated_chunks or all(not chunk or chunk.startswith("[CHUNK") for chunk in translated_chunks):
            logger.warning("Translation resulted in no valid content or only errors.")
            # Still try to save if there are error placeholders to see them in output
            if not any(chunk for chunk in translated_chunks if not chunk.startswith("[CHUNK")):
                 return # Exit if truly nothing but errors and no actual content

        merged_text = merge_translated_chunks(translated_chunks)
        
        # Generate output filename
        base_filename = os.path.splitext(os.path.basename(args.file_path))[0]
        output_file_stem = os.path.join(args.output_dir, f"{base_filename}_translated_{start_page}-{end_page}_{args.target_lang}")
        
        txt_path, pdf_path = save_result(merged_text, output_file_stem)
        
        logger.info(f"Translation complete!")
        logger.info(f"Translated text saved to: {txt_path}")
        logger.info(f"Translated PDF saved to: {pdf_path}")

    except Exception as e:
        logger.error(f"Error during translation or saving results: {e}")
        import traceback
        traceback.print_exc() # For more detailed error during development

if __name__ == "__main__":
    main() 