from bs4 import BeautifulSoup
from flask import current_app

def parse_html(filepath, desired_fields):
    """
    Parses an HTML file to extract data for the desired fields.
    Assumes desired_fields correspond to class names or IDs of elements.
    This is a very basic implementation.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f: # Added errors='replace'
            soup = BeautifulSoup(f, 'html.parser')

        # This basic version assumes one "item" per HTML file.
        item_data = {}
        found_any_field = False
        for field in desired_fields:
            element = soup.find(class_=field)
            if not element: # If not found by class, try by ID
                element = soup.find(id=field)

            if element:
                # Special handling for common image and link cases
                if field in ['image', 'img', 'logo', 'picture', 'banner'] and element.name == 'img':
                    item_data[field] = element.get('src')
                elif field in ['link', 'url', 'href'] and element.name == 'a':
                    item_data[field] = element.get('href')
                else:
                    item_data[field] = element.get_text(separator=' ', strip=True)

                if item_data[field]: # If we got some value
                    found_any_field = True
            else:
                item_data[field] = None

        if found_any_field: # Add if at least one field was populated
            return [item_data] # Return as a list of one item
        else:
            return [] # No data found for any field

    except FileNotFoundError:
        current_app.logger.error(f"HTML file not found at {filepath}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error parsing HTML file {filepath}: {e}", exc_info=True)
        return [] # Return empty list on error
