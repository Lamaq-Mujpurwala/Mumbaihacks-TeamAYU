#!/bin/bash

echo "🚀 Starting Financial Guardian AI..."

# Seed the database with demo data
echo "🌱 Seeding database..."
python -m scripts.seed_database

# Start the FastAPI application
echo "🌐 Starting FastAPI server on port ${PORT:-7860}..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
