#!/usr/bin/env python3
"""
Flask web application for FuzzyMatcher
Upload CSV files and get field matching results
"""

from flask import Flask, render_template, request, send_file, jsonify
import os
from werkzeug.utils import secure_filename
from matcher import FieldMatcher
import pandas as pd
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'csv'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')


@app.route('/match', methods=['POST'])
def match_fields():
    """Process uploaded files and perform matching"""

    # Validate files
    if 'ventiv_file' not in request.files or 'salesforce_file' not in request.files:
        return jsonify({'error': 'Both files are required'}), 400

    ventiv_file = request.files['ventiv_file']
    salesforce_file = request.files['salesforce_file']

    if ventiv_file.filename == '' or salesforce_file.filename == '':
        return jsonify({'error': 'Please select both files'}), 400

    if not (allowed_file(ventiv_file.filename) and allowed_file(salesforce_file.filename)):
        return jsonify({'error': 'Only .txt and .csv files are allowed'}), 400

    # Get threshold from form
    threshold = int(request.form.get('threshold', 70))

    # Save uploaded files
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ventiv_filename = secure_filename(f"ventiv_{timestamp}_{ventiv_file.filename}")
    salesforce_filename = secure_filename(f"salesforce_{timestamp}_{salesforce_file.filename}")

    ventiv_path = os.path.join(app.config['UPLOAD_FOLDER'], ventiv_filename)
    salesforce_path = os.path.join(app.config['UPLOAD_FOLDER'], salesforce_filename)

    ventiv_file.save(ventiv_path)
    salesforce_file.save(salesforce_path)

    try:
        # Initialize matcher
        matcher = FieldMatcher(threshold=threshold)

        # Load fields
        ventiv_fields_dict = matcher.load_fields_with_labels(ventiv_path)
        salesforce_fields_dict = matcher.load_fields_with_labels(salesforce_path)

        # Determine if we have labels
        has_ventiv_labels = any(api != label for api, label in ventiv_fields_dict.items())
        has_sf_labels = any(api != label for api, label in salesforce_fields_dict.items())
        has_labels = has_ventiv_labels or has_sf_labels

        # Perform matching
        if has_labels:
            matches = matcher.match_fields_with_labels(ventiv_fields_dict, salesforce_fields_dict)
        else:
            ventiv_fields = list(ventiv_fields_dict.keys())
            salesforce_fields = list(salesforce_fields_dict.keys())
            matches = matcher.match_fields(ventiv_fields, salesforce_fields)

        # Calculate statistics
        total_matches = len(matches)
        high_conf = len([m for m in matches if m['confidence'] >= 80])
        med_conf = len([m for m in matches if 60 <= m['confidence'] < 80])
        low_conf = len([m for m in matches if m['confidence'] < 60])

        above_threshold = len([m for m in matches if m['confidence'] >= threshold])

        # Save results to CSV
        results_filename = f"results_{timestamp}.csv"
        results_path = os.path.join(app.config['UPLOAD_FOLDER'], results_filename)

        if matches:
            df = pd.DataFrame(matches)
            if 'salesforce_label' in df.columns:
                column_map = {
                    'ventiv_field': 'Ventiv_Field',
                    'salesforce_field': 'Salesforce_API_Name',
                    'salesforce_label': 'Salesforce_Label',
                    'confidence': 'Confidence_Score',
                    'status': 'Status',
                    'matched_on': 'Matched_On',
                    'matched_value': 'Matched_Value'
                }
            else:
                column_map = {
                    'ventiv_field': 'Ventiv_Field',
                    'salesforce_field': 'Salesforce_Field',
                    'confidence': 'Confidence_Score',
                    'status': 'Status'
                }
            df = df.rename(columns=column_map)
            df.to_csv(results_path, index=False)

        # Clean up uploaded files
        os.remove(ventiv_path)
        os.remove(salesforce_path)

        # Prepare data for template
        return render_template('results.html',
                             matches=matches,
                             has_labels=has_labels,
                             has_ventiv_labels=has_ventiv_labels,
                             has_sf_labels=has_sf_labels,
                             total_matches=total_matches,
                             high_conf=high_conf,
                             med_conf=med_conf,
                             low_conf=low_conf,
                             above_threshold=above_threshold,
                             threshold=threshold,
                             results_file=results_filename,
                             ventiv_count=len(ventiv_fields_dict),
                             salesforce_count=len(salesforce_fields_dict))

    except Exception as e:
        # Clean up files on error
        if os.path.exists(ventiv_path):
            os.remove(ventiv_path)
        if os.path.exists(salesforce_path):
            os.remove(salesforce_path)

        return jsonify({'error': f'Error processing files: {str(e)}'}), 500


@app.route('/download/<filename>')
def download_file(filename):
    """Download results CSV file"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
