# Generated by Django 2.2.17 on 2020-12-09 10:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labshare', '0023_auto_20201203_1200'),
    ]

    operations = [
        migrations.AddField(
            model_name='gpu',
            name='utilization',
            field=models.CharField(default=0, max_length=100),
            preserve_default=False,
        ),
    ]
