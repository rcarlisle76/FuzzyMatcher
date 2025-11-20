#!/usr/bin/env python3
"""
FuzzyMatcher - RMIS Field Mapping Tool
Matches Ventiv IRM fields to Salesforce API fields using fuzzy logic
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from rapidfuzz import fuzz, process
import pandas as pd
import numpy as np


class FieldMatcher:
    """Handles fuzzy matching between two sets of field names"""

    def __init__(self, threshold: int = 80, use_embeddings: bool = False,
                 fuzzy_weight: float = 0.5, semantic_weight: float = 0.5):
        """
        Initialize the FieldMatcher

        Args:
            threshold: Minimum confidence score (0-100) for a match
            use_embeddings: Whether to use semantic embeddings for matching
            fuzzy_weight: Weight for fuzzy matching score (0-1)
            semantic_weight: Weight for semantic similarity score (0-1)
        """
        self.threshold = threshold
        self.use_embeddings = use_embeddings
        self.fuzzy_weight = fuzzy_weight
        self.semantic_weight = semantic_weight
        self.model = None
        self.embedding_cache = {}

        # Try to load embedding model if requested
        if use_embeddings:
            self._load_embedding_model()

        # Common field name abbreviations and expansions
        self.abbreviations = {
            'addr': 'address',
            'num': 'number',
            'nbr': 'number',
            'desc': 'description',
            'amt': 'amount',
            'mgr': 'manager',
            'dept': 'department',
            'emp': 'employee',
            'id': 'identifier',
            'fax': 'fax',
            'tel': 'telephone',
            'phn': 'phone',
            'ph': 'phone',
            'dob': 'date of birth',
            'ssn': 'social security number',
            'npi': 'national provider identifier',
            'med': 'medical',
            'm': 'middle',
            'i': 'initial',
            'lt': 'litigation',
            'ref': 'reference'
        }

        # Field type compatibility rules
        # Define which types are compatible with each other
        self.type_groups = {
            'text': {'text', 'string', 'varchar', 'char', 'email', 'phone', 'url', 'picklist'},
            'number': {'number', 'integer', 'int', 'decimal', 'float', 'double', 'currency', 'percent'},
            'date': {'date', 'datetime', 'timestamp', 'time'},
            'boolean': {'boolean', 'bool', 'checkbox'},
            'reference': {'reference', 'lookup', 'id', 'foreignkey'}
        }

    def normalize_type(self, field_type: str) -> str:
        """
        Normalize a field type to a standard category

        Args:
            field_type: Original field type

        Returns:
            Normalized type category
        """
        if not field_type:
            return 'unknown'

        field_type_lower = field_type.lower().strip()

        # Find which group this type belongs to
        for group_name, types in self.type_groups.items():
            if field_type_lower in types:
                return group_name

        # If no match, return as-is
        return field_type_lower

    def are_types_compatible(self, type1: str, type2: str) -> tuple:
        """
        Check if two field types are compatible

        Args:
            type1: First field type
            type2: Second field type

        Returns:
            Tuple of (compatible: bool, match_quality: str)
            match_quality can be 'exact', 'compatible', or 'incompatible'
        """
        if not type1 or not type2:
            return (True, 'unknown')  # No penalty if type info missing

        norm_type1 = self.normalize_type(type1)
        norm_type2 = self.normalize_type(type2)

        # Exact match
        if norm_type1 == norm_type2:
            return (True, 'exact')

        # Check if they're in the same compatibility group
        for group_types in self.type_groups.values():
            if type1.lower() in group_types and type2.lower() in group_types:
                return (True, 'compatible')

        # Incompatible types
        return (False, 'incompatible')

    def _load_embedding_model(self):
        """Load the sentence transformer model for semantic matching"""
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading semantic embedding model (this may take a moment on first run)...")
            # Use a small, fast model optimized for semantic similarity
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✓ Embedding model loaded successfully")
        except ImportError:
            print("Warning: sentence-transformers not installed. Falling back to fuzzy matching only.")
            print("Install with: pip install sentence-transformers")
            self.use_embeddings = False
        except Exception as e:
            print(f"Warning: Could not load embedding model: {e}")
            print("Falling back to fuzzy matching only.")
            self.use_embeddings = False

    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding vector for a text string (with caching)

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if model not available
        """
        if not self.model:
            return None

        # Check cache first
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        # Compute and cache embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        self.embedding_cache[text] = embedding
        return embedding

    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        from sklearn.metrics.pairwise import cosine_similarity
        return cosine_similarity([vec1], [vec2])[0][0]

    def calculate_semantic_similarity(self, source: str, target: str) -> float:
        """
        Calculate semantic similarity using embeddings

        Args:
            source: Source field name
            target: Target field name

        Returns:
            Semantic similarity score (0-100)
        """
        if not self.use_embeddings or not self.model:
            return 0.0

        # Get embeddings for both normalized field names
        source_norm = self.normalize_field_name(source)
        target_norm = self.normalize_field_name(target)

        source_emb = self.get_embedding(source_norm)
        target_emb = self.get_embedding(target_norm)

        if source_emb is None or target_emb is None:
            return 0.0

        # Compute cosine similarity and convert to 0-100 scale
        similarity = self.cosine_similarity(source_emb, target_emb)
        return round(similarity * 100, 2)

    def load_fields(self, file_path: str) -> List[str]:
        """
        Load field names from a text file

        Args:
            file_path: Path to the file containing field names

        Returns:
            List of field names
        """
        try:
            with open(file_path, 'r') as f:
                fields = [line.strip() for line in f if line.strip()]
            return fields
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            sys.exit(1)

    def load_fields_with_labels(self, file_path: str) -> Dict[str, Dict[str, str]]:
        """
        Load fields from CSV with API names, labels, and optional types
        Format: Label,API_Name or Label,API_Name,Type

        Args:
            file_path: Path to CSV file

        Returns:
            Dictionary mapping API names to dict with 'label' and 'type' keys
            Example: {'Email__c': {'label': 'Email Address', 'type': 'Email'}}
        """
        import csv

        fields_dict = {}

        try:
            with open(file_path, 'r') as f:
                # Try to detect if it's CSV or simple text file
                first_line = f.readline().strip()
                f.seek(0)

                if ',' in first_line:
                    # CSV format with labels and optional types
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            # Column order: Label, API_Name, Type (optional)
                            label = row[0].strip()
                            api_name = row[1].strip() if len(row) > 1 and row[1].strip() else label
                            field_type = row[2].strip() if len(row) > 2 and row[2].strip() else None

                            fields_dict[api_name] = {
                                'label': label,
                                'type': field_type
                            }
                else:
                    # Simple text format, use API name as label, no type
                    for line in f:
                        line = line.strip()
                        if line:
                            fields_dict[line] = {
                                'label': line,
                                'type': None
                            }

            return fields_dict

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            sys.exit(1)

    def extract_numbers(self, field_name: str) -> set:
        """
        Extract all numbers from a field name

        Args:
            field_name: Field name to extract numbers from

        Returns:
            Set of numbers found in the field name
        """
        import re
        numbers = re.findall(r'\d+', field_name)
        return set(numbers)

    def normalize_field_name(self, field_name: str, preserve_numbers: bool = True) -> str:
        """
        Normalize a field name for better matching by:
        - Splitting camelCase
        - Removing common prefixes and suffixes
        - Expanding abbreviations
        - Standardizing separators
        - Optionally preserving numbers for accurate matching

        Args:
            field_name: Original field name
            preserve_numbers: If True, keep numbers in the normalized name

        Returns:
            Normalized field name
        """
        import re

        # First, split camelCase by inserting spaces before capital letters
        # e.g., "FirstName" -> "First Name"
        field_with_spaces = re.sub(r'([a-z])([A-Z])', r'\1 \2', field_name)

        # Convert to lowercase
        normalized = field_with_spaces.lower()

        # Remove common Ventiv prefixes (B_, etc.)
        if normalized.startswith('b_') or normalized.startswith('b '):
            normalized = normalized[2:]

        # Remove common suffixes (_S, _L, _N, etc.)
        for suffix in [' s', ' l', ' n', ' c', ' d', ' t', '_s', '_l', '_n', '_c', '_d', '_t']:
            if normalized.endswith(suffix):
                normalized = normalized[:-2]
                break

        # Remove Salesforce custom field suffix (__c)
        if '__c' in normalized:
            normalized = normalized.replace('__c', '')

        # Replace underscores with spaces
        normalized = normalized.replace('_', ' ')

        # Split into tokens and process each
        tokens = normalized.split()
        expanded_tokens = []

        for token in tokens:
            # Strip any remaining special characters
            token = token.strip()
            if not token:
                continue

            # If preserve_numbers is False, skip numeric-only tokens
            if not preserve_numbers and token.isdigit():
                continue

            # Expand abbreviations (but not numbers)
            if token in self.abbreviations:
                expanded_tokens.append(self.abbreviations[token])
            else:
                expanded_tokens.append(token)

        # Join tokens back with single space
        normalized = ' '.join(expanded_tokens).strip()

        return normalized

    def calculate_confidence(self, source: str, target: str, source_type: str = None, target_type: str = None) -> Dict[str, float]:
        """
        Calculate confidence score using fuzzy matching and optionally semantic similarity
        Applies penalties for number mismatches to prevent matching Address1 to Address3
        Applies penalties/bonuses based on field type compatibility

        Args:
            source: Source field name
            target: Target field name
            source_type: Optional field type for source
            target_type: Optional field type for target

        Returns:
            Dictionary with fuzzy_score, semantic_score, and combined confidence
        """
        # Extract numbers from both field names
        source_numbers = self.extract_numbers(source)
        target_numbers = self.extract_numbers(target)

        # Normalize field names for better matching (with numbers preserved)
        source_norm = self.normalize_field_name(source, preserve_numbers=True)
        target_norm = self.normalize_field_name(target, preserve_numbers=True)

        # Use multiple matching algorithms on normalized names
        ratio_score = fuzz.ratio(source_norm, target_norm)
        partial_score = fuzz.partial_ratio(source_norm, target_norm)
        token_sort_score = fuzz.token_sort_ratio(source_norm, target_norm)
        token_set_score = fuzz.token_set_ratio(source_norm, target_norm)

        # Also compare original names for cases where normalization might hurt
        orig_ratio = fuzz.ratio(source.lower(), target.lower())
        orig_token_sort = fuzz.token_sort_ratio(source.lower(), target.lower())

        # Weighted average favoring normalized comparisons
        fuzzy_score = (
            ratio_score * 0.25 +
            partial_score * 0.15 +
            token_sort_score * 0.25 +
            token_set_score * 0.25 +
            orig_ratio * 0.05 +
            orig_token_sort * 0.05
        )

        # Apply number mismatch penalty
        # If both fields have numbers but they don't match, heavily penalize the score
        number_penalty = 0.0
        if source_numbers and target_numbers:
            # Both have numbers - they should match
            if source_numbers != target_numbers:
                # Numbers don't match - apply heavy penalty (e.g., Address 1 vs Address 3)
                number_penalty = 40.0  # Reduce score by 40 points
        elif source_numbers or target_numbers:
            # Only one has numbers - moderate penalty
            number_penalty = 10.0  # Reduce score by 10 points

        # Apply type matching bonus/penalty
        type_adjustment = 0.0
        if source_type and target_type:
            compatible, match_quality = self.are_types_compatible(source_type, target_type)

            if match_quality == 'exact':
                # Same type - boost confidence
                type_adjustment = 10.0
            elif match_quality == 'compatible':
                # Compatible types - small boost
                type_adjustment = 5.0
            elif match_quality == 'incompatible':
                # Incompatible types - heavy penalty
                type_adjustment = -50.0

        # Apply the penalties and bonuses (capped at 100)
        fuzzy_score = min(100.0, max(0, fuzzy_score - number_penalty + type_adjustment))

        # Calculate semantic similarity if embeddings are enabled
        semantic_score = 0.0
        if self.use_embeddings:
            semantic_score = self.calculate_semantic_similarity(source, target)
            # Also apply number penalty and type adjustment to semantic score (capped at 100)
            semantic_score = min(100.0, max(0, semantic_score - number_penalty + type_adjustment))

        # Combine scores based on weights (capped at 100)
        if self.use_embeddings and semantic_score > 0:
            combined_confidence = min(100.0, (
                fuzzy_score * self.fuzzy_weight +
                semantic_score * self.semantic_weight
            ))
        else:
            combined_confidence = fuzzy_score

        return {
            'fuzzy_score': round(fuzzy_score, 2),
            'semantic_score': round(semantic_score, 2),
            'confidence': round(combined_confidence, 2)
        }

    def get_confidence_status(self, confidence: float) -> str:
        """
        Get human-readable confidence status

        Args:
            confidence: Confidence score (0-100)

        Returns:
            Status string
        """
        if confidence >= 80:
            return "High Confidence"
        elif confidence >= 60:
            return "Medium Confidence"
        else:
            return "Low Confidence"

    def match_fields(self, ventiv_fields: List[str], salesforce_fields: List[str]) -> List[Dict]:
        """
        Match Ventiv fields to Salesforce fields using fuzzy logic
        Uses Hungarian algorithm for optimal one-to-one assignment

        Args:
            ventiv_fields: List of Ventiv IRM field names
            salesforce_fields: List of Salesforce API field names

        Returns:
            List of match dictionaries
        """
        from scipy.optimize import linear_sum_assignment

        n_ventiv = len(ventiv_fields)
        n_salesforce = len(salesforce_fields)

        # Build cost matrix
        cost_matrix = np.zeros((n_ventiv, n_salesforce))
        scores_matrix = {}

        print(f"\nBuilding cost matrix for {n_ventiv} Ventiv fields x {n_salesforce} Salesforce fields...")

        for i, ventiv_field in enumerate(ventiv_fields):
            for j, sf_field in enumerate(salesforce_fields):
                # Calculate confidence score
                scores = self.calculate_confidence(ventiv_field, sf_field)

                # Store negative confidence as cost (Hungarian minimizes cost)
                cost_matrix[i, j] = -scores['confidence']

                # Store scores for later
                scores_matrix[(i, j)] = scores

        print("Running Hungarian algorithm for optimal one-to-one assignment...")

        # Run Hungarian algorithm
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        # Build matches from optimal assignment
        matches = []
        for i, j in zip(row_indices, col_indices):
            ventiv_field = ventiv_fields[i]
            sf_field = salesforce_fields[j]
            scores = scores_matrix[(i, j)]

            match_data = {
                'ventiv_field': ventiv_field,
                'salesforce_field': sf_field,
                'confidence': scores['confidence'],
                'fuzzy_score': scores['fuzzy_score'],
                'semantic_score': scores['semantic_score'],
                'status': self.get_confidence_status(scores['confidence'])
            }

            matches.append(match_data)

        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x['confidence'], reverse=True)

        print(f"✓ Optimal assignment complete: {len(matches)} unique matches\n")

        return matches

    def match_fields_with_labels(self, ventiv_fields_dict: Dict[str, Dict[str, str]], salesforce_fields_dict: Dict[str, Dict[str, str]]) -> List[Dict]:
        """
        Match Ventiv fields to Salesforce fields using both API names, labels, and types
        Uses Hungarian algorithm for optimal one-to-one assignment

        Args:
            ventiv_fields_dict: Dictionary mapping Ventiv API names to dict with 'label' and 'type'
            salesforce_fields_dict: Dictionary mapping Salesforce API names to dict with 'label' and 'type'

        Returns:
            List of match dictionaries with enhanced information
        """
        from scipy.optimize import linear_sum_assignment

        ventiv_fields = list(ventiv_fields_dict.keys())
        salesforce_fields = list(salesforce_fields_dict.keys())

        n_ventiv = len(ventiv_fields)
        n_salesforce = len(salesforce_fields)

        # Build cost matrix: for each Ventiv field, calculate confidence against all SF fields
        # We'll try matching against both API names and labels and use the better score
        cost_matrix = np.zeros((n_ventiv, n_salesforce))
        match_info = {}  # Store which matched better (API name or label) and the value

        print(f"\nBuilding cost matrix for {n_ventiv} Ventiv fields x {n_salesforce} Salesforce fields...")

        for i, ventiv_field in enumerate(ventiv_fields):
            ventiv_info = ventiv_fields_dict[ventiv_field]
            ventiv_label = ventiv_info['label']
            ventiv_type = ventiv_info.get('type')

            for j, sf_field in enumerate(salesforce_fields):
                sf_info = salesforce_fields_dict[sf_field]
                sf_label = sf_info['label']
                sf_type = sf_info.get('type')

                # Calculate confidence matching Ventiv field to SF API name (with type info)
                api_scores = self.calculate_confidence(ventiv_field, sf_field, ventiv_type, sf_type)
                api_conf = api_scores['confidence']

                # Calculate confidence matching Ventiv field to SF label (with type info)
                label_scores = self.calculate_confidence(ventiv_field, sf_label, ventiv_type, sf_type)
                label_conf = label_scores['confidence']

                # Also try matching Ventiv label to SF API and label (with type info)
                ventiv_label_to_api_scores = self.calculate_confidence(ventiv_label, sf_field, ventiv_type, sf_type)
                ventiv_label_to_api_conf = ventiv_label_to_api_scores['confidence']

                ventiv_label_to_label_scores = self.calculate_confidence(ventiv_label, sf_label, ventiv_type, sf_type)
                ventiv_label_to_label_conf = ventiv_label_to_label_scores['confidence']

                # Find the best match among all combinations
                best_conf = max(api_conf, label_conf, ventiv_label_to_api_conf, ventiv_label_to_label_conf)

                # Determine which match was best
                if best_conf == api_conf:
                    best_scores = api_scores
                    match_type = 'API Name'
                    matched_value = sf_field
                elif best_conf == label_conf:
                    best_scores = label_scores
                    match_type = 'Label'
                    matched_value = sf_label
                elif best_conf == ventiv_label_to_api_conf:
                    best_scores = ventiv_label_to_api_scores
                    match_type = 'Ventiv Label to API'
                    matched_value = sf_field
                else:
                    best_scores = ventiv_label_to_label_scores
                    match_type = 'Ventiv Label to Label'
                    matched_value = sf_label

                # Store negative confidence as cost (Hungarian minimizes cost)
                cost_matrix[i, j] = -best_conf

                # Store match info for later
                match_info[(i, j)] = {
                    'scores': best_scores,
                    'match_type': match_type,
                    'matched_value': matched_value
                }

        print("Running Hungarian algorithm for optimal one-to-one assignment...")

        # Run Hungarian algorithm - returns row indices and col indices
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        # Build matches from optimal assignment
        matches = []
        for i, j in zip(row_indices, col_indices):
            ventiv_field = ventiv_fields[i]
            sf_field = salesforce_fields[j]
            info = match_info[(i, j)]

            ventiv_info = ventiv_fields_dict[ventiv_field]
            sf_info = salesforce_fields_dict[sf_field]

            match_data = {
                'ventiv_field': ventiv_field,
                'ventiv_label': ventiv_info['label'],
                'ventiv_type': ventiv_info.get('type'),
                'salesforce_field': sf_field,
                'salesforce_label': sf_info['label'],
                'salesforce_type': sf_info.get('type'),
                'confidence': info['scores']['confidence'],
                'fuzzy_score': info['scores']['fuzzy_score'],
                'semantic_score': info['scores']['semantic_score'],
                'status': self.get_confidence_status(info['scores']['confidence']),
                'matched_on': info['match_type'],
                'matched_value': info['matched_value']
            }

            matches.append(match_data)

        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x['confidence'], reverse=True)

        print(f"✓ Optimal assignment complete: {len(matches)} unique matches\n")

        return matches

    def filter_by_threshold(self, matches: List[Dict]) -> List[Dict]:
        """
        Filter matches by confidence threshold

        Args:
            matches: List of match dictionaries

        Returns:
            Filtered list of matches
        """
        return [m for m in matches if m['confidence'] >= self.threshold]

    def save_to_csv(self, matches: List[Dict], output_path: str):
        """
        Save matches to CSV file

        Args:
            matches: List of match dictionaries
            output_path: Path to output CSV file
        """
        if not matches:
            print("Warning: No matches to save")
            return

        df = pd.DataFrame(matches)

        # Base column mappings
        base_map = {
            'ventiv_field': 'Ventiv_Field',
            'salesforce_field': 'Salesforce_Field',
            'confidence': 'Combined_Confidence',
            'status': 'Status'
        }

        # Add optional columns if they exist
        if 'ventiv_label' in df.columns:
            base_map['ventiv_label'] = 'Ventiv_Label'
        if 'salesforce_label' in df.columns:
            base_map['salesforce_label'] = 'Salesforce_Label'
        if 'fuzzy_score' in df.columns:
            base_map['fuzzy_score'] = 'Fuzzy_Score'
        if 'semantic_score' in df.columns:
            base_map['semantic_score'] = 'Semantic_Score'
        if 'matched_on' in df.columns:
            base_map['matched_on'] = 'Matched_On'
        if 'matched_value' in df.columns:
            base_map['matched_value'] = 'Matched_Value'

        df = df.rename(columns=base_map)

        # Reorder columns for better readability
        desired_order = []
        if 'Ventiv_Field' in df.columns:
            desired_order.append('Ventiv_Field')
        if 'Ventiv_Label' in df.columns:
            desired_order.append('Ventiv_Label')
        if 'Salesforce_Field' in df.columns:
            desired_order.append('Salesforce_Field')
        if 'Salesforce_Label' in df.columns:
            desired_order.append('Salesforce_Label')
        if 'Fuzzy_Score' in df.columns:
            desired_order.append('Fuzzy_Score')
        if 'Semantic_Score' in df.columns:
            desired_order.append('Semantic_Score')
        if 'Combined_Confidence' in df.columns:
            desired_order.append('Combined_Confidence')
        if 'Status' in df.columns:
            desired_order.append('Status')
        if 'Matched_On' in df.columns:
            desired_order.append('Matched_On')
        if 'Matched_Value' in df.columns:
            desired_order.append('Matched_Value')

        # Reorder columns
        existing_cols = [col for col in desired_order if col in df.columns]
        df = df[existing_cols]

        df.to_csv(output_path, index=False)
        print(f"Results saved to: {output_path}")

    def save_to_json(self, matches: List[Dict], output_path: str):
        """
        Save matches to JSON file

        Args:
            matches: List of match dictionaries
            output_path: Path to output JSON file
        """
        output_data = {
            'metadata': {
                'total_matches': len(matches),
                'threshold': self.threshold,
                'high_confidence': len([m for m in matches if m['confidence'] >= 80]),
                'medium_confidence': len([m for m in matches if 60 <= m['confidence'] < 80]),
                'low_confidence': len([m for m in matches if m['confidence'] < 60])
            },
            'matches': matches
        }

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"Results saved to: {output_path}")

    def print_summary(self, matches: List[Dict]):
        """
        Print a summary of the matches to console

        Args:
            matches: List of match dictionaries
        """
        print("\n" + "="*80)
        print("FUZZY MATCHING RESULTS")
        print("="*80)
        print(f"\nTotal matches found: {len(matches)}")
        print(f"Confidence threshold: {self.threshold}%\n")

        high_conf = len([m for m in matches if m['confidence'] >= 80])
        med_conf = len([m for m in matches if 60 <= m['confidence'] < 80])
        low_conf = len([m for m in matches if m['confidence'] < 60])

        print(f"High Confidence (>=80%): {high_conf}")
        print(f"Medium Confidence (60-79%): {med_conf}")
        print(f"Low Confidence (<60%): {low_conf}")

        print("\n" + "-"*160)

        # Check if we have label information
        has_ventiv_labels = len(matches) > 0 and 'ventiv_label' in matches[0]
        has_sf_labels = len(matches) > 0 and 'salesforce_label' in matches[0]

        if has_ventiv_labels and has_sf_labels:
            print(f"{'Ventiv Field':<25} {'Ventiv Label':<25} {'SF Field':<25} {'SF Label':<25} {'Conf%':<8} {'Match':<10} {'Status'}")
        elif has_sf_labels:
            print(f"{'Ventiv Field':<25} {'SF API Name':<30} {'SF Label':<30} {'Conf%':<8} {'Match':<10} {'Status'}")
        else:
            print(f"{'Ventiv Field':<30} {'Salesforce Field':<35} {'Conf%':<8} {'Status'}")
        print("-"*160)

        for match in matches[:20]:  # Show top 20
            if has_ventiv_labels and has_sf_labels:
                print(f"{match['ventiv_field']:<25} {match['ventiv_label']:<25} "
                      f"{match['salesforce_field']:<25} {match['salesforce_label']:<25} "
                      f"{match['confidence']:<8} {match['matched_on']:<10} {match['status']}")
            elif has_sf_labels:
                print(f"{match['ventiv_field']:<25} {match['salesforce_field']:<30} "
                      f"{match['salesforce_label']:<30} {match['confidence']:<8} "
                      f"{match['matched_on']:<10} {match['status']}")
            else:
                print(f"{match['ventiv_field']:<30} {match['salesforce_field']:<35} "
                      f"{match['confidence']:<8} {match['status']}")

        if len(matches) > 20:
            print(f"\n... and {len(matches) - 20} more matches")

        print("="*120 + "\n")


