import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, session, abort
from werkzeug.utils import secure_filename

from app.utils.parser_controller import process_file
from app.utils.data_normalizer import normalize_data
from app.utils.db_handler import save_data_to_mongodb

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'html', 'htm', 'json', 'xlsx', 'xls'}

bp = Blueprint('routes', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        try:
            file.save(upload_path)

            data_fields_str = request.form.get('data_fields', '').strip()

            if not data_fields_str:
                flash('Error: Data fields configuration cannot be empty.', 'error')
                # Optionally, delete the uploaded file if config is invalid
                try:
                    os.remove(upload_path)
                except OSError:
                    pass # Ignore if file cannot be removed
                return redirect(request.url)

            raw_fields = data_fields_str.split(',')
            desired_fields = [field.strip().lower() for field in raw_fields if field.strip()]

            if not desired_fields:
                flash('Error: Processed data fields configuration is empty. Ensure you provide valid field names.', 'error')
                try:
                    os.remove(upload_path)
                except OSError:
                    pass
                return redirect(request.url)

            flash(f"File '{filename}' uploaded. Will attempt to extract: {', '.join(desired_fields)}.", 'success')
            current_app.logger.info(f"File {filename} uploaded. Desired fields: {desired_fields}")

            # filepath is already defined as upload_path
            # Use file.filename for the original name with extension for process_file

            try:
                extracted_data_list = process_file(upload_path, file.filename, desired_fields)
                normalized_data_list = [] # Initialize to handle scope if extracted_data_list is None

                if extracted_data_list is not None:
                    # Normalize the extracted data
                    # Pass desired_fields to ensure all expected fields are considered during normalization
                    normalized_data_list = normalize_data(list(extracted_data_list), list(desired_fields))

                    if normalized_data_list: # Check if list is not empty after normalization
                        flash(f"Successfully extracted and normalized {len(normalized_data_list)} item(s) from '{file.filename}'.", 'success')

                        # Store in session for now to display on a results page (to be implemented)
                        # from flask import session # session is now imported at the top
                        session['processed_data'] = normalized_data_list
                        session['filename_for_results'] = file.filename
                        # return redirect(url_for('routes.show_results')) # Next step

                    # else: # List is empty after normalization or was empty before
                        # This case will be handled by the revised logic below
                        pass # No specific flash here, covered by generic messages below

                # Revised logic for flashing messages:
                if extracted_data_list is None: # Parser controller indicated unsupported type or major error
                     flash(f"File type of '{file.filename}' is not supported for parsing or a major error occurred in controller.", 'error')
                elif not extracted_data_list: # Parsers returned an empty list (and therefore normalized_data_list will also be empty)
                    flash(f"No data could be extracted from '{file.filename}' for the specified fields by the parser.", 'warning')
                elif not normalized_data_list: # Parsers found data, but normalization resulted in empty list
                    flash(f"Data extracted from '{file.filename}', but all items were empty or invalid after normalization.", 'warning')
                # else: # normalized_data_list has items, success message already flashed above.
                    # This 'else' is covered by the success flash for normalized_data_list having items.

                # Save to DB if normalized_data_list has items
                if normalized_data_list: # Ensure there's data to save
                    inserted_count, error_msg = save_data_to_mongodb(list(normalized_data_list)) # Pass a copy
                    if error_msg:
                        flash(f"Error saving data to database: {error_msg}", 'error')
                    else:
                        flash(f"Successfully saved {inserted_count} item(s) to the database.", 'success')

            except Exception as e:
                current_app.logger.error(f"Error during processing, parsing, normalization, or DB save of file {file.filename}: {e}", exc_info=True)
                flash(f"An unexpected error occurred while trying to process or parse '{file.filename}'. Details: {e}", 'error')
                # Consider removing the file if processing fails critically
                # import os
                # if os.path.exists(upload_path): # upload_path is the filepath
                #     os.remove(upload_path)

            return redirect(url_for('routes.show_results')) # Redirect to results page

        except Exception as e:
            flash(f"An error occurred while saving the file or processing fields: {str(e)}", 'error')
            current_app.logger.error(f"Error saving file {filename}: {e}") # It's good to log errors
            return redirect(request.url) # Or redirect to index

    else:
        flash('File type not allowed. Allowed types are: html, htm, json, xlsx, xls.', 'error')
        return redirect(request.url) # Or redirect to index

# Example of how to access the db instance if needed within a route
@bp.route('/test_db')
def test_db():
    from app import db # Import db locally to avoid circular import issues at module level
    if db:
        try:
            # Example: count documents in a hypothetical 'users' collection
            # user_count = db.users.count_documents({})
            # flash(f"DB connected. Users count: {user_count}", 'info')
            flash("DB object seems available.", "info")
        except Exception as e:
            flash(f"Error interacting with DB: {e}", "error")
            current_app.logger.error(f"DB interaction error: {e}")
    else:
        flash("DB connection not available.", "error")
    return redirect(url_for('routes.index'))

@bp.route('/results')
def show_results():
    processed_data = session.get('processed_data', [])
    filename = session.get('filename_for_results', 'Unknown file')
    # It's good practice to clear large data from session after use
    # session.pop('processed_data', None)
    # session.pop('filename_for_results', None)
    return render_template('results.html', data=processed_data, filename=filename)

@bp.route('/browse-data')
def browse_data():
    if not hasattr(current_app, 'db') or current_app.db is None:
        flash("Database connection is not available.", "error")
        return render_template('browse_data.html', items_list=[], page=1, total_pages=0, per_page=0, total_items=0)

    db_to_use = current_app.db
    collection_name = "extracted_items" # Or make this configurable if needed
    collection = db_to_use[collection_name]

    page = request.args.get('page', 1, type=int)
    per_page = 20 # Items per page

    try:
        total_items = collection.count_documents({})
    except Exception as e:
        current_app.logger.error(f"Error counting documents in '{collection_name}': {e}", exc_info=True)
        flash(f"Error accessing database: {e}", "error")
        return render_template('browse_data.html', items_list=[], page=1, total_pages=0, per_page=per_page, total_items=0)

    total_pages = (total_items + per_page - 1) // per_page # Ceiling division

    if total_items > 0 and (page < 1 or page > total_pages):
        return abort(404) # Page out of range

    skip_items = (page - 1) * per_page

    items_list = []
    if total_items > 0:
        try:
            # Sort by _id descending to show newest items first
            items_cursor = collection.find({}).sort('_id', -1).skip(skip_items).limit(per_page)
            items_list = list(items_cursor) # Convert cursor to list
        except Exception as e:
            current_app.logger.error(f"Error querying data from '{collection_name}': {e}", exc_info=True)
            flash(f"Error retrieving data: {e}", "error")
            # items_list will remain empty as initialized

    return render_template('browse_data.html',
                           items_list=items_list,
                           page=page,
                           total_pages=total_pages,
                           per_page=per_page,
                           total_items=total_items)
