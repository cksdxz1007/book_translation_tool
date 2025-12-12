# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application for translating documents (PDF, ePub, Markdown, text) using multiple translation engines including BabelDOC for professional PDF translation and traditional text-based translation.

## Technology Stack

- **Backend Framework:** Flask + Blueprint modular architecture
- **Frontend Framework:** Vanilla JavaScript + jQuery
- **Database:** SQLite (configuration storage)
- **Package Manager:** uv (modern Python package manager)
- **Translation Engines:** Multi-engine support (OpenAI-compatible, Ollama, BabelDOC)

## Architecture Highlights

- ✅ Modular Blueprint design
- ✅ Frontend-backend separated API architecture
- ✅ Real-time progress tracking (Server-Sent Events)
- ✅ Encrypted configuration management
- ✅ Multi-format file support (PDF, EPUB, Markdown)

## Core Components

### Main Application Files
- **app.py** - Main Flask application with routes for PDF, ePub, and Markdown translation
- **translator.py** - Translation service abstraction supporting multiple providers
- **admin_routes.py** - Web-based configuration management interface
- **pdf_translator_babeldoc.py** - BabelDOC integration for professional PDF translation

### Configuration Management
- **config/manager.py** - SQLite-based secure configuration management with encryption
- **data/config.db** - SQLite database with encrypted service configurations
- **data/keys/master.key** - Encryption key for sensitive data

### Translation Engines
1. **BabelDOC Engine** (`pdf_translator_babeldoc.py`) - Professional PDF translation with layout preservation
2. **Traditional Engine** (`translator.py`) - Text-based translation for ePub/Markdown/PDF
3. **Format-Preserving Engine** - Maintains document structure for ePub/Markdown

## Flask Blueprint Structure

### Independent Blueprints (no /api prefix)
- **PDF Blueprint** (`/pdf`) - PDF translation page and file upload
- **Markdown Blueprint** (`/markdown`) - Markdown translation page and file upload
- **EPUB Blueprint** (`/epub`) - EPUB translation page and file upload

### API Blueprint (with /api prefix)
- **API Routes** (`/api/*`) - RESTful API endpoints for translation operations
- **Admin Blueprint** (`/admin/*`) - Web-based configuration management

### Key API Endpoints
- `POST /api/translate` - PDF translation API
- `POST /api/translate-markdown` - Markdown translation API
- `POST /api/translate-epub` - EPUB translation API
- `POST /api/reset-progress` - Reset translation progress
- `POST /api/abort-translation` - Abort translation
- `POST /api/clear-cache` - Clear cache
- `GET /api/download/<filename>` - Download translation results
- `POST /api/cleanup-files` - Cleanup files

## File Processing Pipeline

1. **Upload** → `uploads/` directory
2. **Parsing** → File-specific parsers (PDF, ePub, Markdown)
3. **Translation** → Selected translation engine
4. **Output** → `results/` directory with multiple formats

## Development Commands

### Running the Application

```bash
# Start the Flask application using UV (RECOMMENDED)
./start_uv.sh              # Run in foreground
# or
./start_uv_bg.sh           # Run in background

# Restart the application (kills existing process and starts fresh)
./restart.sh               # Quick restart with automatic cleanup

# Alternative: Use uv run directly
uv run python app.py

# Access the application
http://localhost:5001

# Access admin interface
http://localhost:5001/admin
```

### Virtual Environment

**IMPORTANT: This project uses uv for dependency management and virtual environments.**

```bash
# The project uses uv (modern Python package manager)
# Virtual environment is automatically managed by uv

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies using uv
uv sync

# Activate the virtual environment (optional)
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# Verify the environment is active
which python
# Should show: /Users/cynningli/Desktop/book_translation_tool/.venv/bin/python

# Add new dependencies using uv (RECOMMENDED)
uv add <package-name>

# Run the application using uv (RECOMMENDED)
./start_uv.sh              # Foreground
# or
./start_uv_bg.sh           # Background
# or
uv run python app.py       # Direct
```

**All future development and execution MUST use the uv-managed virtual environment.**

### Configuration Management

Translation services are managed through the web admin interface at `/admin`:

- Add/remove translation services
- Test service connections
- Set default service
- All sensitive data is encrypted in SQLite database

### Supported Translation Service Types

- `openai` - OpenAI-compatible APIs (DeepSeek, SiliconFlow, etc.)
- `ollama` - Local Ollama instances
- `third_party_completion` - Legacy completion APIs

### File Format Support

#### PDF Files
- **BabelDOC**: Professional translation with layout preservation
- **Traditional**: Text extraction and translation
- Output: Translated PDF, dual-language PDF, Markdown

#### ePub Files
- **Format-Preserving**: Maintains book structure and metadata
- Output: Translated ePub, HTML preview, text backup

#### Markdown Files
- **Format-Preserving**: Preserves Markdown syntax and structure
- Output: Translated Markdown, HTML preview, text backup

#### Text Files
- **Traditional**: Simple text translation
- Output: Translated text file

## Security Features

- API keys encrypted with AES-256 in SQLite database
- Secure file upload validation
- SQL injection protection via parameterized queries
- File permission controls for sensitive data

## Error Handling

- Real-time progress tracking via Server-Sent Events
- Graceful fallback for failed translations
- User-friendly error messages
- Translation abort functionality

## Important Directories

