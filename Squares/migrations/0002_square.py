# Generated by Django 5.0.2 on 2024-02-08 04:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Squares', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Square',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('row', models.IntegerField()),
                ('column', models.IntegerField()),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='Squares.participant')),
            ],
            options={
                'unique_together': {('row', 'column')},
            },
        ),
    ]
