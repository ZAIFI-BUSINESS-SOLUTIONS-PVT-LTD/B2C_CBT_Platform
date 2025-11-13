from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from neet_app.models import Question
import json

# If you'd like the old-style inline script behavior, set these constants and run
# the management command with --use-inline. This keeps execution safe (nothing
# runs at import time) but lets you edit the file to provide the test name and
# answers directly.
# Example:
# INLINE_TEST_NAME = 'demo test'
# INLINE_NEW_ANSWERS = ['A','B','C', ...]
INLINE_TEST_NAME = 'demo Test'
INLINE_NEW_ANSWERS = [
    'A','A','A','A','A','A','A','A','A','A',
    'B','B','B','B','B','B','B','B','B',
    'C','12','13','14','15','C','C','C','C','C','C','C','C',
    'D','D','D','D','D','D','D','D','D','D','D','D','D',
    '45.6','46.6','47.6','48.6','49.6',
    'A','A','B','B','B','B','B','B','B','B','B','B',
    'C','C','C','C','C','C','C','C',
    '1.45','2.45','3.45','4.45','5.45'
]


class Command(BaseCommand):
    help = (
        "Bulk update Question.correct_answer for questions matching an institution_test_name.\n"
        "Provide answers via --answers-file (JSON array) or --answers (JSON array or comma-separated list)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-name",
            dest="test_name",
            required=False,
            help="institution_test_name to filter questions (required unless --use-inline is provided)",
        )
        parser.add_argument(
            "--answers-file",
            dest="answers_file",
            help="Path to a JSON file containing a list of answers (array)",
        )
        parser.add_argument(
            "--answers",
            dest="answers",
            help=(
                "Answers provided inline as a JSON array string or as a comma-separated list. "
                "Example: --answers='[""A"", ""B"", ""C""]' or --answers=A,B,C"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show planned updates (first 10) and do not persist changes",
        )
        parser.add_argument(
            "--show-all",
            action="store_true",
            dest="show_all",
            help="When doing a dry-run, show all planned updates instead of just the first 10",
        )
        parser.add_argument(
            "--chunk-size",
            dest="chunk_size",
            type=int,
            default=0,
            help=(
                "When applying changes, update in chunks of this size using bulk_update. "
                "0 means update all at once (default). Use this if your DB has limits."
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            dest="apply",
            help="Persist the changes (must be passed to actually update the DB)",
        )
        parser.add_argument(
            "--use-inline",
            action="store_true",
            dest="use_inline",
            help=(
                "Use INLINE_TEST_NAME and INLINE_NEW_ANSWERS constants defined in this file. "
                "Edit the file and set those values, then run with --use-inline."
            ),
        )

    def handle(self, *args, **options):
        test_name = options.get("test_name")
        answers_file = options.get("answers_file")
        answers_arg = options.get("answers")
        dry_run = options.get("dry_run")
        do_apply = options.get("apply")

        use_inline = options.get("use_inline")

        # If the user didn't pass --test-name or --use-inline but the inline
        # constants are set in the file, auto-enable inline mode so the
        # command behaves like the old script (convenient for manual runs).
        if not use_inline and not test_name and INLINE_TEST_NAME is not None:
            self.stdout.write("Using INLINE_TEST_NAME/INLINE_NEW_ANSWERS from command file")
            use_inline = True

        # If requested, use the inline constants defined at the top of this file.
        if use_inline:
            if INLINE_TEST_NAME is None or INLINE_NEW_ANSWERS is None:
                raise CommandError(
                    "--use-inline specified but INLINE_TEST_NAME or INLINE_NEW_ANSWERS is not set in the file."
                )
            test_name = INLINE_TEST_NAME
            new_answers = INLINE_NEW_ANSWERS

            qs = Question.objects.filter(institution_test_name=test_name).order_by("id")
            q_count = qs.count()
        else:
            qs = Question.objects.filter(institution_test_name=test_name).order_by("id")
            q_count = qs.count()

        # If not using inline, ensure the user supplied --test-name
        if not use_inline and not test_name:
            raise CommandError("--test-name is required unless you pass --use-inline")

        if not use_inline:
            if answers_file:
                try:
                    with open(answers_file, "r", encoding="utf-8") as fh:
                        new_answers = json.load(fh)
                except Exception as exc:  # pragma: no cover - CLI helper
                    raise CommandError(f"Failed to read answers file: {exc}")
                if not isinstance(new_answers, list):
                    raise CommandError("Answers file must contain a JSON array (list)")
            elif answers_arg:
                # Try JSON first, then fallback to comma-separated
                try:
                    parsed = json.loads(answers_arg)
                    if not isinstance(parsed, list):
                        raise ValueError("not a list")
                    new_answers = parsed
                except Exception:
                    # fallback to comma-separated list
                    new_answers = [x.strip() for x in answers_arg.split(",") if x.strip()]
            else:
                raise CommandError("Provide --answers-file or --answers")

        if q_count != len(new_answers):
            raise CommandError(
                f"Question count ({q_count}) != answers provided ({len(new_answers)}) - aborting. Please check."
            )

        # Build list of questions that actually need updating (current != new)
        questions = list(qs)  # materialize
        pairs = list(zip(questions, new_answers))
        to_update = []
        for q, ans in pairs:
            cur = (q.correct_answer or "")
            # Normalize to strings for comparison
            cur_s = str(cur).strip()
            new_s = str(ans).strip()
            if cur_s != new_s:
                q._new_correct_answer = new_s  # attach temporary attribute
                to_update.append(q)

        show_all = options.get("show_all")
        self.stdout.write(
            f"Planned updates: total_questions={len(questions)} will_change={len(to_update)}" +
            (" (showing all)" if show_all else " (showing first 10)")
        )
        iterator = to_update if show_all else to_update[:10]
        for q in iterator:
            self.stdout.write(f"  Will update question id={q.id} from {q.correct_answer!r} -> {q._new_correct_answer!r}")

        if not to_update:
            self.stdout.write(self.style.SUCCESS("No changes required; all answers already match the provided values."))
            return

        if not do_apply:
            self.stdout.write(self.style.WARNING("Dry-run only. Re-run with --apply to persist changes."))
            return

        # Persist within a transaction for safety. Backup old values first.
        import os, datetime

        backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        safe_name = test_name.replace(" ", "_")[:50]
        backup_path = os.path.join(backup_dir, f"correct_answers_backup_{safe_name}_{timestamp}.json")

        backup_data = [{"id": q.id, "old": q.correct_answer} for q in to_update]
        with open(backup_path, "w", encoding="utf-8") as bf:
            json.dump(backup_data, bf, ensure_ascii=False, indent=2)

        chunk_size = options.get("chunk_size") or 0
        updated_count = 0
        with transaction.atomic():
            if chunk_size and chunk_size > 0:
                for i in range(0, len(to_update), chunk_size):
                    batch = to_update[i : i + chunk_size]
                    for q in batch:
                        q.correct_answer = q._new_correct_answer
                    Question.objects.bulk_update(batch, ["correct_answer"])
                    updated_count += len(batch)
            else:
                for q in to_update:
                    q.correct_answer = q._new_correct_answer
                Question.objects.bulk_update(to_update, ["correct_answer"])
                updated_count = len(to_update)

        self.stdout.write(self.style.SUCCESS(f"Updated {updated_count} questions for test '{test_name}'."))
        self.stdout.write(self.style.SUCCESS(f"Backup of previous values written to: {backup_path}"))