- **uploads/** - User uploaded files
- **results/** - Translation output files
- **config/** - Configuration management code
- **templates/** - Flask HTML templates
- **static/** - Static assets
- **data/** - Database and encryption keys
- **Docs/** - Project documentation
- **test/** - Temporary test files and diagnostic tools

## Directory Restrictions

**⚠️ DO NOT USE /tmp DIRECTORY**

This is a macOS system. Always use the project's `test/` directory for all temporary files and testing purposes.

```bash
# ✅ CORRECT: Use project test directory
test/my_test_file.py
test/screenshots/

# ❌ WRONG: Never use /tmp
/tmp/my_test_file.py
```

## Frontend Testing

**Always use Playwright for frontend page inspection and testing.**

When checking frontend pages (styles, errors, functionality), use the Playwright MCP tools:
- `mcp__playwright__browser_navigate` - Navigate to URL
- `mcp__playwright__browser_snapshot` - Get page accessibility snapshot
- `mcp__playwright__browser_console_messages` - Check for JS errors
- `mcp__playwright__browser_network_requests` - Check resource loading
- `mcp__playwright__browser_evaluate` - Run JavaScript to inspect computed styles
- `mcp__playwright__browser_take_screenshot` - Capture visual state

Example workflow:
```
1. Navigate to the page
2. Check console messages for errors
3. Check network requests for 404s
4. Evaluate computed styles if needed
5. Take screenshot for documentation
```

## BabelDOC Configuration

- **babeldoc.toml** - BabelDOC CLI configuration for PDF translation
- Uses DeepSeek API by default, configurable via admin interface

## Key Configuration Files

### Service Configuration
- **data/config.db** - SQLite database with encrypted service configurations
- **data/keys/master.key** - Encryption key for sensitive data
- **services.json** - Legacy configuration (migrated to SQLite)

## Development Notes

- The application uses Flask with SQLite for configuration
- All translation services are abstracted through `TranslationService` class
- File processing is asynchronous with progress tracking
- Configuration changes require service restart to take effect
- BabelDOC requires separate installation and configuration

## Testing

```bash
# Test UV environment configuration
uv run python test_uv_environment.py

# Test BabelDOC integration
uv run python test_babeldoc_integration.py

# Test format-preserving translation
uv run python test_format_preserving.py
```

## Common Development Tasks

### Adding a New Translation Service
1. Access `/admin` interface
2. Click "Add Service"
3. Fill in service details (type, URL, API key, model)
4. Test connection
5. Set as default if desired

### Debugging Translation Issues
1. Check service configuration in admin interface
2. Verify API keys and URLs
3. Test service connection
4. Check application logs in `app.log`

### Managing File Storage
- Uploads are stored in `uploads/`
- Results are stored in `results/`
- Old files should be periodically cleaned up
- Maximum file size: 50MB

### Test File Cleanup Policy

**IMPORTANT: All test files MUST be cleaned up after testing is complete.**

#### Files to Clean After Testing:
- Test files in `uploads/` directory (files with "test" in name)
- Test files in `results/` directory (files with "test" in name)
- Test Python files (`test_*.py`, `*test*.py`)
- Debug files (`debug_*.py`, `debug_*.md`)
- Test log files (`*test*.log`)

#### Cleanup Commands:
```bash
# Clean test files from uploads and results
find uploads -name "test*" -type f -delete
find results -name "test*" -type f -delete

# Clean test Python files
rm -f test_*.py *test*.py debug_*.py

# Clean test log files
rm -f *test*.log

# Clean test utility files
rm -f check_translation_result.py TEST_REPORT.md
```

**Always clean up test files immediately after testing to maintain a clean project state.**

## Project Status

**Current State:** Project is in a clean, documented state with all historical issues resolved and prevention measures in place. The codebase follows Flask best practices with modular Blueprint architecture and comprehensive documentation in the `Docs/` directory.

For detailed architecture information, see:
- **PROJECT_STRUCTURE.md** - Complete architecture documentation
- **ADMIN_SECURITY_GUIDE.md** - Security guidelines
- **BABELDOC_INTEGRATION.md** - BabelDOC setup guide
- **MARKDOWN_TRANSLATION_ANALYSIS_AND_OPTIMIZATION.md** - Translation optimization guide

## Access URLs

- **Application Home:** http://localhost:5001
- **Admin Interface:** http://localhost:5001/admin
- **PDF Translation:** http://localhost:5001/pdf
- **Markdown Translation:** http://localhost:5001/markdown
- **EPUB Translation:** http://localhost:5001/epub

## Startup Scripts

This project includes three essential startup scripts:

### 1. start_uv.sh
Runs the application in **foreground mode**. Recommended for development and debugging.
```bash
./start_uv.sh
```
- Output logs directly to console
- Ctrl+C to stop
- Best for development

### 2. start_uv_bg.sh
Runs the application in **background mode**. Recommended for production and continuous operation.
```bash
./start_uv_bg.sh
```
- Runs as background process
- Logs written to `app.log`
- Can be stopped with `lsof -ti:5001 | xargs kill`

### 3. restart.sh
**Quick restart script** that automatically cleans up and restarts the application.
```bash
./restart.sh
```
- Kills any existing process on port 5001
- Waits for port to be free
- Starts application in background mode
- Shows success/failure status
- Perfect for quick restarts after configuration changes

**Use Cases:**
- **Development:** `./start_uv.sh` for interactive debugging
- **Production:** `./start_uv_bg.sh` for background service
- **Configuration Changes:** `./restart.sh` to apply changes quickly
- **Troubleshooting:** `./restart.sh` to resolve port conflicts

---

**Last Updated:** 2025-12-10
**Version:** v2.0 (Blueprint Refactored)
**Package Manager:** uv (Python 3.12+)