def main():
    """Main entry point for the field matcher"""
    parser = argparse.ArgumentParser(
        description='Match Ventiv IRM fields to Salesforce API fields using fuzzy logic'
    )

    parser.add_argument(
        '--ventiv',
        required=True,
        help='Path to file containing Ventiv IRM field names'
    )

    parser.add_argument(
        '--salesforce',
        required=True,
        help='Path to file containing Salesforce API field names'
    )

    parser.add_argument(
        '--threshold',
        type=int,
        default=80,
        help='Minimum confidence score for a match (0-100, default: 80)'
    )

    parser.add_argument(
        '--output',
        help='Output file path (optional)'
    )

    parser.add_argument(
        '--format',
        choices=['csv', 'json'],
        default='csv',
        help='Output format (default: csv)'
    )

    parser.add_argument(
        '--show-all',
        action='store_true',
        help='Show all matches, even those below threshold'
    )

    parser.add_argument(
        '--use-embeddings',
        action='store_true',
        help='Use semantic embeddings for improved matching (requires sentence-transformers)'
    )

    parser.add_argument(
        '--fuzzy-weight',
        type=float,
        default=0.5,
        help='Weight for fuzzy matching score (0-1, default: 0.5)'
    )

    parser.add_argument(
        '--semantic-weight',
        type=float,
        default=0.5,
        help='Weight for semantic similarity score (0-1, default: 0.5)'
    )

    args = parser.parse_args()

    # Validate threshold
    if not 0 <= args.threshold <= 100:
        print("Error: Threshold must be between 0 and 100")
        sys.exit(1)

    # Validate weights
    if not 0 <= args.fuzzy_weight <= 1:
        print("Error: Fuzzy weight must be between 0 and 1")
        sys.exit(1)
    if not 0 <= args.semantic_weight <= 1:
        print("Error: Semantic weight must be between 0 and 1")
        sys.exit(1)

    # Initialize matcher
    matcher = FieldMatcher(
        threshold=args.threshold,
        use_embeddings=args.use_embeddings,
        fuzzy_weight=args.fuzzy_weight,
        semantic_weight=args.semantic_weight
    )

    # Load field lists
    print(f"Loading Ventiv IRM fields from: {args.ventiv}")
    ventiv_fields_dict = matcher.load_fields_with_labels(args.ventiv)
    print(f"Loaded {len(ventiv_fields_dict)} Ventiv fields")

    print(f"Loading Salesforce API fields from: {args.salesforce}")
    salesforce_fields_dict = matcher.load_fields_with_labels(args.salesforce)
    print(f"Loaded {len(salesforce_fields_dict)} Salesforce fields")

    # Determine if we have labels or types
    has_ventiv_labels = any(api != info['label'] for api, info in ventiv_fields_dict.items())
    has_sf_labels = any(api != info['label'] for api, info in salesforce_fields_dict.items())
    has_ventiv_types = any(info.get('type') is not None for info in ventiv_fields_dict.values())
    has_sf_types = any(info.get('type') is not None for info in salesforce_fields_dict.values())

    # Perform matching - always use match_fields_with_labels since it handles the new structure
    print("\nPerforming fuzzy matching...")
    if has_ventiv_labels or has_sf_labels:
        print("Using API names and labels for matching...")
    if has_ventiv_types or has_sf_types:
        print("Using field types for improved accuracy...")
    matches = matcher.match_fields_with_labels(ventiv_fields_dict, salesforce_fields_dict)

    # Filter by threshold unless --show-all is specified
    if not args.show_all:
        matches = matcher.filter_by_threshold(matches)

    # Print summary
    matcher.print_summary(matches)

    # Save to file if output path specified
    if args.output:
        if args.format == 'csv':
            matcher.save_to_csv(matches, args.output)
        else:
            matcher.save_to_json(matches, args.output)

    # Return exit code based on results
    if len(matches) == 0:
        print("Warning: No matches found above threshold")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
