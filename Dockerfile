FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything needed
COPY models/ ./models/
COPY api/app.py ./api/app.py

# Expose port
EXPOSE 5000

# Start Flask
CMD ["python3", "api/app.py"]
