# Build Django Docker Image and push to ecr

1. Create a Dockerfile like:

```bash
FROM python:3.7

ENV PYTHONUNBUFFERED 1

COPY requirements.txt /code/
RUN pip install -r /code/requirements.txt

COPY . /code/

WORKDIR /code/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

1. Build image: `docker build -t mydjangoapp .`

## Push to Amazon ECR

1. Create ECR repository
2. Authenticate Docker with ECR
3. Tag image: `docker tag mydjangoapp:latest MY_ECR_URI/mydjangoapp:latest`
4. Push image: `docker push MY_ECR_URI/mydjangoapp:latest`
