import json
from flask import current_app

def parse_json(filepath, desired_fields):
    """
    Parses a JSON file to extract data for the desired fields.
    Handles a single JSON object or a list of JSON objects.
    Matches desired_fields against keys in the JSON objects.
    """
    extracted_items = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f: # Added errors='replace'
            data = json.load(f)

        # Ensure desired_fields are lowercase for consistent matching
        # (They should already be from routes.py, but good to be sure if used elsewhere)
        # desired_fields_lower = [df.lower() for df in desired_fields]

        if isinstance(data, dict): # Single JSON object as the root
            current_item_data = {}
            item_has_data = False
            for field_key in desired_fields: # these are already lowercased
                # Try direct key match first (common case)
                value = data.get(field_key)
                # If not found, try case-insensitive match for flexibility
                if value is None:
                    for k_obj, v_obj in data.items():
                        if k_obj.lower() == field_key:
                            value = v_obj
                            break
                current_item_data[field_key] = value
                if value is not None:
                    item_has_data = True

            if item_has_data:
                extracted_items.append(current_item_data)

        elif isinstance(data, list): # List of JSON objects as the root
            for record in data:
                if isinstance(record, dict):
                    current_item_data = {}
                    item_has_data = False
                    for field_key in desired_fields:
                        value = record.get(field_key)
                        if value is None:
                            for k_obj, v_obj in record.items():
                                if k_obj.lower() == field_key:
                                    value = v_obj
                                    break
                        current_item_data[field_key] = value
                        if value is not None:
                            item_has_data = True

                    if item_has_data: # Add item only if it has some data for desired fields
                        extracted_items.append(current_item_data)
                else:
                    # Log or handle items in the list that are not dictionaries
                    current_app.logger.warning(f"Item in JSON list is not a dictionary: {record} in file {filepath}")
        else:
            # Log or handle cases where JSON root is neither dict nor list
            current_app.logger.warning(f"JSON data in {filepath} is not a single object or a list of objects.")
            return []

    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from file {filepath}: {e}", exc_info=True)
        return [] # Return empty list on JSON format errors
    except FileNotFoundError:
        current_app.logger.error(f"JSON file not found at {filepath}")
        return []
    except Exception as e:
        # Catch any other unexpected errors during parsing
        current_app.logger.error(f"An unexpected error occurred while parsing JSON file {filepath}: {e}", exc_info=True)
        return []

    return extracted_items
