# Generated by Django 3.2 on 2021-10-06 23:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0003_userprofile_permissions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='bio',
            field=models.TextField(blank=True, max_length=2048),
        ),
    ]
