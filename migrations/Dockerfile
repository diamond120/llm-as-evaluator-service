# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container at /app
COPY ${WORKSPACE}/requirements.txt /app/requirements.txt

# Copy the current directory contents into the container at /usr/src/app
COPY ${WORKSPACE}/migrations/ /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run Alembic migrations
CMD ["alembic", "upgrade", "head"]