import os
import sys
import django
import random

# Add parent directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'anamuslimah_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

class UserSeeder:
    """Seeder for creating test users"""
    
    # Sample data for realistic names
    FIRST_NAMES = [
        'Aisha', 'Fatima', 'Mariam', 'Zainab', 'Khadija', 'Sofia', 'Layla', 
        'Noor', 'Sara', 'Hana', 'Amina', 'Ranya', 'Yasmin', 'Iman', 'Salma',
        'Nadia', 'Rania', 'Dina', 'Lina', 'Mona', 'Samira', 'Huda', 'Rima'
    ]
    
    LAST_NAMES = [
        'Ahmed', 'Hassan', 'Ali', 'Omar', 'Mahmoud', 'Ibrahim', 'Saleh', 
        'Rashid', 'Saeed', 'Mustafa', 'Khalid', 'Hamid', 'Nasser', 'Faris'
    ]
    
    FATHER_NAMES = [
        'Mohammed', 'Ahmed', 'Ali', 'Hassan', 'Omar', 'Mahmoud', 'Ibrahim',
        'Yusuf', 'Ismail', 'Bilal', 'Zakariya', 'Yahya', 'Adam', 'Nuh'
    ]
    
    VALID_PHONE_PREFIXES = ['2', '4', '5', '6', '7', '9']
    
    @classmethod
    def generate_phone_number(cls):
        """Generate a unique 7-digit phone number"""
        while True:
            prefix = random.choice(cls.VALID_PHONE_PREFIXES)
            rest = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            phone = prefix + rest
            
            # Check if phone number already exists
            if not User.objects.filter(phone=phone).exists():
                return phone
    
    @classmethod
    def generate_user_data(cls, user_type='student', custom_data=None):
        """Generate random user data"""
        if custom_data:
            return custom_data
        
        return {
            'first_name': random.choice(cls.FIRST_NAMES),
            'last_name': random.choice(cls.LAST_NAMES),
            'fathers_first_name': random.choice(cls.FATHER_NAMES),
            'phone': cls.generate_phone_number(),
            'user_type': user_type,
            'password': 'password123',  # Default password for all seeded users
        }
    
    @classmethod
    def seed_students(cls, count=20):
        """Seed student users"""
        created_users = []
        for i in range(count):
            user_data = cls.generate_user_data('student')
            try:
                # Check if user already exists
                if not User.objects.filter(phone=user_data['phone']).exists():
                    user = User.objects.create_user(**user_data)
                    created_users.append({
                        'id': user.id,
                        'name': user.full_name,
                        'phone': user.phone,
                        'type': user.user_type
                    })
                    print(f"✓ Created student: {user.full_name} ({user.phone})")
                else:
                    print(f"⚠ Student with phone {user_data['phone']} already exists, skipping...")
            except Exception as e:
                print(f"✗ Failed to create student: {e}")
        
        return created_users
    
    @classmethod
    def seed_admins(cls, count=3):
        """Seed admin users"""
        created_users = []
        for i in range(count):
            user_data = cls.generate_user_data('admin')
            user_data['is_staff'] = True
            user_data['is_superuser'] = True if i == 0 else False
            
            try:
                if not User.objects.filter(phone=user_data['phone']).exists():
                    user = User.objects.create_user(**user_data)
                    if i == 0:
                        user.is_superuser = True
                        user.is_staff = True
                        user.save()
                    
                    created_users.append({
                        'id': user.id,
                        'name': user.full_name,
                        'phone': user.phone,
                        'type': user.user_type,
                        'is_superuser': user.is_superuser
                    })
                    print(f"✓ Created admin: {user.full_name} ({user.phone}) - {'Superuser' if user.is_superuser else 'Admin'}")
                else:
                    print(f"⚠ Admin with phone {user_data['phone']} already exists, skipping...")
            except Exception as e:
                print(f"✗ Failed to create admin: {e}")
        
        return created_users
    
    @classmethod
    def seed_specific_users(cls):
        """Seed specific users with predefined data"""
        specific_users = [
            {
                'first_name': 'Admin',
                'last_name': 'User',
                'fathers_first_name': 'System',
                'phone': '7123456',
                'user_type': 'admin',
                'password': 'admin123',
            },
            {
                'first_name': 'Fatima',
                'last_name': 'Zahra',
                'fathers_first_name': 'Ali',
                'phone': '9234567',
                'user_type': 'admin',
                'password': 'admin123',
            },
            {
                'first_name': 'Aisha',
                'last_name': 'Siddiqua',
                'fathers_first_name': 'Omar',
                'phone': '5345678',
                'user_type': 'student',
                'password': 'student123'
            },
            {
                'first_name': 'Mariam',
                'last_name': 'Bint Imran',
                'fathers_first_name': 'Imran',
                'phone': '6456789',
                'user_type': 'student',
                'password': 'student123'
            },
            {
                'first_name': 'Khadija',
                'last_name': 'Al-Kubra',
                'fathers_first_name': 'Khuwaylid',
                'phone': '7567890',
                'user_type': 'student',
                'password': 'student123'
            }
        ]
        
        created_users = []
        for user_data in specific_users:
            password = user_data.pop('password')
            is_superuser = user_data.get('user_type') == 'admin' and user_data.get('phone') == '7123456'
            is_staff = user_data.get('user_type') == 'admin'
            
            try:
                if not User.objects.filter(phone=user_data['phone']).exists():
                    user = User.objects.create_user(**user_data, password=password)
                    if is_superuser:
                        user.is_superuser = True
                    if is_staff:
                        user.is_staff = True
                    user.save()
                    
                    created_users.append({
                        'id': user.id,
                        'name': user.full_name,
                        'phone': user.phone,
                        'type': user.user_type
                    })
                    print(f"✓ Created specific user: {user.full_name} ({user.phone})")
                else:
                    print(f"⚠ User with phone {user_data['phone']} already exists, skipping...")
            except Exception as e:
                print(f"✗ Failed to create specific user {user_data['phone']}: {e}")
        
        return created_users
    
    @classmethod
    def run_all(cls, student_count=20, admin_count=3, include_specific=True):
        """Run all seeders"""
        print("\n" + "="*50)
        print("Starting User Seeder...")
        print("="*50 + "\n")
        
        results = {
            'students': [],
            'admins': [],
            'specific': []
        }
        
        # Seed students
        print("📚 Seeding Students...")
        results['students'] = cls.seed_students(student_count)
        
        print("\n👑 Seeding Admins...")
        results['admins'] = cls.seed_admins(admin_count)
        
        # Seed specific users
        if include_specific:
            print("\n⭐ Seeding Specific Users...")
            results['specific'] = cls.seed_specific_users()
        
        # Print summary
        print("\n" + "="*50)
        print("Seeder Summary")
        print("="*50)
        print(f"✅ Students created: {len(results['students'])}")
        print(f"✅ Admins created: {len(results['admins'])}")
        print(f"✅ Specific users created: {len(results['specific'])}")
        print(f"📊 Total users: {User.objects.count()}")
        print("\nDefault Passwords:")
        print("  - Students: password123")
        print("  - Admins: admin123 (for specific users)")
        print("  - Generated users: password123")
        print("="*50 + "\n")
        
        return results

if __name__ == "__main__":
    # Run the seeder
    UserSeeder.run_all(student_count=20, admin_count=3, include_specific=True)