from flask import current_app # For accessing app.db and logger

def save_data_to_mongodb(data_list, collection_name="extracted_items"):
    """
    Saves a list of data dictionaries to a specified MongoDB collection.
    """
    if not data_list:
        return 0, "No data provided to save."

    if not hasattr(current_app, 'db') or current_app.db is None:
        current_app.logger.error("Database (current_app.db) is not initialized or connection failed.")
        return 0, "Database not initialized or connection failed previously."

    db_to_use = current_app.db
    collection = db_to_use[collection_name]

    try:
        if not isinstance(data_list, list) or not all(isinstance(item, dict) for item in data_list):
            current_app.logger.error("Invalid data format: data_list must be a list of dictionaries.")
            return 0, "Invalid data format for MongoDB insertion."

        result = collection.insert_many(data_list)
        inserted_count = len(result.inserted_ids)
        current_app.logger.info(f"Successfully inserted {inserted_count} items into '{collection_name}'.")
        return inserted_count, None
    except Exception as e:
        current_app.logger.error(f"Error inserting data into MongoDB collection '{collection_name}': {e}", exc_info=True)
        return 0, str(e)
