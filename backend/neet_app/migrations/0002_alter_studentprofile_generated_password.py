# Generated by Django 5.2.4 on 2025-07-28 18:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("neet_app", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentprofile",
            name="generated_password",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
