# Generated by Django 5.1.3 on 2024-12-07 11:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("order", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClickTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "state",
                    models.IntegerField(
                        choices=[
                            (0, "Created"),
                            (1, "Initiating"),
                            (2, "Successfully"),
                        ],
                        default=0,
                    ),
                ),
                ("transaction_id", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="click_transactions",
                        to="order.order",
                    ),
                ),
            ],
        ),
    ]
