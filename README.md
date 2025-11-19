# FuzzyMatcher - RMIS Field Mapping Tool

A Python-based fuzzy matching tool for mapping fields between Ventiv IRM and Salesforce API systems.

## Overview

This tool helps with system integration by automatically matching field names from two different RMIS (Risk Management Information Systems) using fuzzy logic. It's specifically designed to map Ventiv IRM fields to Salesforce API fields where naming conventions may differ slightly.

## Features

- **🌐 Web Interface**: Easy-to-use web UI for uploading files and viewing results
- **💻 Command Line Interface**: Full-featured CLI for automation and scripting
- **Fuzzy String Matching**: Uses advanced fuzzy matching algorithms to find similar field names
- **Label-Aware Matching**: Supports matching against both Salesforce API names AND field labels for significantly improved accuracy
- **Smart Field Normalization**: Handles camelCase, underscores, prefixes/suffixes, and common abbreviations
- **Configurable Threshold**: Adjust matching sensitivity based on your needs
- **Multiple Output Formats**: Export results as CSV or JSON
- **Confidence Scoring**: Each match includes a confidence score (0-100)
- **Manual Review Support**: Easily identify low-confidence matches for manual verification
- **Match Transparency**: Shows whether each match was found via API name or label

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Web Interface (Recommended)

The easiest way to use FuzzyMatcher is through the web interface:

1. Start the web server:
```bash
python app.py
```

2. Open your browser to: **http://localhost:5000**

3. Upload your files:
   - **Ventiv IRM Fields**: .txt file with one field per line
   - **Salesforce Fields**: .txt or .csv file (CSV with labels recommended)

4. Adjust the confidence threshold (default: 70%)

5. Click "Match Fields" and view results

6. Download results as CSV

### Command Line Interface

For automation or scripting, use the CLI:

```bash
python matcher.py --ventiv data/ventiv_fields.txt --salesforce data/salesforce_fields.txt
```

### Advanced Options

```bash
# Set custom matching threshold (default: 80)
python matcher.py --ventiv data/ventiv_fields.txt --salesforce data/salesforce_fields.txt --threshold 75

# Output to CSV
python matcher.py --ventiv data/ventiv_fields.txt --salesforce data/salesforce_fields.txt --output results.csv --format csv

# Output to JSON
python matcher.py --ventiv data/ventiv_fields.txt --salesforce data/salesforce_fields.txt --output results.json --format json
```

## Input Format

### Ventiv Fields (Text File)

Provide Ventiv IRM fields as a text file with one field name per line:

**ventiv_fields.txt**:
```
B_FIRST_NAME_S
B_LAST_NAME_S
B_EMAIL_ADDRESS_S
BIRTH_DATE
CONTACT_ID
```

### Salesforce Fields (Text or CSV)

You have two options for Salesforce fields:

**Option 1: Simple Text File (API names only)**
```
FirstName
LastName
Email
Birthdate
JigsawContactId
```

**Option 2: CSV with Labels (RECOMMENDED for best results)**

For significantly improved matching accuracy, provide a CSV file with both API names and field labels:

**salesforce_fields.csv**:
```csv
FirstName,First Name
LastName,Last Name
Email,Email Address
Birthdate,Birth Date
JigsawContactId,Contact ID
Middle_Initial__c,Middle Initial
HomePhone,Home Phone Number
Address_1__c,Street Address Line 1
```

The tool automatically detects the format and uses both API names and labels when available, resulting in 95-99% confidence matches for most fields.

### How to Export Salesforce Field Labels

**Option 1: Salesforce Workbench**
1. Go to https://workbench.developerforce.com
2. Login to your org
3. Navigate to: Info → Standard & Custom Objects → Contact (or your object)
4. Click on "Fields"
5. Export to CSV with both API Name and Label columns

**Option 2: Salesforce Setup UI**
1. Setup → Object Manager → Contact
2. Click "Fields & Relationships"
3. Export or copy the API Name and Label columns to CSV

**Option 3: SOQL Query (Developer Console)**
```sql
SELECT QualifiedApiName, Label
FROM FieldDefinition
WHERE EntityDefinition.QualifiedApiName = 'Contact'
ORDER BY Label
```

## Output Format

### CSV Output (with labels)

When using CSV input with labels, the output includes comprehensive matching information:

```csv
Ventiv_Field,Salesforce_API_Name,Salesforce_Label,Confidence_Score,Status,Matched_On,Matched_Value
BIRTH_DATE,Birthdate,Birth Date,99.0,High Confidence,Label,Birth Date
B_FIRST_NAME_S,FirstName,First Name,97.83,High Confidence,API Name,FirstName
B_EMAIL_ADDRESS_S,Email,Email Address,96.33,High Confidence,Label,Email Address
```

### CSV Output (without labels)
```csv
Ventiv_Field,Salesforce_Field,Confidence_Score,Status
BIRTH_DATE,Birthdate,93.86,High Confidence
B_FIRST_NAME_S,FirstName,97.83,High Confidence
```

### JSON Output
```json
{
  "matches": [
    {
      "ventiv_field": "ClaimNumber",
      "salesforce_field": "Claim_Number__c",
      "confidence": 95,
      "status": "High Confidence"
    }
  ]
}
```

## Confidence Levels

- **High Confidence (80-100)**: Strong match, likely correct
- **Medium Confidence (60-79)**: Possible match, review recommended
- **Low Confidence (< 60)**: Weak match, manual review required

## Project Structure

```
FuzzyMatcher/
├── matcher.py              # Main matching script
├── requirements.txt        # Python dependencies
├── data/                   # Sample data files
│   ├── ventiv_fields.txt
│   └── salesforce_fields.txt
└── output/                 # Output directory for results
```

## License

MIT
