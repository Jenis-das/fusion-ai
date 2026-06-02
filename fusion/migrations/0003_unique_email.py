from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("fusion", "0002_llmmodel_is_custom"),  # ← your app name + last migration
    ]

    operations = [
        migrations.RunSQL(
            sql="CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_uniq ON auth_user (email);",
            reverse_sql="DROP INDEX IF EXISTS auth_user_email_uniq;",
        ),
    ]