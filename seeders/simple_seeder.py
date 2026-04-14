#!/usr/bin/env python
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anamuslimah_project.settings')

# Initialize Django
import django
django.setup()

from django.contrib.auth import get_user_model
from attendance.models import AttendanceRecord
from datetime import datetime, timedelta
import random

User = get_user_model()

def create_users():
    print("\n🌱 Creating test users...\n")
    
    # Create admin users
    admins = [
        ('7123456', 'admin123', 'Admin', 'User', 'System'),
        ('9234567', 'admin123', 'Fatima', 'Zahra', 'Ali'),
    ]
    
    admin_user = None
    for phone, password, first, last, father in admins:
        if not User.objects.filter(phone=phone).exists():
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=first,
                last_name=last,
                fathers_first_name=father,
                user_type='admin',
                is_staff=True,
                is_superuser=(phone == '7123456')
            )
            print(f"✓ Created admin: {first} {last} ({phone})")
            if phone == '7123456':
                admin_user = user
        else:
            user = User.objects.get(phone=phone)
            print(f"⚠ Admin {phone} already exists")
            if phone == '7123456':
                admin_user = user
    
    # Create student users
    students = [
        ('5345678', 'student123', 'Aisha', 'Siddiqua', 'Omar'),
        ('6456789', 'student123', 'Mariam', 'Bint Imran', 'Imran'),
        ('7567890', 'student123', 'Khadija', 'Al-Kubra', 'Khuwaylid'),
        ('2678901', 'student123', 'Zainab', 'Bint Ali', 'Ali'),
        ('9789012', 'student123', 'Sofia', 'Ahmed', 'Mohammed'),
        ('4890123', 'student123', 'Layla', 'Hassan', 'Yusuf'),
        ('5901234', 'student123', 'Noor', 'Ibrahim', 'Ismail'),
    ]
    
    student_objects = []
    for phone, password, first, last, father in students:
        if not User.objects.filter(phone=phone).exists():
            user = User.objects.create_user(
                phone=phone,
                password=password,
                first_name=first,
                last_name=last,
                fathers_first_name=father,
                user_type='student'
            )
            print(f"✓ Created student: {first} {last} ({phone})")
            student_objects.append(user)
        else:
            user = User.objects.get(phone=phone)
            print(f"⚠ Student {phone} already exists")
            student_objects.append(user)
    
    print(f"\n✅ Total users in database: {User.objects.count()}")
    return admin_user, student_objects

def create_attendance(admin_user, student_objects):
    print("\n🌱 Creating attendance records...\n")
    
    if not admin_user:
        print("❌ No admin user found, cannot create attendance records")
        return 0
    
    if not student_objects:
        print("❌ No students found, cannot create attendance records")
        return 0
    
    STATUSES = ['present', 'absent', 'excused', 'late', 'sick']
    WEIGHTS = [0.70, 0.10, 0.05, 0.10, 0.05]
    
    # Create attendance for last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)
    
    total_records = 0
    current_date = start_date
    
    while current_date <= end_date:
        # Skip weekends (Saturday and Sunday)
        if current_date.weekday() < 5:  # Monday to Friday
            for student in student_objects:
                # Check if record already exists
                if not AttendanceRecord.objects.filter(student=student, date=current_date).exists():
                    # Random status based on weights
                    status = random.choices(STATUSES, weights=WEIGHTS)[0]
                    
                    # Simple notes
                    notes_map = {
                        'present': 'Attended class',
                        'absent': 'Absent',
                        'excused': 'Excused absence',
                        'late': 'Arrived late',
                        'sick': 'Sick leave'
                    }
                    
                    AttendanceRecord.objects.create(
                        student=student,
                        marked_by=admin_user,
                        date=current_date,
                        status=status,
                        notes=notes_map[status]
                    )
                    total_records += 1
            
            # Print progress
            if total_records % 20 == 0 and total_records > 0:
                print(f"  Created {total_records} records so far...")
        
        current_date += timedelta(days=1)
    
    print(f"\n✅ Created {total_records} attendance records")
    return total_records

def main():
    print("\n" + "="*50)
    print("An-Namuslimah Database Seeder")
    print("="*50)
    
    admin_user, student_objects = create_users()
    total_attendance = create_attendance(admin_user, student_objects)
    
    print("\n" + "="*50)
    print("Seeder Summary")
    print("="*50)
    print(f"👥 Total users: {User.objects.count()}")
    print(f"  - Admins: {User.objects.filter(user_type='admin').count()}")
    print(f"  - Students: {User.objects.filter(user_type='student').count()}")
    print(f"📋 Attendance records: {total_attendance}")
    print("\n📝 Login credentials:")
    print("   Admin (superuser): phone: 7123456, password: admin123")
    print("   Admin: phone: 9234567, password: admin123")
    print("   Students: phones: 5345678, 6456789, etc., password: student123")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()