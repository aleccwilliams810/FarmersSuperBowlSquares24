# Generated by Django 5.0.2 on 2024-02-08 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Squares', '0003_participant_purchase_complete_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='participant',
            name='squares_pending',
            field=models.IntegerField(default=0),
        ),
    ]
