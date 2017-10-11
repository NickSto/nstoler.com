# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-10-10 07:06
from __future__ import unicode_literals

from django.db import migrations, models
import utils.misc


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TempData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.IntegerField(blank=True, null=True)),
                ('type', models.CharField(max_length=127)),
                ('int', models.IntegerField(blank=True, null=True)),
                ('float', models.FloatField(blank=True, null=True)),
                ('data', models.TextField()),
            ],
            bases=(utils.misc.ModelMixin, models.Model),
        ),
    ]