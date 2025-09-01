from django.db import models


class DatabaseQuestion(models.Model):
    """
    External/source table containing all questions data. Lives in another DB.
    This model is unmanaged so Django won't create/migrate it in the default DB.
    """
    id = models.AutoField(primary_key=True)
    question_number = models.IntegerField(null=True, blank=True)
    question_text = models.TextField(null=True, blank=True)
    question_type = models.TextField(null=True, blank=True)
    option_1 = models.TextField(null=True, blank=True)
    option_2 = models.TextField(null=True, blank=True)
    option_3 = models.TextField(null=True, blank=True)
    option_4 = models.TextField(null=True, blank=True)
    subject = models.TextField(null=True, blank=True)
    chapter = models.TextField(null=True, blank=True)
    topic = models.TextField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    source = models.TextField(null=True, blank=True)
    source_page = models.IntegerField(null=True, blank=True)
    correct_answer = models.TextField(null=True, blank=True)
    explanation = models.TextField(null=True, blank=True)
    difficulty = models.TextField(null=True, blank=True)
    explanation_image = models.TextField(null=True, blank=True)
    option_1_image = models.TextField(null=True, blank=True)
    option_2_image = models.TextField(null=True, blank=True)
    option_3_image = models.TextField(null=True, blank=True)
    option_4_image = models.TextField(null=True, blank=True)
    question_image = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'database_question'
        managed = False  # Important: do not manage/migrate this table in default DB
        app_label = 'external_db'  # Explicit app label since this is not in INSTALLED_APPS
        verbose_name = 'Database Question'
        verbose_name_plural = 'Database Questions'

    def __str__(self):
        return f"Q{self.id}: {self.question_text[:50] if self.question_text else 'No text'}..."
