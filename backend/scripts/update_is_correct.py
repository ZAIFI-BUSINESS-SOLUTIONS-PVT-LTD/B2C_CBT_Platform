#!/usr/bin/env python3
"""Recalculate `test_answers.is_correct` for a set of questions.

This script boots Django (expects `neet_backend.settings`) and runs a Postgres
UPDATE that handles both MCQ (selected_answer) and NVT (text_answer) evaluation.

It supports dry-run (--dry-run) and an --apply flag. Provide IDs via --ids,
--ids-file (JSON array), or by editing the inline Q_IDS variable below.
"""

import argparse
import json
import os
import sys


# Optional: set Q_IDS here if you prefer editing the file instead of passing --ids
# Example:
# Q_IDS = [1144, 1145, 1146]
Q_IDS = [1134,1135,1136,1137,1138,1141,1142,1143,1140,1145,1147,1149,1184,1185,1164,1165,1175,1148,1152,1154,1139,1155,1159,1160,1150,1151,1153,1156,1157,1144,1146,1167,1169,1170,1174,1176,1178,1179,1180,1182,1183,1186,1187,1188,1189,1190,1191,1192,1171,1172,1173,1177,1181,1162,1166,1168,1193,1194,1195,1196,1197,1198,1199,1200,1201,1202,1203,1204,1205,1206,1207,1208,1161,1163,1158]


def main(argv=None):
  parser = argparse.ArgumentParser(
    description="Recalculate test_answers.is_correct for given question ids"
  )
  parser.add_argument("--ids", help="Comma-separated question ids (e.g. 1,2,3)")
  parser.add_argument("--ids-file", help="Path to JSON file with array of ids")
  parser.add_argument(
    "--tolerance",
    type=float,
    default=0.0001,
    help="Numeric tolerance for numeric NVT comparison",
  )
  parser.add_argument("--dry-run", action="store_true", help="Do not apply changes; show what would change")
  parser.add_argument("--apply", action="store_true", help="Apply the update (dangerous) — requires explicit flag")
  parser.add_argument("--sample", type=int, default=10, help="How many sample rows to print in dry-run")
  args = parser.parse_args(argv)

  # Load IDs (priority: --ids, --ids-file, inline Q_IDS)
  ids = []
  if args.ids:
    ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
  elif args.ids_file:
    with open(args.ids_file, "r", encoding="utf-8") as fh:
      ids = json.load(fh)
      if not isinstance(ids, list):
        raise SystemExit("ids-file must contain a JSON array of integers")
  elif Q_IDS:
    ids = list(Q_IDS)
    print("Using inline Q_IDS from script")
  else:
    raise SystemExit("Provide --ids, --ids-file or set Q_IDS in the script")

  if not ids:
    raise SystemExit("No question ids provided")

  # Bootstrap Django
  project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  if project_root not in sys.path:
    sys.path.insert(0, project_root)

  os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neet_backend.settings")
  try:
    import django

    django.setup()
  except Exception:
    print(
      "Failed to setup Django. Make sure this script is run from the project 'backend' folder and virtualenv is active."
    )
    print(f"Tried project_root={project_root}; sys.path[0]={sys.path[0]}")
    raise

  from django.db import connection, transaction

  # Build placeholders for IN clause
  placeholders = ",".join(["%s"] * len(ids))

  # CASE expression with a single %s placeholder for numeric tolerance
  case_sql = f"""
CASE
  WHEN ta.selected_answer IS NOT NULL AND trim(ta.selected_answer) <> '' THEN
    CASE WHEN upper(trim(ta.selected_answer)) = upper(trim(q.correct_answer::text)) THEN true ELSE false END

  WHEN ta.text_answer IS NOT NULL AND trim(ta.text_answer) <> '' THEN
    CASE
      WHEN q.correct_answer IS NULL THEN false
      WHEN trim(ta.text_answer) ~ '^-?[0-9]+(\.[0-9]+)?$' AND trim(q.correct_answer::text) ~ '^-?[0-9]+(\.[0-9]+)?$' THEN
        CASE WHEN abs( (ta.text_answer::numeric) - (q.correct_answer::numeric) ) <= %s THEN true ELSE false END
      WHEN lower(trim(ta.text_answer)) = lower(trim(q.correct_answer::text)) THEN true
      ELSE false
    END
  ELSE false
END
"""

  select_sql = f"""
SELECT ta.id, ta.question_id, ta.selected_answer, ta.text_answer, q.correct_answer,
  {case_sql} AS new_is_correct
FROM test_answers ta
JOIN questions q ON ta.question_id = q.id
WHERE ta.question_id IN ({placeholders})
  AND ({case_sql}) IS DISTINCT FROM ta.is_correct
LIMIT %s
"""

  count_sql = f"""
SELECT count(*) FROM (
  SELECT ta.id, {case_sql} AS new_is_correct, ta.is_correct
  FROM test_answers ta JOIN questions q ON ta.question_id = q.id
  WHERE ta.question_id IN ({placeholders})
) t WHERE t.new_is_correct IS DISTINCT FROM t.is_correct
"""

  update_sql = f"""
BEGIN;
UPDATE test_answers ta
SET is_correct = {case_sql}
FROM questions q
WHERE ta.question_id = q.id
  AND ta.question_id IN ({placeholders});
COMMIT;
"""

  params_for_case = [args.tolerance]

  # Execute dry-run count and sample
  with connection.cursor() as cur:
    # count_sql has one %s (tolerance) then len(ids) placeholders
    cur.execute(count_sql, params_for_case + ids)
    cnt = cur.fetchone()[0]
    print(f"Rows that would change: {cnt}")

    # select_sql param order: [tolerance] + ids + [tolerance] + [limit]
    cur.execute(select_sql, params_for_case + ids + params_for_case + [args.sample])
    rows = cur.fetchall()
    if rows:
      print(
        "Sample rows that would change (id, question_id, selected_answer, text_answer, correct_answer, new_is_correct):"
      )
      for r in rows:
        print(r)
    else:
      print("No sample rows — nothing to change.")

  if not args.apply:
    print("Dry-run complete. Rerun with --apply to persist changes.")
    return

  # Backup affected rows' current is_correct values
  backup_q = f"SELECT ta.id, ta.question_id, ta.is_correct FROM test_answers ta WHERE ta.question_id IN ({placeholders})"
  with connection.cursor() as cur:
    cur.execute(backup_q, ids)
    backup_rows = cur.fetchall()

  backup_path = os.path.join(
    os.path.dirname(__file__), f"is_correct_backup_{ids[0]}_{len(ids)}.json"
  )
  with open(backup_path, "w", encoding="utf-8") as bf:
    json.dump(
      [
        {"id": r[0], "question_id": r[1], "old_is_correct": r[2]}
        for r in backup_rows
      ],
      bf,
      default=str,
      indent=2,
    )
  print(f"Backup written to: {backup_path}")

  # Apply the update inside a transaction
  with transaction.atomic():
    with connection.cursor() as cur:
      # update_sql has one %s (tolerance) then len(ids) placeholders
      cur.execute(update_sql, params_for_case + ids)

  print("Update applied successfully.")


if __name__ == "__main__":
  main()
