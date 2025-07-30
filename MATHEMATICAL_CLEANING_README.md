# Mathematical Text Cleaning Implementation

## Overview
This implementation adds comprehensive regex handling for mathematical expressions and LaTeX formatting in questions and options. It efficiently cleans text without affecting other functionality.

## Components Added

### 1. Core Cleaning Function (`clean_mathematical_text`)
- **Location**: `backend/neet_app/views/utils.py`
- **Purpose**: Converts LaTeX/regex patterns to Unicode equivalents
- **Features**:
  - Handles fractions: `\frac{a}{b}` → `(a/b)`
  - Converts superscripts: `^{2}` → `²`
  - Converts subscripts: `_{2}` → `₂`
  - Greek letters: `\alpha` → `α`
  - Mathematical symbols: `\times` → `×`
  - Removes LaTeX environments and commands
  - Error handling with fallback to original text

### 2. Integration Points

#### A. Question Sync (`sync_questions_from_neo4j`)
- **When**: During data import from Neo4j
- **What**: Automatically cleans questions and options before saving
- **Benefit**: All new questions are cleaned at import time

#### B. Question Generation (`generate_questions_for_topics`)
- **When**: During test session creation
- **What**: Checks and cleans questions if LaTeX patterns detected
- **Benefit**: Handles legacy questions not yet cleaned

#### C. Bulk Cleaning API (`clean_existing_questions`)
- **Endpoint**: `GET/POST /api/dashboard/clean-existing-questions/`
- **Purpose**: Clean all existing questions in database
- **Features**: Batch processing, transaction safety

#### D. Management Command (`clean_questions`)
- **Usage**: `python manage.py clean_questions [--dry-run] [--batch-size=100]`
- **Purpose**: Command-line bulk cleaning with progress tracking
- **Features**: Dry-run mode, customizable batch size

## Usage Examples

### 1. Automatic Cleaning (New Questions)
```python
# When syncing from Neo4j - automatic
python manage.py shell -c "
from neet_app.views.utils import sync_questions_from_neo4j
result = sync_questions_from_neo4j()
print(result)
"
```

### 2. Clean Existing Questions (API)
```bash
curl -X POST http://localhost:8000/api/dashboard/clean-existing-questions/
```

### 3. Clean Existing Questions (Command Line)
```bash
# Dry run to see what would be changed
python manage.py clean_questions --dry-run

# Actual cleaning
python manage.py clean_questions

# Custom batch size
python manage.py clean_questions --batch-size=50
```

### 4. Manual Cleaning (In Code)
```python
from neet_app.views.utils import clean_mathematical_text

# Clean individual text
original = r"T^{2}=Kr^{3} and F = \frac{GMm}{r^2}"
cleaned = clean_mathematical_text(original)
print(cleaned)  # Output: T²=Kr³ and F = (GMm/r²)
```

## Supported Conversions

### Mathematical Expressions
- `\frac{a}{b}` → `(a/b)`
- `\sqrt{x}` → `√(x)`
- `x^{2}` → `x²`
- `H_{2}O` → `H₂O`

### Greek Letters
- `\alpha` → `α`
- `\beta` → `β`
- `\pi` → `π`
- `\theta` → `θ`

### Mathematical Symbols
- `\times` → `×`
- `\div` → `÷`
- `\pm` → `±`
- `\leq` → `≤`
- `\geq` → `≥`

### LaTeX Environments
- Removes `\begin{equation}` and `\end{equation}`
- Removes `$$` delimiters
- Removes `\text{}`, `\mathrm{}`, `\mathbf{}` wrappers

## Performance Considerations

1. **Batch Processing**: Processes questions in configurable batches (default: 100)
2. **Transaction Safety**: Uses database transactions for consistency
3. **Lazy Cleaning**: Only cleans questions that contain LaTeX patterns
4. **Caching**: Questions are cleaned once and saved to database
5. **Error Handling**: Graceful fallback to original text if cleaning fails

## Testing

Run the test script to see examples:
```bash
cd backend
python test_cleaning.py
```

## Integration with Test Sessions

When a test session is created:
1. Questions are fetched for selected topics
2. Any questions with LaTeX patterns are automatically cleaned
3. Cleaned questions are saved back to database
4. Future test sessions will use the cleaned versions

This ensures a seamless user experience with readable mathematical expressions.
