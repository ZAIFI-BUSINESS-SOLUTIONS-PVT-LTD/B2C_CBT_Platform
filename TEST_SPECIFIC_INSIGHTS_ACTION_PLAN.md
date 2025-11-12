# Test-Specific Subject-Wise Insight Implementation Plan

## 📋 Executive Summary

This document outlines the implementation plan for adding **Test-Specific Subject-Wise Insights** to the NeetNinja platform. This feature will generate per-test, per-subject insights with 3 zones (Steady, Edge, Focus) containing 2 actionable points each, displayed in the Analysis tab.

**Key Principle:** Zero disruption to existing 4-card insights (Strength, Weakness, Study Plan, Last Test Feedback).

---

## 🎯 Current System Analysis

### Existing Insights (4 Cards) - UNCHANGED
1. **Strength Topics** - High accuracy (≥80%) with good time
2. **Weakness Topics** - Low accuracy (<60%) 
3. **Study Plan** - Mix of weak topics with actionable suggestions
4. **Last Test Feedback** - Most recent test performance

**Current Flow:**
```
Test Submit (TestSessionViewSet.submit)
    ↓
Session marked complete → signals.py (post_save on TestSession)
    ↓
update_subject_scores_on_completion() → calculate subject scores
    ↓
generate_insights_task (Celery) OR background thread
    ↓
get_student_insights() in insights_views.py
    ↓
Saves to StudentInsight model (overall insights)
```

**Current Models:**
- `StudentInsight` - Stores overall insights (strength/weakness/study plan/last test)
- Stores: `llm_strengths`, `llm_weaknesses`, `llm_study_plan`, `llm_last_test_feedback`

---

## 🆕 New Feature Requirements

### 5th Insight Card: "Test-Specific Subject-Wise Insight"
- Generated **after every test** (alongside the 4 existing cards)
- **Per-test, per-subject** analysis (Physics, Chemistry, Botany, Zoology)
- **3 Zones per subject:**
  - 🟢 **Steady Zone** - 2 points (consistent strengths)
  - 🟠 **Edge Zone** - 2 points (borderline, needs mild improvement)
  - 🔴 **Focus Zone** - 2 points (critical weak areas)

### Data Structure Per Question
Each question sent to LLM includes:
```json
{
  "question": "text",
  "options": {"A": "...", "B": "...", "C": "...", "D": "..."},
  "correct_answer": "A",
  "selected_answer": "B",
  "topic": "Mechanics",
  "time_taken": 120
}
```

---

## 🏗️ Implementation Plan

### Phase 1: Database Schema (30 mins)

#### 1.1 Create New Model: `TestSubjectZoneInsight`

**Location:** `backend/neet_app/models.py`

```python
class TestSubjectZoneInsight(models.Model):
    """
    Stores test-specific, subject-wise zone insights (Steady, Edge, Focus).
    Generated after each test completion alongside overall insights.
    """
    id = models.AutoField(primary_key=True)
    
    # Foreign keys
    student = models.ForeignKey(
        StudentProfile, 
        on_delete=models.CASCADE, 
        to_field='student_id', 
        db_column='student_id'
    )
    test_session = models.ForeignKey(
        TestSession, 
        on_delete=models.CASCADE, 
        db_column='test_session_id'
    )
    
    # Subject identification
    subject = models.CharField(max_length=20)  # Physics, Chemistry, Botany, Zoology
    
    # Zone insights (each is a list of 2 strings)
    steady_zone = models.JSONField(default=list, blank=True)  # 2 points
    edge_zone = models.JSONField(default=list, blank=True)    # 2 points
    focus_zone = models.JSONField(default=list, blank=True)   # 2 points
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Question data used for generation (for debugging/audit)
    questions_analyzed = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'test_subject_zone_insights'
        verbose_name = 'Test Subject Zone Insight'
        verbose_name_plural = 'Test Subject Zone Insights'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'test_session']),
            models.Index(fields=['test_session', 'subject']),
        ]
        # One insight record per test per subject
        unique_together = [['test_session', 'subject']]
    
    def __str__(self):
        return f"{self.subject} zones for Test {self.test_session.id} - {self.student.student_id}"
```

