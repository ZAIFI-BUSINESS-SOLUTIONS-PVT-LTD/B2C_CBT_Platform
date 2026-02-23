import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','neet_backend.settings')
django.setup()
from neet_app.models import Institution, InstitutionAdmin, PlatformTest, Question, StudentProfile

print('Institution.count=', Institution.objects.count())
print('InstitutionAdmin.count=', InstitutionAdmin.objects.count())
print('PlatformTest (institution-linked) count=', PlatformTest.objects.filter(institution__isnull=False).count())
print('Question (institution-linked) count=', Question.objects.filter(institution__isnull=False).count())
print('StudentProfile (institution-linked) count=', StudentProfile.objects.filter(institution__isnull=False).count())

print('\nSample Institutions (first 10):')
for i in Institution.objects.all()[:10]:
    print(i.id, i.name, i.code)

print('\nSample InstitutionAdmins (first 10):')
for a in InstitutionAdmin.objects.select_related('institution').all()[:10]:
    print(a.id, a.username, a.institution_id, getattr(a.institution,'name',None), 'has_hash=', bool(a.password_hash))
