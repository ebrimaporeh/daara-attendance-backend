from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from .models import User
import re

class PhoneNumberField(serializers.CharField):
    """Custom field for phone number validation"""
    
    def validate(self, value):
        # Validate phone number format (7 digits starting with 2,4,5,6,7,9)
        pattern = r'^[2-9]\d{6}$'
        if not re.match(pattern, str(value)):
            raise serializers.ValidationError(
                "Phone number must be a gambian number of 7 digits and not start with 0 or 1."
            )
        return value

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    phone = PhoneNumberField()
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'fathers_first_name', 
            'phone', 'password', 'confirm_password', 'user_type'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'fathers_first_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Password fields didn't match."})
        
        # Check if phone already exists
        if User.objects.filter(phone=attrs['phone']).exists():
            raise serializers.ValidationError({"phone": "A user with this phone number already exists."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    phone = PhoneNumberField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        phone = attrs.get('phone')
        password = attrs.get('password')
        
        if phone and password:
            # Authenticate using phone number
            try:
                user = User.objects.get(phone=phone)
                user = authenticate(username=user.phone, password=password)
                
                if not user:
                    raise serializers.ValidationError('Invalid phone number or password.')
                if not user.is_active:
                    raise serializers.ValidationError('This account is inactive.')
                    
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid phone number or password.')
        else:
            raise serializers.ValidationError('Must include "phone" and "password".')
        
        attrs['user'] = user
        return attrs

class UserResponseSerializer(serializers.ModelSerializer):
    """Serializer for user responses (doesn't include sensitive data)"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'fathers_first_name', 'phone', 'user_type', 'full_name']
    
    def get_full_name(self, obj):
        return obj.full_name

class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'fathers_first_name', 
            'phone', 'user_type', 'full_name', 'date_joined', 
            'last_login', 'is_active'
        ]
        read_only_fields = ['date_joined', 'last_login', 'is_active']
    
    def get_full_name(self, obj):
        return obj.full_name

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'fathers_first_name']
    
    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.fathers_first_name = validated_data.get('fathers_first_name', instance.fathers_first_name)
        instance.save()
        return instance

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_new_password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "New passwords don't match."})
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Old password is incorrect.')
        return value

class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users (admin view)"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'phone', 'user_type', 'full_name', 'is_active']
    
    def get_full_name(self, obj):
        return obj.full_name