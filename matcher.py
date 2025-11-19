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

    def load_fields_with_labels(self, file_path: str) -> Dict[str, str]:
        """
        Load Salesforce fields from CSV with API names and labels
        Format: API_Name,Label (or just API_Name for simple format)

        Args:
            file_path: Path to CSV file

        Returns:
            Dictionary mapping API names to labels (or API name if no label)
        """
        import csv

        fields_dict = {}

        try:
            with open(file_path, 'r') as f:
                # Try to detect if it's CSV or simple text file
                first_line = f.readline().strip()
                f.seek(0)

                if ',' in first_line:
                    # CSV format with labels
                    reader = csv.reader(f)
                    for row in reader:
                        if row and row[0].strip():
                            api_name = row[0].strip()
                            label = row[1].strip() if len(row) > 1 and row[1].strip() else api_name
                            fields_dict[api_name] = label
                else:
                    # Simple text format, use API name as label
                    for line in f:
                        line = line.strip()
                        if line:
                            fields_dict[line] = line

            return fields_dict

        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            sys.exit(1)

    def normalize_field_name(self, field_name: str) -> str:
        """
        Normalize a field name for better matching by:
        - Splitting camelCase
        - Removing common prefixes and suffixes
        - Expanding abbreviations
        - Standardizing separators

        Args:
            field_name: Original field name

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

            # Expand abbreviations
            if token in self.abbreviations:
                expanded_tokens.append(self.abbreviations[token])
            else:
                expanded_tokens.append(token)

        # Join tokens back with single space
        normalized = ' '.join(expanded_tokens).strip()

        return normalized

    def calculate_confidence(self, source: str, target: str) -> Dict[str, float]:
        """
        Calculate confidence score using fuzzy matching and optionally semantic similarity

        Args:
            source: Source field name
            target: Target field name

        Returns:
            Dictionary with fuzzy_score, semantic_score, and combined confidence
        """
        # Normalize field names for better matching
        source_norm = self.normalize_field_name(source)
        target_norm = self.normalize_field_name(target)

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

        # Calculate semantic similarity if embeddings are enabled
        semantic_score = 0.0
        if self.use_embeddings:
            semantic_score = self.calculate_semantic_similarity(source, target)

        # Combine scores based on weights
        if self.use_embeddings and semantic_score > 0:
            combined_confidence = (
                fuzzy_score * self.fuzzy_weight +
                semantic_score * self.semantic_weight
            )
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

        Args:
            ventiv_fields: List of Ventiv IRM field names
            salesforce_fields: List of Salesforce API field names

        Returns:
            List of match dictionaries
        """
        matches = []

        # Create a custom scorer that uses normalized field names
        def normalized_scorer(query, choice, **kwargs):
            query_norm = self.normalize_field_name(query)
            choice_norm = self.normalize_field_name(choice)
            return fuzz.token_sort_ratio(query_norm, choice_norm, **kwargs)

        for ventiv_field in ventiv_fields:
            # Find the best match using rapidfuzz with normalized scorer
            best_match = process.extractOne(
                ventiv_field,
                salesforce_fields,
                scorer=normalized_scorer
            )

            if best_match:
                sf_field, score, _ = best_match

                # Calculate more detailed confidence score
                scores = self.calculate_confidence(ventiv_field, sf_field)

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

        return matches

    def match_fields_with_labels(self, ventiv_fields_dict: Dict[str, str], salesforce_fields_dict: Dict[str, str]) -> List[Dict]:
        """
        Match Ventiv fields to Salesforce fields using both API names and labels

        Args:
            ventiv_fields_dict: Dictionary mapping Ventiv API names to labels
            salesforce_fields_dict: Dictionary mapping Salesforce API names to labels

        Returns:
            List of match dictionaries with enhanced information
        """
        matches = []

        # Create a custom scorer that uses normalized field names
        def normalized_scorer(query, choice, **kwargs):
            query_norm = self.normalize_field_name(query)
            choice_norm = self.normalize_field_name(choice)
            return fuzz.token_sort_ratio(query_norm, choice_norm, **kwargs)

        for ventiv_field in ventiv_fields_dict.keys():
            best_api_scores = None
            best_label_scores = None
            best_api_match = None
            best_label_match = None

            # Match against API names
            api_names = list(salesforce_fields_dict.keys())
            api_match = process.extractOne(
                ventiv_field,
                api_names,
                scorer=normalized_scorer
            )

            if api_match:
                best_api_match = api_match[0]
                best_api_scores = self.calculate_confidence(ventiv_field, best_api_match)

            # Match against labels
            labels_to_api = {label: api for api, label in salesforce_fields_dict.items()}
            unique_labels = list(labels_to_api.keys())

            label_match = process.extractOne(
                ventiv_field,
                unique_labels,
                scorer=normalized_scorer
            )

            if label_match:
                best_label = label_match[0]
                best_label_match = labels_to_api[best_label]
                best_label_scores = self.calculate_confidence(ventiv_field, best_label)

            # Choose the best match between API name and label based on confidence
            api_conf = best_api_scores['confidence'] if best_api_scores else 0
            label_conf = best_label_scores['confidence'] if best_label_scores else 0

            if api_conf >= label_conf:
                final_match = best_api_match
                final_scores = best_api_scores
                match_type = 'API Name'
                matched_value = best_api_match
            else:
                final_match = best_label_match
                final_scores = best_label_scores
                match_type = 'Label'
                matched_value = salesforce_fields_dict[best_label_match]

            if final_match and final_scores:
                match_data = {
                    'ventiv_field': ventiv_field,
                    'ventiv_label': ventiv_fields_dict[ventiv_field],
                    'salesforce_field': final_match,
                    'salesforce_label': salesforce_fields_dict[final_match],
                    'confidence': final_scores['confidence'],
                    'fuzzy_score': final_scores['fuzzy_score'],
                    'semantic_score': final_scores['semantic_score'],
                    'status': self.get_confidence_status(final_scores['confidence']),
                    'matched_on': match_type,
                    'matched_value': matched_value
                }

                matches.append(match_data)

        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x['confidence'], reverse=True)

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

    # Determine if we have labels (CSV format with 2 columns)
    has_ventiv_labels = any(api != label for api, label in ventiv_fields_dict.items())
    has_sf_labels = any(api != label for api, label in salesforce_fields_dict.items())

    # Perform matching
    print("\nPerforming fuzzy matching...")
    if has_ventiv_labels or has_sf_labels:
        print("Using API names and labels for matching...")
        matches = matcher.match_fields_with_labels(ventiv_fields_dict, salesforce_fields_dict)
    else:
        print("Using API names only for matching...")
        ventiv_fields = list(ventiv_fields_dict.keys())
        salesforce_fields = list(salesforce_fields_dict.keys())
        matches = matcher.match_fields(ventiv_fields, salesforce_fields)

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