#### 1.2 Create Migration
```bash
cd F:\ZAIFI\NeetNinja\backend
python manage.py makemigrations neet_app -n add_test_subject_zone_insights
python manage.py migrate
```

---

### Phase 2: LLM Service for Zone Generation (1 hour)

#### 2.1 Create Zone Insight Generator

**Location:** `backend/neet_app/services/zone_insights_service.py` (NEW FILE)

**Key Functions:**
1. `extract_subject_questions(test_session_id, subject)` - Get all questions for a subject
2. `prepare_questions_for_llm(questions)` - Format question data
3. `generate_zone_insights_for_subject(subject, questions)` - Call LLM
4. `parse_llm_zone_response(llm_response)` - Extract 6 points (2 per zone)
5. `generate_all_subject_zones(test_session_id)` - Main orchestrator

**LLM Prompt Template:**
```python
ZONE_INSIGHT_PROMPT = """
You are an expert NEET exam tutor analyzing a student's test performance for {subject}.

Analyze the following questions and their answers to generate exactly 6 insights grouped into 3 zones:

🟢 Steady Zone (2 points): Areas where the student is consistently performing well
🟠 Edge Zone (2 points): Borderline concepts needing mild improvement  
🔴 Focus Zone (2 points): Critical weak areas requiring priority attention

RULES:
- Each point must be 18-20 words maximum
- Be specific and actionable
- Avoid formatting markers like ** or asterisks
- Analyze question-by-question patterns (correctness, speed, topic consistency)
- Prioritize insights by impact and actionability

Questions Data:
{questions_json}

Return EXACTLY 6 insights in this JSON format:
{{
  "steady_zone": ["point 1", "point 2"],
  "edge_zone": ["point 1", "point 2"],
  "focus_zone": ["point 1", "point 2"]
}}
"""
```

**Implementation Notes:**
- Reuse existing `GeminiClient` from `services/ai/gemini_client.py`
- Handle API errors gracefully with fallback messages
- Limit questions per subject to prevent token overflow (max 20-30 questions)

---

### Phase 3: Integration into Test Flow (1 hour)

#### 3.1 Modify Signal Handler

**Location:** `backend/neet_app/signals.py`

**Current flow:**
```python
@receiver(post_save, sender=TestSession)
def update_subject_scores_on_completion(sender, instance, created, **kwargs):
    # ... existing code ...
    instance.calculate_and_update_subject_scores()
    # ... trigger generate_insights_task ...
```

**Add after existing insights generation:**
```python
# After existing insights task is queued
try:
    from .tasks import generate_zone_insights_task
    generate_zone_insights_task.delay(instance.id)
    print(f"🎯 Enqueued zone insights task for test {instance.id}")
except Exception as e:
    print(f"⚠️ Failed to enqueue zone insights: {e}")
```

#### 3.2 Create Celery Task

**Location:** `backend/neet_app/tasks.py`

```python
@celery_app.task(bind=True, name='neet_app.tasks.generate_zone_insights_task')
def generate_zone_insights_task(self, test_session_id: int):
    """
    Generate zone insights for all subjects in a completed test.
    Runs asynchronously after test submission.
    """
    try:
        from .services.zone_insights_service import generate_all_subject_zones
        from .models import TestSession
        
        test_session = TestSession.objects.get(id=test_session_id)
        
        print(f"🎯 Generating zone insights for test {test_session_id}")
        result = generate_all_subject_zones(test_session_id)
        
        print(f"✅ Zone insights generated for {len(result)} subjects")
        return {
            'status': 'success',
            'test_session_id': test_session_id,
            'subjects_processed': list(result.keys())
        }
    except Exception as e:
        logger.exception('generate_zone_insights_task failed')
        return {
            'status': 'error',
            'error': str(e)
        }
```

---

### Phase 4: API Endpoints (1 hour)

#### 4.1 Create Zone Insights Views

**Location:** `backend/neet_app/views/zone_insights_views.py` (NEW FILE)

