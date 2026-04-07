## 🛠 Installation

**Requirements:**
- Python 3.11+  
- Local PostgreSQL Database


### 1. Clone the repo

```bash
git clone https://github.com/YoanaBast/healthy_meals.git
cd healthy_meals
```
- healthy_meals is the name of my root, if you set another name for yours, please use that name - cd your_root
- if you already have a root with venv and clone in that venv, you may get the healthy_meals folder nested in your root. Then you need to cd healthy_meals

  
### 2. Virtual Environment
**Check if a venv already exists:**
- If you created a project in your IDE, it may have already created a virtual environment.
- Look in the project folder for a `venv/` (or similarly named) directory.  
- You can also check the IDE’s Python interpreter settings to see if a venv is active.

**If no venv exists, create one:**
```bash
python -m venv venv
source venv/bin/activate   # on Linux/Mac
venv\Scripts\activate      # on Windows
```

- all following commands are to be run in the root where manage.py is (healthy_meals or your_root)
  

### 3. Setup

#### 3.1 Fast Setup
You can run the command below to complete the setup:
```bash
python fast_setup.py
```
- This will do the following: 
  - create .env if you don't have one (you need to put your creds like [this](docs/documented_files/creds_example.txt)
  - install requirements
  - makemigrations and migrate
  - collectstatic

#### 3.2 Manual Setup
If you don't want to use the fast setup, you can follow the steps below
  - create a .env file in the root directory (healthy_meals or the name you set locally)
  - put [this](docs/documented_files/creds_example.txt) inside and update it with your credentials
  - run this to install requirements:
```bash
    pip install -r requirements.txt
```
  - run this to set up your DB:
```bash
    python manage.py makemigrations
    python manage.py migrate
```
  - run this to set up the css:
```bash
    python manage.py collectstatic --noinput
```

### 4. Server
- You can now run the server to see the app:
```bash
    python manage.py runserver
```
- Stop the server with CRL + C in the same console
- If you are reloading collectstatic for some reason, you need to re-run the surver (stop and run again)

### 5. Dummy Data
- You can populate the DB with some dummy data by running this:
```bash
    python manage.py populate_dummy_data
```
