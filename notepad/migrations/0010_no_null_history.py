# -*- coding: utf-8 -*-
# Generated by Django 1.11.27 on 2020-01-25 07:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notepad', '0009_note_history'),
    ]

    operations = [
        migrations.AlterField(
            model_name='note',
            name='history',
            field=models.IntegerField(default=-1),
            preserve_default=False,
        ),
    ]