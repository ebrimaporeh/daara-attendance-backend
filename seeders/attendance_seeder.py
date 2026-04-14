#!/usr/bin/env python
import os
import sys
import django
import random
from datetime import datetime, timedelta
from calendar import monthrange

# Add parent directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anamuslimah_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from attendance.models import AttendanceRecord

User = get_user_model()

class AttendanceSeeder:
    """Seeder for creating attendance records"""
    
    STATUSES = ['present', 'absent', 'excused', 'late', 'sick']
    # Weighted probabilities: 70% present, 10% absent, 5% excused, 10% late, 5% sick
    WEIGHTS = [0.70, 0.10, 0.05, 0.10, 0.05]
    
    # Notes for different statuses
    NOTES = {
        'present': [
            'Arrived on time',
            'Participated well in class',
            'Completed all assignments',
            'Good behavior',
            'Active in class discussions',
            'Memorized the assigned Surah',
            'Excellent recitation',
        ],
        'absent': [
            'Family emergency',
            'Sick leave',
            'Traveling with family',
            'No reason provided',
            'Parent called to inform absence',
            'Weather conditions',
            'Transportation issues',
        ],
        'excused': [
            'Medical appointment',
            'Family function',
            'Approved by admin',
            'Religious holiday',
            'Doctor\'s appointment',
            'Family wedding',
        ],
        'late': [
            'Arrived 15 minutes late',
            'Arrived 30 minutes late',
            'Traffic delay',
            'Transportation issues',
            'Woke up late',
        ],
        'sick': [
            'Fever',
            'Cold and cough',
            'Stomach ache',
            'Headache',
            'Doctor advised rest',
            'Recovering from illness',
        ]
    }
    
    @classmethod
    def get_random_note(cls, status):
        """Get a random note for the given status"""
        return random.choice(cls.NOTES.get(status, ['No notes']))
    
    @classmethod
    def should_mark_attendance(cls, date):
        """Determine if attendance should be marked for a given date"""
        # Skip weekends (Saturday=5, Sunday=6 in Monday=0...Sunday=6)
        # Assuming school days are Sunday to Thursday (adjust based on your region)
        # For Muslim countries, weekend is often Friday-Saturday
        # Let's assume school days: Monday-Friday (0-4)
        weekday = date.weekday()
        
        # Mark attendance only on weekdays (Monday to Friday)
        if weekday >= 5:  # Saturday or Sunday
            return False
        
        # Randomly skip some days (e.g., holidays, breaks)
        # 95% chance to mark attendance on school days
        return random.random() < 0.95
    
    @classmethod
    def generate_attendance_for_student(cls, student, year, month, admin_user):
        """Generate attendance records for a specific student in a given month"""
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, monthrange(year, month)[1]).date()
        
        created_records = []
        current_date = start_date
        
        while current_date <= end_date:
            # Check if we should mark attendance for this date
            if cls.should_mark_attendance(current_date):
                # Don't create duplicate records
                if not AttendanceRecord.objects.filter(student=student, date=current_date).exists():
                    # Select status based on weights
                    status = random.choices(cls.STATUSES, weights=cls.WEIGHTS)[0]
                    note = cls.get_random_note(status)
                    
                    # For students, higher chance of being present on Mondays
                    if current_date.weekday() == 0:  # Monday
                        if random.random() < 0.9:  # 90% present on Monday
                            status = 'present'
                            note = 'Started the week well'
                    
                    # For Fridays, higher chance of being present
                    if current_date.weekday() == 4:  # Friday
                        if random.random() < 0.85:  # 85% present on Friday
                            status = 'present'
                            note = 'End of week attendance'
                    
                    try:
                        record = AttendanceRecord.objects.create(
                            student=student,
                            marked_by=admin_user,
                            date=current_date,
                            status=status,
                            notes=note
                        )
                        created_records.append(record)
                    except Exception as e:
                        print(f"  ⚠ Failed to create record for {student.full_name} on {current_date}: {e}")
            
            current_date += timedelta(days=1)
        
        return created_records
    
    @classmethod
    def seed_attendance_for_month(cls, year, month, admin_phone='7123456'):
        """Seed attendance for all students for a specific month"""
        print(f"\n📅 Seeding attendance for {datetime(year, month, 1).strftime('%B %Y')}")
        print("-" * 50)
        
        # Get admin user
        try:
            admin_user = User.objects.get(phone=admin_phone, user_type='admin')
            print(f"✓ Using admin: {admin_user.full_name}")
        except User.DoesNotExist:
            # Try to get any admin
            admin_user = User.objects.filter(user_type='admin').first()
            if not admin_user:
                print("❌ No admin user found! Please run user seeder first.")
                return 0
            print(f"✓ Using admin: {admin_user.full_name}")
        
        # Get all students
        students = User.objects.filter(user_type='student')
        if not students.exists():
            print("❌ No students found! Please run user seeder first.")
            return 0
        
        print(f"✓ Found {students.count()} students")
        
        total_records = 0
        for student in students:
            records = cls.generate_attendance_for_student(student, year, month, admin_user)
            total_records += len(records)
            
            # Print progress every 10 students
            if students.filter(id__lte=student.id).count() % 10 == 0:
                print(f"  Processed {students.filter(id__lte=student.id).count()}/{students.count()} students...")
        
        print(f"✓ Created {total_records} attendance records for {datetime(year, month, 1).strftime('%B %Y')}")
        return total_records
    
    @classmethod
    def seed_recent_months(cls, months_back=3):
        """Seed attendance for the last X months"""
        print("\n" + "="*60)
        print("🎯 Starting Attendance Seeder")
        print("="*60)
        
        current_date = timezone.now().date()
        total_all_records = 0
        
        for i in range(months_back):
            # Calculate year and month for each month going back
            month = current_date.month - i
            year = current_date.year
            
            if month <= 0:
                month += 12
                year -= 1
            
            # Skip future months
            if year > current_date.year or (year == current_date.year and month > current_date.month):
                continue
            
            records = cls.seed_attendance_for_month(year, month)
            total_all_records += records
        
        print("\n" + "="*60)
        print("📊 Attendance Seeder Summary")
        print("="*60)
        print(f"✅ Total attendance records created: {total_all_records}")
        print(f"📚 Total students: {User.objects.filter(user_type='student').count()}")
        print(f"📅 Months seeded: {months_back}")
        print("="*60 + "\n")
        
        return total_all_records
    
    @classmethod
    def seed_current_month(cls):
        """Seed attendance for the current month only"""
        current_date = timezone.now().date()
        return cls.seed_attendance_for_month(current_date.year, current_date.month)
    
    @classmethod
    def seed_specific_month(cls, year, month):
        """Seed attendance for a specific month"""
        return cls.seed_attendance_for_month(year, month)
    
    @classmethod
    def clear_attendance(cls, confirm=True):
        """Clear all attendance records (use with caution)"""
        if confirm:
            response = input("⚠️  This will delete ALL attendance records. Are you sure? (yes/no): ")
            if response.lower() == 'yes':
                count = AttendanceRecord.objects.count()
                AttendanceRecord.objects.all().delete()
                print(f"✅ Deleted {count} attendance records")
                return count
            else:
                print("❌ Operation cancelled")
                return 0
        else:
            count = AttendanceRecord.objects.count()
            AttendanceRecord.objects.all().delete()
            print(f"✅ Deleted {count} attendance records")
            return count

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Seed attendance records')
    parser.add_argument('--months', type=int, default=3, 
                        help='Number of months to seed (default: 3)')
    parser.add_argument('--current', action='store_true',
                        help='Seed only current month')
    parser.add_argument('--year', type=int,
                        help='Specific year to seed')
    parser.add_argument('--month', type=int,
                        help='Specific month to seed (1-12)')
    parser.add_argument('--clear', action='store_true',
                        help='Clear existing attendance records before seeding')
    
    args = parser.parse_args()
    
    if args.clear:
        AttendanceSeeder.clear_attendance()
    
    if args.year and args.month:
        AttendanceSeeder.seed_specific_month(args.year, args.month)
    elif args.current:
        AttendanceSeeder.seed_current_month()
    else:
        AttendanceSeeder.seed_recent_months(months_back=args.months)