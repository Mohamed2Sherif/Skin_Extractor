FROM python:3.9-slim

# 1. Install Wine and dependencies (minimal setup for CLI)
RUN dpkg --add-architecture i386 && \
    apt-get update && \
    apt-get install -y wine && \
    rm -rf /var/lib/apt/lists/*

# 2. Configure Wine for headless operation
ENV WINEDEBUG=-all
ENV WINEPREFIX=/wine
RUN wine wineboot --init && \
    wineserver --wait  # Ensure Wine initialization completes

# 3. Set up application
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy your files
COPY . .

# 5. Runtime configuration
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]