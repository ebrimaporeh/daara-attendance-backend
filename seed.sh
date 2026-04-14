#!/bin/bash

# Seed.sh - Run seeders for An-Namuslimah

echo "🌱 Seeding An-Namuslimah Database"
echo "================================"

# Activate virtual environment
source venv/bin/activate

# Run migrations first
echo "📦 Running migrations..."
python manage.py makemigrations users attendance 
python manage.py migrate

# Run seeders
echo "🌱 Running seeders..."
# python seeders/simple_seeder.py

python seeders/run_seeders.py --seeder all --students 50 --admins 3 --months 3

echo "✅ Seeding complete!"
echo "================================"
echo "You can now run: python manage.py runserver"