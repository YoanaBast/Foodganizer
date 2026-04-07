import subprocess
from pathlib import Path

env_path = Path(".env")

env_content = f"""
ENVIRONMENT=DOCKER # DEV, PROD, DOCKER

DJANGO_SECRET_KEY=django-insecure-local-dev-key-1234567890
ALLOWED_HOSTS=localhost,127.0.0.1,web
CSRF_TRUSTED_ORIGINS=http://localhost:81,http://127.0.0.1:81

#LOCAL DB
LOCAL_DB_HOST=host.docker.internal
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
DB_SSLMODE=require

#SENTRY
SENTRY_DSN=https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Email via Brevo SMTP
BREVO_SMTP_HOST=smtp-xxxxxxxxxxxxx
BREVO_SMTP_PORT = 587
BREVO_EMAIL_USE_TLS = True
BREVO_SMTP_USER=xxxxxxxxxxxxxxx-brevo.com
BREVO_SMTP_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BREVO_DEFAULT_FROM_EMAIL=xxxxxxxxxxxxxxxx <xxxxxx@xxxxxx.com>

#CLOUDINARY - MEDIA
CLOUDINARY_CLOUD_NAME=xxxxxxxxx
CLOUDINARY_API_KEY=xxxxx
CLOUDINARY_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxx

#CELERY
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
"""

docker_setup = [
    "docker-compose up --build -d",
    "docker-compose exec web python manage.py makemigrations",
    "docker-compose exec web python manage.py migrate",
    "docker-compose exec web python manage.py collectstatic --noinput",
]

affirmatives = {
    "yes", "y", "yea", "yeah", "ye", "yep", "sure", "ok", "okay", "aye", "affirmative", "true", "1"
}


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
        print("\033[1;34m.env created. Please update your DB credentials before continuing.\033[0m")
        input("Press Enter when done...")
    else:
        print("\033[1;33mNo .env file. Make sure it exists before running Docker setup.\033[0m")
        exit()

print("\033[1;34mThis will build and start your Docker containers, run migrations, and collect static files.\033[0m")

if yes("\033[1;35mReady for Docker setup? (y/n): \033[0m"):
    run_commands(docker_setup)

    if yes("\n\033[1;35mCreate a superuser? (y/n): \033[0m"):
        subprocess.run("docker-compose exec web python manage.py createsuperuser", shell=True)

    print("\n\033[1;34mRestarting nginx...\033[0m")
    subprocess.run("docker-compose restart nginx", shell=True)

    print("\n\033[1;33mDocker setup complete! App should be running at \033[0m\033[1;36mhttp://localhost\033[0m")
else:
    print("\033[1;32mRun\033[0m \033[1;34mpython fast_docker_setup.py\033[0m \033[1;32magain when ready.\033[0m")