## Offline Test Upload — Implementation Plan

This document defines the implementation plan for the Offline Test Upload feature (institution admins upload a single Excel file containing questions + student responses). It contains the Excel template, backend design, frontend changes, API contract, validation rules, error-handling, data mapping and test plan.

---

## 1. Goal

Allow institution admins to upload offline (paper) test results in a single Excel file so the platform:
- Persists question and topic data for the institution test
- Creates a `PlatformTest` for the institution
- Creates/links `StudentProfile` records for students
- Creates `TestSession` per student and corresponding `TestAnswer` rows
- Runs existing evaluation and insights pipeline (zone insights + student insights)
- Produces an error report for invalid rows and supports partial success

## 2. High-level flow

1. Institution admin chooses an existing institution and uploads an `.xlsx` file (single-sheet)
2. Backend validates headers and rows, and streams rows grouped by student
3. For each row: create/match Topic and Question (institution-scoped), normalize the correct answer
4. For each student: find or create `StudentProfile` (match by phone, then by name), then create a `TestSession` (platform test) and create `TestAnswer` rows (evaluate correctness)
5. After each student's session is created and answers saved, mark session completed, compute session summary (correct/incorrect/unanswered,time) and enqueue insights tasks
6. Return summary to admin and provide downloadable error CSV for invalid rows

---

## 3. Excel template (single sheet)

Required header row (case-insensitive headers accepted — we will map variants):

- student_name (string) — student full name
- phone_number (string) — mobile in local or E.164 format (used as primary match key)
- email (optional) — used as secondary match key if phone missing
- test_name (string) — name of the institution test (all rows in single upload must share same test_name; endpoint may optionally accept a test_name parameter)
- exam_type (optional) — e.g., `neet`, `jee` (if blank, the institution default will be used)
- subject (string) — Physics/Chemistry/Botany/Zoology/Math/Biology
- topic_name (string) — topic under subject
- question_text (string)
- option_a (string)
- option_b (string)
- option_c (string)
- option_d (string)
- explanation (string)
- correct_answer (string) — canonical answer for the question (e.g., A/B/C/D or numeric/text for NVT)
- opted_answer (string) — student's response (A/B/C/D or text/number)
- question_type (optional)- NVT or blank
- time_taken_seconds (optional integer) — default 1 mins
- answered_at (optional ISO datetime) — default uploaded date



Sample header row:

student_name,phone_number,email,test_name,exam_type,subject,topic_name,question_text,option_a,option_b,option_c,option_d,explanation,correct_answer,opted_answer,question_type,time_taken_seconds,answered_at

Notes:
- All rows must belong to the same `test_name`. If admin supplies a test at upload time (via multipart field) it will be used and per-row `test_name` may be optional.
- We accept different header name variants (e.g., `question`, `question_stem`, `q` mapped to `question_text`) — mapping implemented on backend.

---

## 4. Backend implementation (detailed)

Files to add/change:
- Add: `backend/neet_app/services/offline_results_upload.py` — core service handling parsing, validation, creation and reporting
- Edit: `backend/neet_app/views/institution_admin_views.py` — add endpoint `upload_offline_results` to call the service
- Edit: `backend/neet_app/urls.py` — add route `/api/institution-admin/upload-results/`
- Optionally add unit tests: `backend/tests/test_offline_upload.py`

Design details and responsibilities

1) Header parsing and basic file checks
- Validate `file` exists and extension is `.xlsx`
- Validate file size under configured MAX_FILE_SIZE (e.g., 10 MB)
- Use `openpyxl` with `read_only=True, data_only=True` to stream rows
- Map headers to canonical field names using a mapping table (case-insensitive)

2) Row validation and normalization
- Required per-row fields: `student_name` or `phone_number`, `question_text`, `option_a`..`option_d`, `correct_answer`, `opted_answer`, `topic_name`, `subject`.
- Normalize and validate `phone_number` (strip spaces, optionally normalize to E.164 if helper available)
- Normalize `correct_answer` and `opted_answer` (accept: A/B/C/D | 1/2/3/4 | 'option_a' etc. — transform to canonical 'A'|'B'|'C'|'D' when applicable). For NVT answers keep string/number.
- Normalize subject via `neet_app.views.utils.normalize_subject` (re-use existing helper)

