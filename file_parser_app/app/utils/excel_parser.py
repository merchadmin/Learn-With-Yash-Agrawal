import openpyxl
from flask import current_app

def parse_excel(filepath, desired_fields):
    """
    Parses an Excel file (.xlsx or .xls) to extract data.
    Assumes the first row is headers and matches desired_fields (case-insensitively)
    to these headers to extract column data.
    """
    extracted_items = []
    try:
        # data_only=True ensures that formula values are read, not the formulas themselves.
        # read_only=True can be faster for large files if you don't need to modify.
        workbook = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        sheet = workbook.active # Get the currently active sheet (usually the first one)

        if not sheet.max_row > 0:
            current_app.logger.warning(f"Excel sheet in {filepath} appears to be empty or has no rows.")
            return []

        # Read headers from the first row. sheet.iter_rows(max_row=1) gives an iterator for the first row.
        first_row_iterator = sheet.iter_rows(min_row=1, max_row=1, values_only=True)
        headers_row = next(first_row_iterator, []) # Get values from the first row, default to empty list

        if not headers_row:
            current_app.logger.warning(f"Could not read headers from the first row of {filepath}.")
            return []

        # Map desired_fields (which are already lowercase) to column indices (0-based)
        # and the original header casing for potential use (though keys in dict will be desired_field)
        column_map = {}  # Stores {desired_field_lowercase: column_index}

        for df_lower in desired_fields: # desired_fields are already lowercased
            found_match = False
            for col_idx, header_cell_value in enumerate(headers_row):
                if header_cell_value is not None: # Ensure header cell is not empty
                    header_text = str(header_cell_value).strip().lower()
                    if header_text == df_lower:
                        column_map[df_lower] = col_idx
                        found_match = True
                        break # Found mapping for this desired_field, move to next desired_field
            if not found_match:
                # This desired_field was not found in headers. Store it with None index or skip.
                # For now, we only map found fields. The output dict will lack this field.
                    current_app.logger.warning(f"Desired field '{df_lower}' not found in Excel headers of {filepath}.")


        if not column_map:
            current_app.logger.warning(f"No matching headers found in {filepath} for any of the desired fields: {desired_fields}")
            return []

        # Iterate over data rows (starting from the second row)
        # sheet.iter_rows(min_row=2) gives an iterator for all rows starting from the second.
        for row_values in sheet.iter_rows(min_row=2, values_only=True):
            current_row_data = {}
            item_has_data = False # To check if any of the *mapped* fields have data in this row

            for field_key, col_idx_mapped in column_map.items():
                # col_idx_mapped is 0-based index for the row_values tuple
                if col_idx_mapped < len(row_values):
                    cell_value = row_values[col_idx_mapped]
                    current_row_data[field_key] = cell_value
                    if cell_value is not None and str(cell_value).strip() != "": # Consider a cell with data if not None and not just whitespace
                        item_has_data = True
                else:
                    # This case should ideally not happen if headers_row was complete for col_idx_mapped
                    current_row_data[field_key] = None

            # Add row to extracted_items only if it contains data for at least one of the mapped desired fields
            if item_has_data:
                extracted_items.append(current_row_data)
            # elif any(current_row_data.values()): # Alternative: add if any cell in the row has value, even if not mapped
            #     # This might be too broad if row has data in unmapped columns but not mapped ones
            #     extracted_items.append(current_row_data)


    except FileNotFoundError:
        current_app.logger.error(f"Excel file not found at {filepath}")
        return []
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred while parsing Excel file {filepath}: {e}", exc_info=True)
        # For debugging, you might want to log the full traceback:
        # import traceback
        # current_app.logger.error(traceback.format_exc())
        return [] # Return empty list on error

    return extracted_items
