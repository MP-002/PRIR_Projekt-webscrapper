# Użyj oficjalnego obrazu Python jako bazowego
FROM python:3.9-slim

# Ustaw katalog roboczy
WORKDIR /app

# Skopiuj plik requirements.txt
COPY requirements.txt .

# Zainstaluj zależności
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj resztę plików aplikacji
COPY . .

# Uruchom aplikację Flask
CMD ["python", "silnikv2.py"]