3) Question & Topic persistence
- For each unique (subject, topic_name) create or get `Topic` via `Topic.objects.get_or_create(name=..., subject=...)` using `neet_app.services.institution_upload.get_or_create_topic` logic
- For each unique question_text under that topic and institution test name, create a `Question` row with `institution` and `institution_test_name` set to uploaded `test_name`. Reuse `clean_mathematical_text` to clean fields before create. Observe model uniqueness constraints — if a duplicate exists, reuse it instead of creating a new one.

4) PlatformTest creation
- If the admin did not provide an existing `PlatformTest` to attach results to, create one via `PlatformTest.objects.create(...)` with `is_institution_test=True`, `institution=<inst>`, `exam_type`.
- Set `selected_topics` to unique topic IDs discovered in the file and `total_questions` to count of unique questions.

5) Student matching & creation
- Match by `phone_number` first (primary key); if multiple matches found, pick the best exact phone match. If no phone, try `email`. If both missing or no match, create a `StudentProfile` using provided `student_name` and `phone`/`email` where available.
- For created students: call `StudentProfile.set_unusable_password()` or generate a placeholder email like `{slug(student_name)}@example.com` if email missing; set `institution` to the uploading institution; set `is_active=True` (so analytics include them). Use `neet_app.utils.student_utils.ensure_unique_student_id` to create unique `student_id`.

6) TestSession & TestAnswer creation
- For each student/test pair: create a `TestSession` with:
  - `student_id` = matched/created student's `student_id`
  - `test_type` = 'platform'
  - `platform_test` = platform test created/found
  - `selected_topics` = platform_test.selected_topics or topics from file
  - `start_time` & `end_time` = use `answered_at` if available across rows, otherwise use upload time; set `is_completed=True`.
  - `total_questions` = number of unique question rows assigned to this student (or platform_test.total_questions)
- For each row belonging to that student: create or update a `TestAnswer` row with `session`, `question`, normalized `selected_answer` (or `text_answer`), `is_correct` evaluation (see below), `time_taken`, `answered_at`.
- Use `update_or_create` to avoid duplicate rows if the same student/question appears multiple times.


7) Evaluation
- For MCQ: compare canonical `selected_answer` letter vs `question.correct_answer` using same logic as in `TestAnswerViewSet.create` and `TestSession.submit` (case-insensitive single-letter equality). If `question.correct_answer` is numeric/text (edge case), treat accordingly.
- For NVT: use numeric tolerance `NEET_SETTINGS['NVT_NUMERIC_TOLERANCE']` and case sensitivity setting `NVT_CASE_SENSITIVE` to compare text answers.

8) Finalize session & enqueue insights
- After creating all TestAnswer rows for a student session, compute session aggregates (`correct_answers`, `incorrect_answers`, `unanswered`, `total_time_taken`) and save to `TestSession`.
- Call: `TestSession.calculate_and_update_subject_scores()` (or call after persistence)

- this can be done later skip this llm part(Enqueue Celery tasks: `generate_zone_insights_task.delay(session.id)` and `generate_insights_task.delay(student_id)` so LLM/analytics run asynchronously.)

9) Error handling and partial success
- Maintain an in-memory list (or temporary file) of invalid rows with columns: row_number, raw_data (JSON), error_code, error_message.
- For per-student transactionality: process rows grouped by student inside a `transaction.atomic()` block. If any row for that student errors, roll back that student's session but continue others.
- Return summary: processed_rows, created_sessions_count, created_students_count, questions_created_count, error_count and a downloadable CSV of errors (attach CSV data in response or store under MEDIA_ROOT and return link — implementation option).

10) Logging and auditing
- Log an audit line when admin uploads file (admin username & institution id & test code)
- Add `PlatformTestAudit` or reuse existing audit signals if needed

11) Performance & limits
- Support files up to MAX_ROWS (configurable, e.g., 5000 rows) and MAX_FILE_SIZE (10 MB). Reject above limits.
- Use `bulk_create` for `TestAnswer` creation per session to reduce DB round trips when possible.

---

## 5. API Contract (backend)

Endpoint
- POST /api/institution-admin/upload-results/
- Auth: `institution_admin_required` decorator (same as `upload_test` view)

