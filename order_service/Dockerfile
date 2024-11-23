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
EXPOSE 5003

CMD "python -m ensurepip --upgrade"

# Start the service
CMD ["python", "-u", "order_service.py"]

