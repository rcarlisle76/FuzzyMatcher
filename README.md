# FuzzyMatcher - RMIS Field Mapping Tool

A Python-based fuzzy matching tool for mapping fields between Ventiv IRM and Salesforce API systems.

## Overview

This tool helps with system integration by automatically matching field names from two different RMIS (Risk Management Information Systems) using fuzzy logic. It's specifically designed to map Ventiv IRM fields to Salesforce API fields where naming conventions may differ slightly.

## Features

- **Fuzzy String Matching**: Uses advanced fuzzy matching algorithms to find similar field names
- **Configurable Threshold**: Adjust matching sensitivity based on your needs
- **Multiple Output Formats**: Export results as CSV or JSON
- **Confidence Scoring**: Each match includes a confidence score (0-100)
- **Manual Review Support**: Easily identify low-confidence matches for manual verification

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

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

Field lists should be provided as text files with one field name per line:

**ventiv_fields.txt**:
```
ClaimNumber
PolicyHolderName
DateOfLoss
ClaimAmount
```

**salesforce_fields.txt**:
```
Claim_Number__c
Policy_Holder_Name__c
Loss_Date__c
Claim_Amount__c
```

## Output Format

### CSV Output
```csv
Ventiv_Field,Salesforce_Field,Confidence_Score,Status
ClaimNumber,Claim_Number__c,95,High Confidence
PolicyHolderName,Policy_Holder_Name__c,92,High Confidence
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
