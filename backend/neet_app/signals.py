"""
Django signals for automatic data processing in NEET app models
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import StudentProfile, TestSession


@receiver(pre_save, sender=StudentProfile)
def generate_student_credentials(sender, instance, **kwargs):
    """
    Auto-generate student_id before saving StudentProfile
    Password generation is now handled by user input, not automatic generation
    """
    if not instance.student_id and instance.full_name and instance.date_of_birth:
        # Only generate student_id, password is now user-defined
        instance.generate_credentials()


@receiver(post_save, sender=TestSession)
def classify_test_session_topics(sender, instance, created, **kwargs):
    """
    Classify selected topics by subjects after TestSession is saved
    """
    if created or not all([
        instance.physics_topics,
        instance.chemistry_topics,
        instance.botany_topics,
        instance.zoology_topics
    ]):
        instance.update_subject_classification()
        # Use update() to avoid triggering signals again
        TestSession.objects.filter(id=instance.id).update(
            physics_topics=instance.physics_topics,
            chemistry_topics=instance.chemistry_topics,
            botany_topics=instance.botany_topics,
            zoology_topics=instance.zoology_topics
        )


@receiver(post_save, sender=TestSession)
def update_student_statistics(sender, instance, **kwargs):
    """
    Update student statistics when a test session is completed
    """
    if instance.is_completed:
        try:
            student_profile = StudentProfile.objects.get(student_id=instance.student_id)
            # Update last login timestamp when a test is completed
            from django.utils import timezone
            StudentProfile.objects.filter(student_id=instance.student_id).update(
                last_login=timezone.now()
            )
        except StudentProfile.DoesNotExist:
            pass  # Student profile doesn't exist, skip statistics update
