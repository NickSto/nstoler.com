# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-03-29 12:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('traffic', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cookie',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=4096)),
                ('value', models.CharField(max_length=4096)),
                ('direction', models.CharField(choices=[('set', 'set'), ('got', 'got')], max_length=3)),
                ('max_age', models.IntegerField(blank=True, null=True)),
                ('expires', models.DateTimeField(blank=True, null=True)),
                ('path', models.CharField(max_length=1023)),
                ('domain', models.CharField(max_length=127)),
                ('secure', models.NullBooleanField()),
            ],
        ),
        migrations.AddField(
            model_name='visit',
            name='cookies_got',
            field=models.ManyToManyField(related_name='visits_getting', to='traffic.Cookie'),
        ),
        migrations.AddField(
            model_name='visit',
            name='cookies_set',
            field=models.ManyToManyField(related_name='visits_setting', to='traffic.Cookie'),
        ),
    ]
