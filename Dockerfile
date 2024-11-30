FROM --platform=linux/amd64 public.ecr.aws/docker/library/python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
COPY ./newrelic.ini /code/newrelic.ini

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

ENV NEW_RELIC_LICENSE_KEY=8d4faac46cb94e7311bd1116ed9251c6FFFFNRAL
ENV NEW_RELIC_APP_NAME=blacklist-api-fastapi
ENV NEW_RELIC_CONFIG_FILE=/code/newrelic.ini

COPY ./app /code/app

EXPOSE 8000

CMD ["newrelic-admin", "run-program", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]