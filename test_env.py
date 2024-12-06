from dotenv import load_dotenv
import os

# Laad de .env-variabelen
load_dotenv()

# Test de variabelen
print("DB_USER:", os.getenv("DB_USER"))
print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_NAME:", os.getenv("DB_NAME"))

