### Steps To Start The Servers

### To Start The Vue Server

```
Step 1:
cd frontend

Step 2:
npm run server
```

### To Start The Flask Server

```

Step 1:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

Step 2:
open the venv by: <venv_name>\Scripts\activate

Step 3:
cd backends

Step 4:
python app.py
```

### To Start Redis Server

```

Step 1:
redis-server
```

### To Start The Celery

```

Step 1:
cd backends

Step 2:
celery -A app.celery worker --loglevel=INFO
```

### To Start The Celery Beat

```

Step 1:
cd backends

Step 2:
celery -A app.celery beat --loglevel=INFO
```
