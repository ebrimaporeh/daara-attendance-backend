from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
import re

class UserManager(BaseUserManager):
    """Custom user manager for phone number authentication"""
    
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError('The Phone number must be set')
        
        # Validate phone number format
        if not self.validate_phone_number(phone):
            raise ValueError('Phone number must be 7 digits starting with 2,4,5,6,7, or 9')
        
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(phone, password, **extra_fields)
    
    @staticmethod
    def validate_phone_number(phone):
        """Validate phone number: 7 digits starting with 2,4,5,6,7,9"""
        pattern = r'^[245679]\d{6}$'
        return bool(re.match(pattern, str(phone)))

class User(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('admin', 'Admin'),
    )
    
    phone = models.CharField(
        max_length=7, 
        unique=True,
        help_text="7 digits starting with 2,4,5,6,7, or 9"
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    fathers_first_name = models.CharField(max_length=100, help_text="Father's first name")
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    
    # Required fields for Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_student(self):
        return self.user_type == 'student'
    
    @property
    def is_admin_user(self):
        return self.user_type == 'admin'
    
    class Meta:
        db_table = 'users'
        ordering = ['first_name', 'last_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'