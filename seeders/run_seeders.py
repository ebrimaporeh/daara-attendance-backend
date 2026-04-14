#!/usr/bin/env python
"""
Master script to run all seeders for the An-Namuslimah system
"""

import os
import sys
import django
import argparse

# Add the parent directory to path correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anamuslimah_project.settings')

# Setup Django
django.setup()

from user_seeder import UserSeeder
from attendance_seeder import AttendanceSeeder

def run_user_seeder(args):
    """Run user seeder with specified options"""
    print("\n" + "🎯 Running User Seeder")
    UserSeeder.run_all(
        student_count=args.students,
        admin_count=args.admins,
        include_specific=not args.skip_specific
    )

def run_attendance_seeder(args):
    """Run attendance seeder with specified options"""
    print("\n" + "🎯 Running Attendance Seeder")
    
    if args.clear_attendance:
        AttendanceSeeder.clear_attendance()
    
    if args.year and args.month:
        AttendanceSeeder.seed_specific_month(args.year, args.month)
    elif args.current_month:
        AttendanceSeeder.seed_current_month()
    else:
        AttendanceSeeder.seed_recent_months(months_back=args.months)

def run_all_seeders(args):
    """Run all seeders"""
    print("\n" + "🚀 Running All Seeders\n")
    run_user_seeder(args)
    run_attendance_seeder(args)

def main():
    parser = argparse.ArgumentParser(description='Run seeders for An-Namuslimah system')
    parser.add_argument('--seeder', type=str, choices=['users', 'attendance', 'all'], default='all',
                        help='Which seeder to run (users, attendance, or all)')
    
    # User seeder arguments
    parser.add_argument('--students', type=int, default=20,
                        help='Number of student users to create (default: 20)')
    parser.add_argument('--admins', type=int, default=3,
                        help='Number of admin users to create (default: 3)')
    parser.add_argument('--skip-specific', action='store_true',
                        help='Skip creating specific predefined users')
    
    # Attendance seeder arguments
    parser.add_argument('--months', type=int, default=3,
                        help='Number of months to seed attendance (default: 3)')
    parser.add_argument('--current-month', action='store_true',
                        help='Seed only current month')
    parser.add_argument('--year', type=int,
                        help='Specific year to seed attendance')
    parser.add_argument('--month', type=int,
                        help='Specific month to seed attendance (1-12)')
    parser.add_argument('--clear-attendance', action='store_true',
                        help='Clear existing attendance records before seeding')
    
    # Common arguments
    parser.add_argument('--clear-first', action='store_true',
                        help='Clear all existing data before seeding')
    
    args = parser.parse_args()
    
    if args.clear_first:
        confirm = input("⚠️  This will delete all existing data. Are you sure? (y/N): ")
        if confirm.lower() == 'y':
            from django.core.management import call_command
            call_command('flush', interactive=False)
            print("✅ Database cleared!")
        else:
            print("❌ Operation cancelled")
            sys.exit(0)
    
    if args.seeder == 'users':
        run_user_seeder(args)
    elif args.seeder == 'attendance':
        run_attendance_seeder(args)
    elif args.seeder == 'all':
        run_all_seeders(args)

if __name__ == "__main__":
    main()