import json
import os
import logging

CONFIG_FILE_NAME = "services.json"

# Path to check for the configuration file
# Now only checks the current working directory
CONFIG_PATH = os.path.join(os.getcwd(), CONFIG_FILE_NAME)

logger = logging.getLogger(__name__)

def find_config_file():
    """
    Checks if the service configuration file exists in the current working directory.

    Returns:
        str: The path to the configuration file if it exists, or None.
    """
    if os.path.exists(CONFIG_PATH):
        logger.debug(f"Configuration file found at: {CONFIG_PATH}")
        return CONFIG_PATH
    logger.debug(f"Configuration file '{CONFIG_FILE_NAME}\' not found in current working directory: {CONFIG_PATH}")
    return None

def load_service_config(config_path=None):
    """
    Loads API service configurations from a JSON file.
    If config_path is not provided, it looks in the current working directory.

    Args:
        config_path (str, optional): Specific path to the configuration file. 
                                     If None, defaults to 'services.json' in the current working directory.

    Returns:
        dict: Parsed configuration data, or None if an error occurs.
    """
    effective_config_path = None
    if config_path: # If a specific path is given, use it directly
        effective_config_path = config_path
        if not os.path.exists(effective_config_path):
            logger.warning(f"Specified configuration file not found at: {effective_config_path}")
            return None
    else: # Otherwise, find the config file in the current working directory
        effective_config_path = find_config_file()
        if not effective_config_path:
            # No warning here, as it's a normal case if user hasn't created one
            # or if the intention is to rely solely on direct CLI params in some scenarios.
            return None

    try:
        with open(effective_config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        logger.info(f"Successfully loaded configuration from: {effective_config_path}")
        return config_data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {effective_config_path}: {e}")
        return None
    except IOError as e:
        logger.error(f"Error reading file {effective_config_path}: {e}")
        return None
    except Exception as e: 
        logger.error(f"Unexpected error loading config from {effective_config_path}: {e}")
        return None

def get_api_key_from_config(service_config):
    """
    Retrieves API key from service configuration, checking direct key or environment variable.

    Args:
        service_config (dict): The configuration for a specific service.

    Returns:
        str: The API key, or None if not found.
    """
    if "api_key" in service_config:
        return service_config["api_key"]
    elif "api_key_env_var" in service_config:
        env_var_name = service_config["api_key_env_var"]
        api_key = os.getenv(env_var_name)
        if not api_key:
            logger.warning(f"Environment variable {env_var_name} not set for API key.")
        return api_key
    return None

if __name__ == '__main__':
    # Example usage:
    logging.basicConfig(level=logging.INFO)
    
    configs = load_service_config()
    if configs and "services" in configs:
        print("Available service configurations:")
        for name, details in configs["services"].items():
            print(f"  - {name}: type={details.get('service_type')}, model={details.get('model_name')}")
            key = get_api_key_from_config(details)
            if key:
                print(f"    API Key: {"*" * (len(key) - 4) + key[-4:] if len(key) > 4 else "****"}") # Mask key for printing
            else:
                if "api_key_env_var" in details:
                    print(f"    API Key Env Var: {details['api_key_env_var']} (not set or no direct key)")
                elif details.get("service_type") not in ["ollama"]: # Ollama typically doesn't need an API key
                     print("    API Key: Not configured and not an env var.")


        default_service = configs.get("default_service_name")
        if default_service:
            print(f"\nDefault service: {default_service}")
    else:
        print("\nNo configurations loaded or 'services' key missing.")

    # Test with a specific service if loaded
    if configs and "services" in configs and "siliconflow_default" in configs["services"]:
        sf_config = configs["services"]["siliconflow_default"]
        sf_key = get_api_key_from_config(sf_config)
        print(f"\nSiliconFlow Default API Key: {sf_key is not None}") 