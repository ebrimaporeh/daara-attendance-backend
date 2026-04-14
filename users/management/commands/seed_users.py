"""
Django management command to seed users
Usage: python manage.py seed_users --students=50 --admins=5
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
import sys
import os
from seeders.user_seeder  import UserSeeder


# Add seeders directory to path
sys.path.append(os.path.join(os.getcwd(), 'seeders'))

class Command(BaseCommand):
    help = 'Seed the database with initial user data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--students',
            type=int,
            default=50,
            help='Number of student users to create (default: 50)'
        )
        parser.add_argument(
            '--admins',
            type=int,
            default=5,
            help='Number of admin users to create (default: 5)'
        )
        parser.add_argument(
            '--skip-specific',
            action='store_true',
            help='Skip creating specific predefined users'
        )
        parser.add_argument(
            '--clear-first',
            action='store_true',
            help='Clear existing data before seeding'
        )
    
    def handle(self, *args, **options):
        
        if options['clear_first']:
            confirm = input("⚠️  This will delete all existing users. Are you sure? (y/N): ")
            if confirm.lower() == 'y':
                call_command('flush', interactive=False)
                self.stdout.write(self.style.SUCCESS('✅ Database cleared!'))
            else:
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Starting user seeder...\n'))
        
        UserSeeder.run_all(
            student_count=options['students'],
            admin_count=options['admins'],
            include_specific=not options['skip_specific']
        )
        
        self.stdout.write(self.style.SUCCESS('✅ User seeding completed successfully!'))