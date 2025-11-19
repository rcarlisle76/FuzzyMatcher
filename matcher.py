#!/usr/bin/env python3
"""
FuzzyMatcher - RMIS Field Mapping Tool
Matches Ventiv IRM fields to Salesforce API fields using fuzzy logic
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from rapidfuzz import fuzz, process
import pandas as pd


class FieldMatcher:
    """Handles fuzzy matching between two sets of field names"""

    def __init__(self, threshold: int = 80):
        """
        Initialize the FieldMatcher

        Args:
            threshold: Minimum confidence score (0-100) for a match
        """
        self.threshold = threshold

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

    def calculate_confidence(self, source: str, target: str) -> float:
        """
        Calculate confidence score using multiple fuzzy matching algorithms

        Args:
            source: Source field name
            target: Target field name

        Returns:
            Confidence score (0-100)
        """
        # Use multiple matching algorithms and average them
        ratio_score = fuzz.ratio(source.lower(), target.lower())
        partial_score = fuzz.partial_ratio(source.lower(), target.lower())
        token_sort_score = fuzz.token_sort_ratio(source.lower(), target.lower())
        token_set_score = fuzz.token_set_ratio(source.lower(), target.lower())

        # Weighted average (token_sort and token_set are more lenient with word order)
        confidence = (
            ratio_score * 0.3 +
            partial_score * 0.2 +
            token_sort_score * 0.25 +
            token_set_score * 0.25
        )

        return round(confidence, 2)

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

        for ventiv_field in ventiv_fields:
            # Find the best match using rapidfuzz
            best_match = process.extractOne(
                ventiv_field,
                salesforce_fields,
                scorer=fuzz.token_sort_ratio
            )

            if best_match:
                sf_field, score, _ = best_match

                # Calculate more detailed confidence score
                confidence = self.calculate_confidence(ventiv_field, sf_field)

                match_data = {
                    'ventiv_field': ventiv_field,
                    'salesforce_field': sf_field,
                    'confidence': confidence,
                    'status': self.get_confidence_status(confidence)
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
        df = pd.DataFrame(matches)
        df.columns = ['Ventiv_Field', 'Salesforce_Field', 'Confidence_Score', 'Status']
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

        print("\n" + "-"*80)
        print(f"{'Ventiv Field':<30} {'Salesforce Field':<35} {'Conf%':<8} {'Status'}")
        print("-"*80)

        for match in matches[:20]:  # Show top 20
            print(f"{match['ventiv_field']:<30} {match['salesforce_field']:<35} "
                  f"{match['confidence']:<8} {match['status']}")

        if len(matches) > 20:
            print(f"\n... and {len(matches) - 20} more matches")

        print("="*80 + "\n")


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

    args = parser.parse_args()

    # Validate threshold
    if not 0 <= args.threshold <= 100:
        print("Error: Threshold must be between 0 and 100")
        sys.exit(1)

    # Initialize matcher
    matcher = FieldMatcher(threshold=args.threshold)

    # Load field lists
    print(f"Loading Ventiv IRM fields from: {args.ventiv}")
    ventiv_fields = matcher.load_fields(args.ventiv)
    print(f"Loaded {len(ventiv_fields)} Ventiv fields")

    print(f"Loading Salesforce API fields from: {args.salesforce}")
    salesforce_fields = matcher.load_fields(args.salesforce)
    print(f"Loaded {len(salesforce_fields)} Salesforce fields")

    # Perform matching
    print("\nPerforming fuzzy matching...")
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
