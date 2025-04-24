FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    aria2 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy all files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Run the bot using the existing start.sh script
CMD ["bash", "start.sh"]
