FROM python:3.9.6-alpine

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies and required packages to compile some of them
COPY requirements.txt /app
RUN  \
    apk update && \
    apk upgrade && \
    apk add bash postgresql-libs libressl-dev musl-dev libffi-dev cargo && \
    apk add --virtual .build-deps gcc postgresql-dev && \
    pip3 install --upgrade pip -r requirements.txt && \
    apk --purge del .build-deps

# Add the rest of the code
COPY . /app

# Make port 8000 available for the app
EXPOSE 8000

# Be sure to use 0.0.0.0 for the host within the Docker container,
# otherwise the browser won't be able to find it
RUN ["chmod", "+x", "/app/scripts/entrypoint-dev.sh"]
ENTRYPOINT [ "/app/scripts/entrypoint-dev.sh" ]