**Endpoints:**

1. **GET /api/zone-insights/tests/** - List all tests for dropdown
   ```python
   @api_view(['GET'])
   @permission_classes([IsAuthenticated])
   def get_student_tests(request):
       """Get list of completed tests for the authenticated student"""
       student_id = request.user.student_id
       
       tests = TestSession.objects.filter(
           student_id=student_id,
           is_completed=True
       ).values(
           'id', 'test_type', 'start_time', 'end_time',
           'correct_answers', 'incorrect_answers', 'total_questions',
           'physics_score', 'chemistry_score', 'botany_score', 'zoology_score'
       ).order_by('-end_time')
       
       return Response({
           'status': 'success',
           'tests': list(tests)
       })
   ```

2. **GET /api/zone-insights/test/{test_id}/** - Get zone insights for a test
   ```python
   @api_view(['GET'])
   @permission_classes([IsAuthenticated])
   def get_test_zone_insights(request, test_id):
       """Get zone insights for a specific test"""
       student_id = request.user.student_id
       
       # Verify ownership
       test = get_object_or_404(
           TestSession, 
           id=test_id, 
           student_id=student_id,
           is_completed=True
       )
       
       # Get zone insights
       insights = TestSubjectZoneInsight.objects.filter(
           test_session_id=test_id
       ).values('subject', 'steady_zone', 'edge_zone', 'focus_zone')
       
       # Calculate marks
       total_marks = (test.correct_answers * 4) - (test.incorrect_answers * 1)
       max_marks = test.total_questions * 4
       
       return Response({
           'status': 'success',
           'test_info': {
               'id': test.id,
               'start_time': test.start_time,
               'total_marks': total_marks,
               'max_marks': max_marks,
               'subject_scores': {
                   'Physics': test.physics_score,
                   'Chemistry': test.chemistry_score,
                   'Botany': test.botany_score,
                   'Zoology': test.zoology_score
               }
           },
           'zone_insights': list(insights)
       })
   ```

#### 4.2 Add URL Routes

**Location:** `backend/neet_app/urls.py`

```python
from .views.zone_insights_views import get_student_tests, get_test_zone_insights

urlpatterns = [
    # ... existing routes ...
    
    # Zone insights endpoints
    path('zone-insights/tests/', get_student_tests, name='zone_insights_tests'),
    path('zone-insights/test/<int:test_id>/', get_test_zone_insights, name='zone_insights_test'),
]
```

---

### Phase 5: Frontend Implementation (2 hours)

#### 5.1 Analysis Tab Modifications

**Location:** `client/src/pages/AnalysisPage.tsx` (or similar)

**UI Components Needed:**
1. Test Selector dropdown
2. Test summary strip (marks display)
3. Subject insight cards with 3 zones each

**Example Structure:**
```typescript
interface ZoneInsight {
  subject: string;
  steady_zone: string[];
  edge_zone: string[];
  focus_zone: string[];
}

interface TestInfo {
  id: number;
  total_marks: number;
  max_marks: number;
  subject_scores: {
    Physics: number;
    Chemistry: number;
    Botany: number;
    Zoology: number;
  };
}

const AnalysisPage = () => {
  const [selectedTest, setSelectedTest] = useState<number | null>(null);
  const [testList, setTestList] = useState<any[]>([]);
  const [testInfo, setTestInfo] = useState<TestInfo | null>(null);
  const [zoneInsights, setZoneInsights] = useState<ZoneInsight[]>([]);
  
  // Fetch test list on mount
  useEffect(() => {
    fetch('/api/zone-insights/tests/')
      .then(res => res.json())
      .then(data => setTestList(data.tests));
  }, []);
  
  // Fetch zone insights when test selected
  useEffect(() => {
    if (selectedTest) {
      fetch(`/api/zone-insights/test/${selectedTest}/`)
        .then(res => res.json())
        .then(data => {
          setTestInfo(data.test_info);
          setZoneInsights(data.zone_insights);
        });
    }
  }, [selectedTest]);
  
  return (
    <div className="analysis-page">
      {/* Test Selector */}
      <select onChange={(e) => setSelectedTest(Number(e.target.value))}>
        <option>Select a test...</option>
        {testList.map(test => (
          <option key={test.id} value={test.id}>
            Test {test.id} - {new Date(test.start_time).toLocaleDateString()}
          </option>
        ))}
      </select>
      
      {/* Test Summary */}
      {testInfo && (
        <div className="test-summary">
          <h3>Total: {testInfo.total_marks} / {testInfo.max_marks}</h3>
          <div className="subject-marks">
            <span>Physics: {testInfo.subject_scores.Physics}</span>
            <span>Chemistry: {testInfo.subject_scores.Chemistry}</span>
            <span>Botany: {testInfo.subject_scores.Botany}</span>
            <span>Zoology: {testInfo.subject_scores.Zoology}</span>
          </div>
        </div>
      )}
      
      {/* Zone Insights */}
      {zoneInsights.map(insight => (
        <div key={insight.subject} className="subject-card">
          <h4>{insight.subject}</h4>
          
          <div className="zone steady-zone">
            <h5>🟢 Steady Zone</h5>
            {insight.steady_zone.map((point, i) => (
              <p key={i}>• {point}</p>
            ))}
          </div>
          
          <div className="zone edge-zone">
            <h5>🟠 Edge Zone</h5>
            {insight.edge_zone.map((point, i) => (
              <p key={i}>• {point}</p>
            ))}
          </div>
          
          <div className="zone focus-zone">
            <h5>🔴 Focus Zone</h5>
            {insight.focus_zone.map((point, i) => (
              <p key={i}>• {point}</p>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
```

---

## 🔒 Safety & Testing Strategy

### 1. Non-Disruptive Integration
- ✅ Existing 4 insights remain unchanged
- ✅ New model separate from `StudentInsight`
- ✅ New task runs independently
- ✅ Failure in zone insights doesn't affect existing insights

### 2. Testing Checklist
- [ ] Create migration and verify schema
- [ ] Test zone insights service with sample questions
- [ ] Test Celery task execution
- [ ] Test API endpoints with authenticated user
- [ ] Test frontend dropdown and data display
- [ ] Verify existing 4-card insights still work
- [ ] Test with multiple subjects in a test
- [ ] Test with missing subjects (e.g., only Physics/Chemistry)

### 3. Rollback Plan
If issues occur:
1. Disable task in `signals.py` (comment out `generate_zone_insights_task.delay()`)
2. Hide frontend component
3. Data remains in database for future reactivation

---

## 📊 Database Changes Summary

### New Table: `test_subject_zone_insights`
| Column | Type | Description |
|--------|------|-------------|
| id | AutoField | Primary key |
| student_id | FK → StudentProfile | Owner of insight |
| test_session_id | FK → TestSession | Associated test |
| subject | CharField(20) | Physics/Chemistry/Botany/Zoology |
| steady_zone | JSONField | 2 points (list) |
| edge_zone | JSONField | 2 points (list) |
| focus_zone | JSONField | 2 points (list) |
| questions_analyzed | JSONField | Debug/audit data |
| created_at | DateTimeField | Timestamp |

**Indexes:**
- (`student_id`, `test_session_id`)
- (`test_session_id`, `subject`)

**Unique Constraint:**
- (`test_session_id`, `subject`)

---

## 🚀 Deployment Steps

### Step 1: Backend (Database + API)
```bash
# 1. Pull latest code
cd F:\ZAIFI\NeetNinja
git pull

# 2. Add new model to models.py
# (paste TestSubjectZoneInsight class)

# 3. Create migration
cd backend
python manage.py makemigrations neet_app -n add_test_subject_zone_insights
python manage.py migrate

# 4. Create service file
# Create services/zone_insights_service.py

# 5. Add task to tasks.py
# (paste generate_zone_insights_task)

# 6. Update signals.py
# (add zone insights trigger)

# 7. Create views file
# Create views/zone_insights_views.py

# 8. Update urls.py
# (add zone insights routes)

# 9. Restart Django
python manage.py runserver
```

### Step 2: Frontend (UI)
```bash
cd F:\ZAIFI\NeetNinja\client

# 1. Create/modify Analysis page component
# (add test selector, zone display)

# 2. Test locally
npm run dev

# 3. Build for production
npm run build
```

### Step 3: Verify
1. ✅ Submit a test
2. ✅ Check Celery logs for zone insights task
3. ✅ Query database: `SELECT * FROM test_subject_zone_insights;`
4. ✅ Open Analysis tab
5. ✅ Select test from dropdown
6. ✅ Verify zone insights display correctly

---

## 📝 Code Files to Create/Modify

### New Files (5)
1. `backend/neet_app/services/zone_insights_service.py` - Zone generation logic
2. `backend/neet_app/views/zone_insights_views.py` - API endpoints
3. `backend/neet_app/migrations/XXXX_add_test_subject_zone_insights.py` - Migration
4. `client/src/components/ZoneInsightCard.tsx` - UI component
5. `TEST_SPECIFIC_INSIGHTS_ACTION_PLAN.md` - This document

### Modified Files (4)
1. `backend/neet_app/models.py` - Add `TestSubjectZoneInsight` model
2. `backend/neet_app/tasks.py` - Add `generate_zone_insights_task`
3. `backend/neet_app/signals.py` - Trigger zone insights generation
4. `backend/neet_app/urls.py` - Add zone insights routes
5. `client/src/pages/AnalysisPage.tsx` - Add test selector and zone display

---

## ⏱️ Time Estimates

| Phase | Task | Time |
|-------|------|------|
| 1 | Database schema + migration | 30 mins |
| 2 | LLM service implementation | 1 hour |
| 3 | Integration into test flow | 1 hour |
| 4 | API endpoints | 1 hour |
| 5 | Frontend UI | 2 hours |
| **Total** | | **5.5 hours** |

---

## 🎯 Success Criteria

- [x] Existing 4 insights continue to work unchanged
- [ ] New `test_subject_zone_insights` table created
- [ ] Zone insights generated after every test
- [ ] API returns test list and zone insights
- [ ] Frontend displays test selector and subject cards
- [ ] Each subject shows 3 zones with 2 points each
- [ ] Marks calculated correctly (correct × 4 - incorrect × 1)
- [ ] No performance degradation in test submission

---

## 📚 Additional Notes

### Subject Determination Logic
Use existing `TestSession` subject classification:
- `test_session.physics_topics`
- `test_session.chemistry_topics`
- `test_session.botany_topics`
- `test_session.zoology_topics`

### Question Filtering
```python
def extract_subject_questions(test_session_id, subject):
    test_session = TestSession.objects.get(id=test_session_id)
    
    # Get subject-specific topic IDs
    subject_map = {
        'Physics': test_session.physics_topics,
        'Chemistry': test_session.chemistry_topics,
        'Botany': test_session.botany_topics,
        'Zoology': test_session.zoology_topics
    }
    
    topic_ids = subject_map.get(subject, [])
    
    # Get answers for those topics
    answers = TestAnswer.objects.filter(
        session_id=test_session_id,
        question__topic_id__in=topic_ids
    ).select_related('question', 'question__topic')
    
    return answers
```

### LLM Response Parsing
If LLM returns malformed JSON, use fallback:
```python
fallback_zones = {
    'steady_zone': [
        'No steady zone data available for this subject.',
        'Complete more questions to get better insights.'
    ],
    'edge_zone': [
        'No edge zone data available for this subject.',
        'Practice more to identify improvement areas.'
    ],
    'focus_zone': [
        'No focus zone data available for this subject.',
        'Keep practicing to highlight weak areas.'
    ]
}
```

---

## 🔗 Related Documentation

- `backend/neet_app/views/insights_views.py` - Existing insights implementation
- `backend/neet_app/models.py` - Data models
- `backend/neet_app/signals.py` - Test completion hooks
- `IMPLEMENTATION_CONSOLIDATED.md` - Overall platform implementation

---

**Created:** November 11, 2025  
**Author:** GitHub Copilot  
**Status:** Ready for Implementation
