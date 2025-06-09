import re
from flask import current_app

def normalize_data(extracted_data_list, desired_fields):
    """
    Normalizes a list of extracted data items.
    - Trims whitespace from string values.
    - Converts empty strings to None.
    - Attempts basic type conversion for numeric-like fields.
    """
    if not extracted_data_list:
        return []

    normalized_list = []
    for item in extracted_data_list:
        normalized_item = {}
        # Ensure all desired_fields are present in the normalized_item, even if not in original item
        for field in desired_fields:
            value = item.get(field) # Use .get() to handle fields missing from a particular item

            # 1. Trim whitespace if string
            if isinstance(value, str):
                value = value.strip()

            # 2. Convert empty string to None
            if value == "": # Check after stripping
                value = None

            # 3. Basic Type Conversion Attempt (if value is not None)
            if value is not None:
                # Fields that suggest they should be integers
                # (e.g., bsr, rank, count, qty, quantity, number - but avoid price_number etc.)
                is_int_candidate = any(kw in field.lower() for kw in ['bsr', 'rank', 'count', 'qty', 'quantity']) or field.lower().endswith('number')
                is_price_related_number = any(kw in field.lower() for kw in ['price_number', 'amount_number']) # Avoid converting these to int if they could be float like

                if is_int_candidate and not is_price_related_number:
                    if isinstance(value, str):
                        cleaned_value_str = value.replace(',', '')
                        try:
                            value = int(cleaned_value_str)
                        except ValueError:
                            try:
                                # Try float then int (e.g., for "123.0" or "1,234.0")
                                value = int(float(cleaned_value_str.replace(' ', ''))) # Remove spaces too for float conversion
                            except ValueError:
                                 current_app.logger.debug(f"Could not convert field '{field}' value '{value}' to int after trying float.")
                                pass # Keep as string if conversion fails
                    elif isinstance(value, float):
                        if value.is_integer():
                            value = int(value)
                        # else keep as float if it has actual decimal places

                # Fields that suggest they should be floats (e.g. price, amount, rating, value, fee, cost, discount)
                elif any(kw in field.lower() for kw in ['price', 'amount', 'rating', 'value', 'fee', 'cost', 'discount', 'percent']):
                    if isinstance(value, str):
                        # Remove common currency symbols and thousand separators (commas)
                        # Allow decimal point.
                        cleaned_value_str = re.sub(r'[$,€£¥₹]', '', value) # Remove currency
                        cleaned_value_str = cleaned_value_str.replace(',', '') # Remove commas (as thousand separators)
                        try:
                            value = float(cleaned_value_str)
                        except ValueError:
                                 current_app.logger.debug(f"Could not convert field '{field}' value '{value}' to float.")
                            pass # Keep as string
                    elif isinstance(value, int): # Promote int to float for these fields
                        value = float(value)

            normalized_item[field] = value

        # Add item to list if it has at least one non-None value among the desired_fields
        # This ensures that we don't add completely empty dictionaries if a row had no parsable data for desired fields.
        if any(normalized_item.get(df) is not None for df in desired_fields):
            normalized_list.append(normalized_item)

    return normalized_list
