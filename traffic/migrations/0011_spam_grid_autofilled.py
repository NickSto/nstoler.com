# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-24 17:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('traffic', '0010_spam_one_to_one'),
    ]

    operations = [
        migrations.AddField(
            model_name='spam',
            name='grid_autofilled',
            field=models.NullBooleanField(),
        ),
    ]