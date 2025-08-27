# Use Python 3.11 slim image
FROM python:3.11-slim-bookworm

# Install system dependencies required for WeasyPrint and other packages
RUN apt-get update && apt-get install -y \
    # WeasyPrint dependencies
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    # Font dependencies
    fontconfig \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    fonts-liberation \
    # WeasyPrint text rendering
    libharfbuzz0b \
    libfribidi0 \
    libpangoft2-1.0-0 \
    # Build dependencies
    gcc \
    g++ \
    python3-dev \
    build-essential \
    # PostgreSQL client
    postgresql-client \
    # Additional utilities
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Update font cache
RUN fc-cache -fv

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# WeasyPrint specific environment variables
ENV FONTCONFIG_PATH=/etc/fonts

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads/employees
RUN mkdir -p temp/pdf

# Set proper permissions
RUN chmod -R 755 /app

# Expose port
EXPOSE 5000

# Make start script executable
RUN chmod +x start.sh

# Run the application
CMD ["./start.sh"]