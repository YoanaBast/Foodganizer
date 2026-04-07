import subprocess
from pathlib import Path

env_path = Path(".env")

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


if not env_path.exists():
    print("\033[1;31mNo .env file found. Please create one before running Docker setup.\033[0m")
    print("\033[1;33mRun \033[0m\033[1;36mpython fast_setup.py\033[0m\033[1;33m first to generate one.\033[0m")
    exit()

print("\033[1;34mThis will build and start your Docker containers, run migrations, and collect static files.\033[0m")

if yes("\033[1;35mReady for Docker setup? (y/n): \033[0m"):
    run_commands(docker_setup)

    if yes("\n\033[1;35mCreate a superuser? (y/n): \033[0m"):
        subprocess.run("docker-compose exec web python manage.py createsuperuser", shell=True)

    print("\n\033[1;33mDocker setup complete! App should be running at \033[0m\033[1;36mhttp://localhost:81\033[0m")

else:
    print("\033[1;32mRun\033[0m \033[1;34mpython docker_setup.py\033[0m \033[1;32magain when ready.\033[0m")