Request (multipart/form-data)
- file: Excel `.xlsx` (required)
- test_id (optional): numeric id of an existing `PlatformTest` created earlier for this `institution` — if provided, we attach sessions to this test and ignore per-row `test_name`.
- test_name (optional): if `test_id` not provided, create a new `PlatformTest` using this name (required if test_id missing)
- exam_type (optional)

Response (201 created) — success summary

{
  "success": true,
  "processed_rows": 120,
  "created_sessions": 110,
  "created_students": 5,
  "questions_created": 50,
  "errors_count": 2,
  "errors_file": "/media/offline_uploads/errors_20251114_1234.csv"
}

Failure cases (400)
- Missing file / invalid headers — return JSON describing missing headers
- All rows invalid — 400 with error details

Partial success (200 or 201) — include errors_count > 0 and link to error CSV

Security
- Only institution admins for that `institution` may call this endpoint. Validate that provided `test_id` belongs to the same institution.

---

## 6. Frontend changes (institution admin dashboard)

Files to update (high level)
- Add new UI in institution admin dashboard (component under `client/src/pages/institution-admin/` or existing admin UI):
  - Button: "Upload Offline Results"
  - Modal or dedicated page with:
    - Select test (dropdown of existing institution tests) OR provide new test name field
    - Upload file input (accept `.xlsx`)
    - Download template link (generate client-side CSV/XLSX with header row or point to documentation)
    - Progress indicator while upload is in progress
    - Link to download error report after processing

UX notes
- Validate file extension client-side before upload
- Show a preview of first 5 rows (optional) for confirmation
- Show final summary (created sessions, errors) returned from API

Implementation details
- Use existing auth token (institution admin access) to call new endpoint
- POST multipart form with `file`, `test_id` or `test_name`, `exam_type`
- For error file link returned, download and show as CSV to admin

---

## 7. Validation & Test plan

Unit tests (backend)
- `test_offline_upload_happy_path`: upload small Excel, expect PlatformTest created, students and sessions created, answers created
- `test_offline_upload_partial_invalid_rows`: one invalid row in file; expect partial success + errors_count=1
- `test_student_matching_by_phone`: rows with same phone map to same student
- `test_question_duplicate_handling`: repeated identical question rows do not create duplicate question model entries

Integration tests
- Upload a multi-student file and ensure insights tasks are enqueued (mock Celery)

Manual acceptance
- Admin uploads file with 2 students and 5 questions; check student dashboards and institution test analytics show results

---

## 8. Edge cases & decisions

- Mixed test names in rows: disallow — require all rows belong to the same `test_name` (or pass `test_id` param). If mixed, reject rows and include error reasons.
- Large files: consider asynchronous background processing for very large files (out of scope for v1). For now process synchronously with limits and use progress spinner in UI.
- Duplicate student entries in the same file: group rows by phone/email+name to create a single session per student.
- Time zone handling: assume ISO datetimes; if absent treat as server timezone. Document this behavior.

---

## 9. Files to add / patch

- `backend/neet_app/services/offline_results_upload.py` (new)
- `backend/neet_app/views/institution_admin_views.py` (add `upload_offline_results` handler)
- `backend/neet_app/urls.py` (add route)
- `client/src/pages/institution-admin/OfflineUpload.tsx` (new front-end page/component) — optional path depending on project
- `backend/tests/test_offline_upload.py` (unit tests)

---

## 10. Rollout and migration notes

- No DB migrations required — we'll use existing models and create rows normally.
- Run tests and try with sample file on staging. Ensure LLM/insights tasks are not overwhelmed (monitor Celery worker queue).

---

## 11. Next steps (suggested prioritized checklist)

1. Add `OFFLINE_TEST_UPLOAD_PLAN.md` (this document) — done
2. Implement `services/offline_results_upload.py` and a minimal `upload_offline_results` view that calls it
3. Add a basic frontend upload page (simple form to upload) and link in admin dashboard
4. Add tests (unit + integration) and run `pytest` in backend
5. QA on staging with a sample Excel (5 students x 10 questions)
6. Monitor Celery tasks as uploads hit production

---

If you'd like, I can now implement the backend service + view and a small frontend upload form. Tell me to "Proceed implement backend" and I'll start coding the service and wire the endpoint in the repo.
