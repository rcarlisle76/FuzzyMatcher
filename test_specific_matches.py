#!/usr/bin/env python3
"""
Test specific field matches to debug
"""

import sys
sys.path.insert(0, '/home/user/FuzzyMatcher')
from matcher import FieldMatcher

# Create matcher instance
matcher = FieldMatcher()

# Load actual fields
ventiv_fields = matcher.load_fields('data/ventiv_fields.txt')
salesforce_fields = matcher.load_fields('data/salesforce_fields.txt')

# Test specific Ventiv fields against Salesforce
test_fields = [
    'B_FIRST_NAME_S',
    'B_LAST_NAME_S',
    'B_EMAIL_ADDRESS_S',
    'B_HOME_PHONE_NUMBER_S',
    'B_MOBILE_PHONE_NUBER_S',
    'B_FAX_NUMBER_S',
    'B_ADDRESS1_S',
    'B_ADDRESS2_S',
    'B_CITY_S',
    'B_STATE_L',
    'B_COUNTRY_L',
    'B_POSTAL_CODE_S',
    'BIRTH_DATE',
    'B_COMPANY_NAME_S',
]

print("TESTING SPECIFIC VENTIV FIELDS:\n")
print("="*80)

for ventiv_field in test_fields:
    print(f"\n{ventiv_field}:")
    print("-"*80)

    # Find top 3 matches
    from rapidfuzz import process, fuzz

    # Get normalized version for display
    v_norm = matcher.normalize_field_name(ventiv_field)
    print(f"  Normalized: {v_norm}")
    print(f"\n  Top 5 matches:")

    # Calculate scores for all Salesforce fields
    scores = []
    for sf_field in salesforce_fields:
        confidence = matcher.calculate_confidence(ventiv_field, sf_field)
        scores.append((sf_field, confidence))

    # Sort by confidence
    scores.sort(key=lambda x: x[1], reverse=True)

    # Show top 5
    for i, (sf_field, confidence) in enumerate(scores[:5], 1):
        sf_norm = matcher.normalize_field_name(sf_field)
        print(f"    {i}. {sf_field:35} ({confidence}%)  [{sf_norm}]")
