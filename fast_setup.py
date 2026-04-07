import subprocess
from pathlib import Path
# from django.core.management.utils import get_random_secret_key

# Config
env_path = Path(".env")
env_content = f"""
ENVIRONMENT=DEV # DEV, PROD, DOCKER

DJANGO_SECRET_KEY=django-insecure-local-dev-key-1234567890
ALLOWED_HOSTS=localhost,127.0.0.1,web
CSRF_TRUSTED_ORIGINS=http://localhost:81,http://127.0.0.1:81

#LOCAL DB
LOCAL_DB_HOST=localhost
LOCAL_DB_PORT=5432
LOCAL_POSTGRES_DB=xxxxxxxxx
LOCAL_POSTGRES_USER=xxxxxxxx
LOCAL_POSTGRES_PASSWORD=xxxxxxxxxxx
LOCAL_DB_SSLMODE=disable

# CLOUD DB LIKE SUPABASE
POSTGRES_DB=postgres
POSTGRES_USER=postgres.xxxxxxxxxxxxxxxxx
POSTGRES_PASSWORD=xxxxxxxx
DB_HOST=aws-xxxxxxxxxxxxxxxxxxxxxxx
DB_PORT=5432
DB_SSLMODE=require  #require for cloud, disable for local

#SENTRY
SENTRY_DSN=https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Email via Brevo SMTP
BREVO_SMTP_HOST=smtp-xxxxxxxxxxxxx
BREVO_SMTP_PORT = 587
BREVO_EMAIL_USE_TLS = True
BREVO_SMTP_USER=xxxxxxxxxxxxxxx-brevo.com
BREVO_SMTP_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BREVO_DEFAULT_FROM_EMAIL=xxxxxxxxxxxxxxxx <xxxxxx@xxxxxx.com>

#CLIUNDINARY - MEDIA
CLOUDINARY_CLOUD_NAME=xxxxxxxxx
CLOUDINARY_API_KEY=xxxxx
CLOUDINARY_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxx

#CELERY
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

"""

affirmatives = {
    "yes", "y", "yea", "yeah", "ye", "yep", "sure", "ok", "okay", "aye", "affirmative", "true", "1"
}

minimal_setup = [
    "pip install -r requirements.txt",
    "python manage.py makemigrations",
    "python manage.py migrate",
    "python manage.py collectstatic --noinput"
]


def yes(prompt: str) -> bool:
    return input(prompt).strip().lower() in {x.lower() for x in affirmatives}


def run_commands(cmd_list):
    for cmd in cmd_list:
        print(f"\n\033[1;32mRunning:\033[0m \033[38;5;214m{cmd}\033[0m")
        subprocess.run(cmd, shell=True, check=True)

# .env setup
if not env_path.exists():
    if yes("No .env file found. Create one now? (y/n): "):
        env_path.write_text(env_content)
        print("\033[1;34m.env created. Please update LOCAL_POSTGRES_DB, LOCAL_POSTGRES_USER, LOCAL_POSTGRES_PASSWORD before continuing.\033[0m")
        input("You may need to reload from disk to see it. Press Enter when done...")
    else:
        print("\033[1;33mNo .env file. Make sure it exists before running setup. It should look like:\033[0m")
        print(env_content)
        exit()

if yes("\033[1;35mReady for minimal setup? (y/n): \033[0m"):
    run_commands(minimal_setup)
    print("\033[1;33mYou can now use \033[0m\033[1;36mpython manage.py runserver\033[0m\033[1;33m to view the app.\033[0m")


else:
    print("\033[1;32mRun\033[0m \033[1;34mpython fast_setup.py\033[0m \033[1;32magain when ready.\033[0m")
