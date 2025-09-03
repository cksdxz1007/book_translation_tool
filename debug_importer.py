import sys
import os

print("--- Debug Importer Script ---")

# Print initial sys.path
print(f"Initial sys.path: {sys.path}")

# Explicitly set project root and add to sys.path (if not already first)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"Script directory (SCRIPT_DIR): {SCRIPT_DIR}")

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
    print(f"Added SCRIPT_DIR {SCRIPT_DIR} to sys.path.")
elif sys.path[0] != SCRIPT_DIR:
    sys.path.remove(SCRIPT_DIR)
    sys.path.insert(0, SCRIPT_DIR)
    print(f"Moved SCRIPT_DIR {SCRIPT_DIR} to the front of sys.path.")
else:
    print(f"SCRIPT_DIR {SCRIPT_DIR} is already at the front of sys.path.")

print(f"Final sys.path for this script: {sys.path}")
print(f"Current working directory (os.getcwd()): {os.getcwd()}")

print("\nAttempting to import 'config_loader'...")
try:
    import config_loader
    print("Successfully imported 'config_loader'.")
    print(f"Location of imported 'config_loader': {config_loader.__file__}")
    print(f"Config_loader functions: {dir(config_loader)}")
except ImportError as e:
    print(f"Failed to import 'config_loader'.")
    print(f"ImportError: {e}")
except Exception as e:
    print(f"An unexpected error occurred during import: {e}")

print("\n--- End of Debug Importer Script ---") 