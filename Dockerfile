FROM ubuntu:latest

# 1. Update and install required packages (g++, libstdc++, Python, pip)
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-get update && \
    apt-get install -y \
    g++-11 \
    libstdc++6 \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates

# 2. Set working directory
WORKDIR /app

# 3. Copy and install Python dependencies
COPY requirements.txt .
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt
# 4. Copy the rest of the app
COPY . .

# 5. Expose port and start the server
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
