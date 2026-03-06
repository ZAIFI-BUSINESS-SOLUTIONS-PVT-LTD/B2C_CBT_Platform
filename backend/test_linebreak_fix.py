"""
Quick test to verify line break preservation in clean_mathematical_text
Run: python backend/test_linebreak_fix.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')

import django
django.setup()

from neet_app.views.utils import clean_mathematical_text

# Test case matching the user's example
test_input = """Given below are two statements: one is labelled as Assertion (A) and the other is labelled as Reason (R).
Assertion (A): All vertebrates are chordates but all chordates are not vertebrate.
Reason (R): The members of subphylum vertebrata possess notochord during the embryonic period, the notochord is replaced by cartilaginous or bony vertebral column in adults.
In the light of the above statements, choose the correct answer from the options given below:"""

print("=" * 80)
print("TESTING LINE BREAK PRESERVATION")
print("=" * 80)
print("\nINPUT TEXT:")
print(repr(test_input))
print("\nVISUAL INPUT:")
print(test_input)
print("\n" + "-" * 80)

result = clean_mathematical_text(test_input)

print("\nOUTPUT TEXT:")
print(repr(result))
print("\nVISUAL OUTPUT:")
print(result)
print("\n" + "=" * 80)

# Verify newlines are preserved
newline_count_input = test_input.count('\n')
newline_count_output = result.count('\n')

print(f"\nNewlines in input:  {newline_count_input}")
print(f"Newlines in output: {newline_count_output}")

if newline_count_input == newline_count_output:
    print("✅ SUCCESS: Line breaks preserved!")
else:
    print("❌ FAILURE: Line breaks were lost!")
    sys.exit(1)

# Test with LaTeX content
test_latex = """What is the value of \\frac{1}{2}?
Option A: 0.5
Option B: 1"""

print("\n" + "=" * 80)
print("TESTING WITH LATEX CONTENT")
print("=" * 80)
print("\nINPUT:")
print(repr(test_latex))

result_latex = clean_mathematical_text(test_latex)
print("\nOUTPUT:")
print(repr(result_latex))
print("\nVISUAL:")
print(result_latex)

if '\n' in result_latex:
    print("✅ Line breaks preserved with LaTeX content!")
else:
    print("❌ Line breaks lost with LaTeX content!")
    sys.exit(1)

print("\n" + "=" * 80)
print("ALL TESTS PASSED! ✅")
print("=" * 80)
