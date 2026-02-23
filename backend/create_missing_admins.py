"""
One-off script: create InstitutionAdmin records for orphaned institutions
(institutions that have no admin account).

Usage:
    python create_missing_admins.py

The script prints the generated username / temporary password for each new admin.
Change the passwords immediately after logging in.
"""

import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neet_backend.settings')
django.setup()

from neet_app.models import Institution, InstitutionAdmin
from django.db import transaction

# Find every institution that has no admin
orphaned = list(
    Institution.objects.exclude(
        id__in=InstitutionAdmin.objects.values('institution_id')
    ).order_by('id')
)

if not orphaned:
    print("✅  No orphaned institutions found — all institutions already have admins.")
    sys.exit(0)

print(f"Found {len(orphaned)} institution(s) without an admin account:\n")
for inst in orphaned:
    print(f"  ID={inst.id:<4} name={inst.name!r:<30} code={inst.code}")

print()
created = []

for inst in orphaned:
    # Default username: lowercase institution code, replace spaces
    base_username = inst.code.lower().replace(' ', '_')

    # Make username unique if it already exists
    username = base_username
    suffix = 1
    while InstitutionAdmin.objects.filter(username=username).exists():
        username = f"{base_username}_{suffix}"
        suffix += 1

    # Temporary password: Admin@<code>
    temp_password = f"Admin@{inst.code}"

    try:
        with transaction.atomic():
            admin = InstitutionAdmin(
                username=username,
                institution=inst,
                is_active=True
            )
            admin.set_password(temp_password)
            admin.save()
        created.append((inst, username, temp_password))
        print(f"✅  Created admin for '{inst.name}'  username={username!r}  password={temp_password!r}")
    except Exception as e:
        print(f"❌  Failed for '{inst.name}': {e}")

print()
if created:
    print("=" * 60)
    print("Admin accounts created (change passwords after first login):")
    print("=" * 60)
    for inst, uname, pwd in created:
        print(f"  Institution : {inst.name} (code: {inst.code})")
        print(f"  Username    : {uname}")
        print(f"  Password    : {pwd}")
        print()
