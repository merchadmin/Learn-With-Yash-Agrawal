import os
from flask import current_app
from . import html_parser # Assuming html_parser.py will exist in the same directory
from . import json_parser
from . import excel_parser

def process_file(filepath, filename, desired_fields):
    """
    Determines the file type and calls the appropriate parser.
    """
    _, extension = os.path.splitext(filename)
    extension = extension.lower()

    extracted_data_list = []

    if extension == '.html' or extension == '.htm':
        extracted_data_list = html_parser.parse_html(filepath, desired_fields)
    elif extension == '.json':
        extracted_data_list = json_parser.parse_json(filepath, desired_fields)
    elif extension == '.xlsx' or extension == '.xls':
        extracted_data_list = excel_parser.parse_excel(filepath, desired_fields)
    else:
        current_app.logger.warning(f"Unsupported file type: '{extension}' for file '{filename}'. No parser available.")
        # Return None or an empty list to indicate no processing for this type yet or error
        return None

    return extracted_data_list
