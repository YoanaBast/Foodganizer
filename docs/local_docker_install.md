## 🐳 Docker Installation

**Requirements:**
- Docker Desktop (running)
- Local PostgreSQL Database (if using local DB, can be in Docker too)

### 1. Clone the repo
```bash
git clone https://github.com/YoanaBast/healthy_meals.git
cd healthy_meals
```

### 2. Setup

#### 2.1 Fast Docker Setup
Run the command below to complete the Docker setup:
```bash
python fast_docker_setup.py
```
- This will do the following:
  - create `.env` if you don't have one (update it with your credentials before continuing)
  - build and start all Docker containers (web, nginx, redis, celery, celery-beat)
  - run `makemigrations` and `migrate` inside the container
  - run `collectstatic` inside the container
  - optionally create a superuser
  - restart nginx to ensure it connects to the web container

#### 2.2 Manual Docker Setup
If you don't want to use the fast setup, follow the steps below:

- Create a `.env` file in the root directory and fill in your credentials (see [this](docs/documented_files/creds_docker_example.txt))
- Make sure `ENVIRONMENT=DOCKER` is set in your `.env`
```bash
docker-compose up --build -d
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
docker-compose restart nginx
```

- Optionally create a superuser:
```bash
docker-compose exec web python manage.py createsuperuser
```

### 3. Access the app
- App runs at: **http://localhost**
- Stop all containers with:
```bash
docker-compose down
```

### 4. Dummy Data
- You can populate the DB with some dummy data by running:
```bash
docker-compose exec web python manage.py populate_dummy_data
```