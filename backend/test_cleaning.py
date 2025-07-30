"""
Test script to demonstrate the mathematical text cleaning functionality
"""

# Sample test data that might come from Neo4j
test_cases = [
    {
        'input': r"Kepler's third law states that square of period of revolution (T) of a planet around the sun, is proportional to third power of average distance r between sun and planet i.e., T^{2}=Kr^{3} here K is constant.",
        'expected_output': "Kepler's third law states that square of period of revolution (T) of a planet around the sun, is proportional to third power of average distance r between sun and planet i.e., T²=Kr³ here K is constant."
    },
    {
        'input': r"The force of attraction between masses is F = $$\frac{GMm}{r^2}$$, here G is gravitational constant.",
        'expected_output': "The force of attraction between masses is F = (GMm/r²), here G is gravitational constant."
    },
    {
        'input': r"The quadratic formula is $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$",
        'expected_output': "The quadratic formula is x = (-b ± √(b² - 4ac)/2a)"
    },
    {
        'input': r"Energy equation: $E = mc^2$ where c is speed of light",
        'expected_output': "Energy equation: E = mc² where c is speed of light"
    },
    {
        'input': r"Greek letters: $\alpha$, $\beta$, $\gamma$, $\pi$, $\theta$",
        'expected_output': "Greek letters: α, β, γ, π, θ"
    }
]

def test_cleaning():
    """Test the cleaning function with sample data"""
    print("Testing Mathematical Text Cleaning Function")
    print("=" * 50)
    
    # This would normally import from the views.utils
    # from neet_app.views.utils import clean_mathematical_text
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}:")
        print(f"Input:    {test_case['input']}")
        # In actual usage: cleaned = clean_mathematical_text(test_case['input'])
        print(f"Expected: {test_case['expected_output']}")
        print("-" * 30)

if __name__ == "__main__":
    test_cleaning()
