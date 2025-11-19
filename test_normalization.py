#!/usr/bin/env python3
"""
Test script to see how field normalization works
"""

import sys
sys.path.insert(0, '/home/user/FuzzyMatcher')
from matcher import FieldMatcher

# Create matcher instance
matcher = FieldMatcher()

# Test Ventiv fields
ventiv_test = [
    'B_ADDRESS1_S',
    'B_ADDRESS2_S',
    'B_CITY_S',
    'B_FIRST_NAME_S',
    'B_LAST_NAME_S',
    'B_EMAIL_ADDRESS_S',
    'B_HOME_PHONE_NUMBER_S',
    'B_MOBILE_PHONE_NUBER_S',
    'B_COMPANY_NAME_S',
    'B_STATE_L',
    'B_COUNTRY_L',
    'B_POSTAL_CODE_S',
    'ADJUSTER',
    'ADJUSTER_EMAIL',
    'BIRTH_DATE',
    'DEATH_DATE',
    'B_M_I_S'
]

# Test Salesforce fields
salesforce_test = [
    'Address_1__c',
    'Address_2__c',
    'City__c',
    'FirstName',
    'LastName',
    'Email',
    'HomePhone',
    'MobilePhone',
    'Name',
    'State__c',
    'Country__c',
    'Zip_Code__c',
    'Middle_Initial__c'
]

print("VENTIV FIELDS NORMALIZATION:")
print("-" * 80)
for field in ventiv_test:
    normalized = matcher.normalize_field_name(field)
    print(f"{field:30} -> {normalized}")

print("\n\nSALESFORCE FIELDS NORMALIZATION:")
print("-" * 80)
for field in salesforce_test:
    normalized = matcher.normalize_field_name(field)
    print(f"{field:30} -> {normalized}")

print("\n\nCOMPARISON EXAMPLES:")
print("-" * 80)
examples = [
    ('B_ADDRESS1_S', 'Address_1__c'),
    ('B_FIRST_NAME_S', 'FirstName'),
    ('B_EMAIL_ADDRESS_S', 'Email'),
    ('B_HOME_PHONE_NUMBER_S', 'HomePhone'),
    ('B_MOBILE_PHONE_NUBER_S', 'MobilePhone'),
    ('BIRTH_DATE', 'Birthdate'),
    ('B_M_I_S', 'Middle_Initial__c'),
]

for ventiv, salesforce in examples:
    v_norm = matcher.normalize_field_name(ventiv)
    s_norm = matcher.normalize_field_name(salesforce)
    confidence = matcher.calculate_confidence(ventiv, salesforce)
    print(f"\nVentiv: {ventiv:30} -> {v_norm}")
    print(f"Salesforce: {salesforce:30} -> {s_norm}")
    print(f"Confidence: {confidence}%")
