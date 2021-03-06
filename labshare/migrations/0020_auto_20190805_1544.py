# Generated by Django 2.1.11 on 2019-08-05 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labshare', '0019_auto_20180829_1605'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='extension_reminder_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='reservation',
            name='usage_expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='usage_started',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
