# Use official Python image as a base image
FROM python:3.12.7-alpine3.19

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port the service runs on
EXPOSE 5002

# Start the service
CMD ["python", "product_service.py"]

