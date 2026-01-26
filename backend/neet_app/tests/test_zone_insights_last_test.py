"""
Unit tests for last test zone insights functionality.
Tests the filtering and selection logic for get_last_test_zone_insights.
"""

import unittest
from neet_app.views.insights_views import is_valid_insight


class TestZoneInsightFiltering(unittest.TestCase):
    """Test cases for insight validation and filtering"""
    
    def test_valid_insights(self):
        """Test that valid insights are correctly identified"""
        valid_insights = [
            "Master equilibrium concepts through Le Chatelier's principle practice.",
            "Focus on balancing chemical equations with speed and accuracy.",
            "Your understanding of photosynthesis pathways shows strong conceptual grasp.",
            "Revise Newton's laws applications in two-dimensional motion problems.",
        ]
        
        for insight in valid_insights:
            self.assertTrue(
                is_valid_insight(insight), 
                f"Expected '{insight}' to be valid"
            )
    
    def test_fallback_phrases_filtered(self):
        """Test that fallback phrases are correctly filtered out"""
        fallback_insights = [
            "No data available for analysis",
            "Insufficient data to generate insights",
            "Continue practicing Physics for better insights",
            "Additional analysis needed for this subject",
            "No insights available yet",
            "Not available at this time",
            "Not enough questions attempted",
            "Complete more tests to see patterns",
            "Take more tests for detailed feedback",
            "Attempt more questions in this subject",
        ]
        
        for insight in fallback_insights:
            self.assertFalse(
                is_valid_insight(insight), 
                f"Expected '{insight}' to be filtered out"
            )
    
    def test_short_insights_filtered(self):
        """Test that very short insights are filtered out"""
        short_insights = [
            "Good job",
            "Practice",
            "Study",
            "",
            "   ",
        ]
        
        for insight in short_insights:
            self.assertFalse(
                is_valid_insight(insight), 
                f"Expected short insight '{insight}' to be filtered out"
            )
    
    def test_none_and_invalid_types(self):
        """Test that None and invalid types are handled"""
        invalid_inputs = [None, 123, [], {}, True]
        
        for invalid_input in invalid_inputs:
            self.assertFalse(
                is_valid_insight(invalid_input), 
                f"Expected {invalid_input} to be invalid"
            )
    
    def test_case_insensitive_filtering(self):
        """Test that filtering is case-insensitive"""
        case_variants = [
            "NO DATA AVAILABLE",
            "No Data Available",
            "no data available",
            "INSUFFICIENT DATA FOR ANALYSIS",
            "Continue Practicing Chemistry For Better Insights",
        ]
        
        for insight in case_variants:
            self.assertFalse(
                is_valid_insight(insight), 
                f"Expected '{insight}' to be filtered (case-insensitive)"
            )


if __name__ == '__main__':
    unittest.main()
