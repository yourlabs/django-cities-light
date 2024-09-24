# Use the official Python image as the base image
FROM python:3.12-alpine

# Install MySQL and PostgreSQL client libraries
RUN apk update && apk add --no-cache \
    mariadb-connector-c-dev \
    postgresql-dev python3-dev musl-dev git

# Install Tox
RUN pip install tox

# Set the working directory
WORKDIR /app

# Copy the project files to the working directory
COPY . /app

RUN tox -e dev

# Set the entrypoint command
CMD ["tox"]
