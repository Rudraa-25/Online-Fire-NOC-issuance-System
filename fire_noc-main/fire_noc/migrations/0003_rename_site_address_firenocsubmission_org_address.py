# Generated by Django 5.1.7 on 2025-03-09 07:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fire_noc', '0002_firenocsubmission_email_firenocsubmission_name_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='firenocsubmission',
            old_name='site_address',
            new_name='org_address',
        ),
    ]
