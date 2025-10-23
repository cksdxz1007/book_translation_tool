# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based web application for translating documents (PDF, ePub, Markdown, text) using multiple translation engines including BabelDOC for professional PDF translation and traditional text-based translation.

## Architecture

### Core Components

- **app.py** - Main Flask application with routes for PDF, ePub, and Markdown translation
- **translator.py** - Translation service abstraction supporting multiple providers (OpenAI-compatible, Ollama, custom)
- **start_app.py** - Application launcher with virtual environment handling
- **config/manager.py** - SQLite-based secure configuration management with encryption
- **admin_routes.py** - Web-based configuration management interface

### Translation Engines

1. **BabelDOC Engine** (`pdf_translator_babeldoc.py`) - Professional PDF translation with layout preservation
2. **Traditional Engine** (`translator.py`) - Text-based translation for ePub/Markdown/PDF
3. **Format-Preserving Engine** (`format_preserving_*`) - Maintains document structure for ePub/Markdown

### File Processing Pipeline

1. **Upload** → `uploads/` directory
2. **Parsing** → File-specific parsers (PDF, ePub, Markdown)
3. **Translation** → Selected translation engine
4. **Output** → `results/` directory with multiple formats

## Development Commands

### Running the Application

```bash
# Start the Flask application
python start_app.py

# Access the application
http://localhost:5001

# Access admin interface
http://localhost:5001/admin
```

### Virtual Environment

**IMPORTANT: This project MUST use the conda virtual environment named `books_venv` located at:**
`/opt/homebrew/Caskroom/miniconda/base/envs/books_venv`

```bash
# Activate the conda environment
conda activate books_venv

# Verify the environment is active
which python
# Should show: /opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/python

# Install dependencies if needed
pip install -r requirements.txt

# Run the application
python start_app.py
```

**All future development and execution MUST use this conda environment.**

### Configuration Management

Translation services are managed through the web admin interface at `/admin`:

- Add/remove translation services
- Test service connections
- Set default service
- All sensitive data is encrypted in SQLite database

### Testing

```bash
# Test BabelDOC integration
python test_babeldoc_integration.py

# Test format-preserving translation
python test_format_preserving.py
```

## Key Configuration Files

### Service Configuration

- **data/config.db** - SQLite database with encrypted service configurations
- **data/keys/master.key** - Encryption key for sensitive data
- **services.json** - Legacy configuration (migrated to SQLite)

### BabelDOC Configuration

- **babeldoc.toml** - BabelDOC CLI configuration for PDF translation
- Uses DeepSeek API by default, configurable via admin interface

## Important Directories

- **uploads/** - User uploaded files
- **results/** - Translation output files
- **config/** - Configuration management code
- **templates/** - Flask HTML templates
- **static/admin/** - Admin interface assets
- **data/** - Database and encryption keys

## Translation Service Types

Supported service types in the configuration system:

- `openai` - OpenAI-compatible APIs (DeepSeek, SiliconFlow, etc.)
- `ollama` - Local Ollama instances
- `third_party_completion` - Legacy completion APIs

## File Format Support

### PDF Files
- **BabelDOC**: Professional translation with layout preservation
- **Traditional**: Text extraction and translation
- Output: Translated PDF, dual-language PDF, Markdown

### ePub Files
- **Format-Preserving**: Maintains book structure and metadata
- Output: Translated ePub, HTML preview, text backup

### Markdown Files
- **Format-Preserving**: Preserves Markdown syntax and structure
- Output: Translated Markdown, HTML preview, text backup

### Text Files
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

## Development Notes

- The application uses Flask with SQLite for configuration
- All translation services are abstracted through `TranslationService` class
- File processing is asynchronous with progress tracking
- Configuration changes require service restart to take effect
- BabelDOC requires separate installation and configuration

## Common Tasks

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