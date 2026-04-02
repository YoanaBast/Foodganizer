# Foodganizer - AWS EC2 Deployment Documentation

| | |
|---|---|
| **Server** | Ubuntu 22.04 LTS, t3.micro |
| **IP** | 52.45.4.205 |
| **Domain** | foodganizer.com |
| **Stack** | Django + Gunicorn + Nginx + Docker + Supabase |
| **Date** | April 2, 2026 |

---

## Overview
Deployed a Django-based meal planning and nutrition tracking web application to AWS EC2 using Docker, with Nginx as a reverse proxy, Gunicorn as the WSGI server, and Supabase as the hosted PostgreSQL database. HTTPS was configured using Let's Encrypt via Certbot.

---

## Initial Server Setup
```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install docker.io docker-compose-plugin -y
    sudo apt install docker.io -y
    sudo apt install docker.io -y
    sudo apt install docker-compose -y # I was getting some kernel update pop-up here, rebooted after the update
    sudo reboot
```

---

## Docker Setup (after reboot)
```bash
    sudo apt install docker.io -y
    sudo apt install docker-compose -y
    sudo usermod -aG docker ubuntu    # Add ubuntu user to docker group so we don't need sudo for docker commands
    exit
    docker --version
```

---

## Project Setup
```bash
   git clone https://github.com/YoanaBast/healthy_meals.git
   cd healthy_meals
   nano .env     # Created .env file manually (not on GitHub for security)
   cat .env # checking if I saved anything 
```

---

## Nginx & Docker Compose Configuration
```bash
   vim docker-compose.yml # Fixed nginx port from "81:80" to "80:80"
   cat nginx/nginx.conf # I use a lot of cats because I keep wanting to check things
   cat docker-compose.yml 
   vim nginx/nginx.conf  # Changed server_name from localhost to foodganizer.com www.foodganizer.com
   docker-compose build   # Built the Django app Docker image
   cat docker-compose.yml
   vim docker-compose.yml # Fixed identation error i made
   cat docker-compose.yml
   docker-compose build
   docker-compose up -d
   docker-compose ps # check run
   docker-compose logs web # check for errors -> none in console but there is 1 on the sit
```

---

## Error 1 — DisallowedHost

**Symptom:** Site was reachable but showed:
```
DisallowedHost at /
Invalid HTTP_HOST header: 'foodganizer.com'.
You may need to add 'foodganizer.com' to ALLOWED_HOSTS.
```

**Fix:**
```bash
   vim .env # changed ENVIRONMENT, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
   cat .env
   vim .env
   docker-compose down && docker-compose up -d
   docker-compose ps
   docker-compose logs nginx
```

---

## Error 2 — 301 Redirect Loop

**Symptom:** After restarting, nginx logs showed:
```
GET / HTTP/1.1" 301 
```
Django was saying "you're on HTTP, go to HTTPS" but HTTPS didn't exist yet, causing an infinite redirect loop.

**Fix:**
```bash
   cat .env
   vim .env # I set debug true/false multiple times around here to get around the 301
   docker-compose down && docker-compose up -d #error resolved but I'm on HTTP 

```

---

## HTTPS Setup with Certbot
```bash
   docker-compose stop nginx
   sudo apt install certbot -y
   sudo certbot certonly --standalone -d foodganizer.com -d www.foodganizer.com
   #ran Certbot on port 80 (that's why I stopped nginx first), got verified as owner of my domain, gave me certificate and key	
   vim nginx/nginx.conf # told nginx where to find the certificates
   cat nginx/nginx.conf
   vim docker-compose.yml # expose port 443 and mount the certificates
   cat docker-compose.yml
   vim .env # Changed ENVIRONMENT=DOCKER to ENVIRONMENT=PROD
   vim docker-compose.yml
   cat docker-compose.yml
   vim .env # I don't think I changed anything here, I was exploring vim 
   docker-compose down && docker-compose up -d     # Final restart - site now live at https://foodganizer.com
   history > deployment_history.txt # saving the console history, removed sensitive data (although it seems to only save my commands) and adding comments 
```

---

