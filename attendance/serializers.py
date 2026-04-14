from rest_framework import serializers
from django.utils import timezone
from .models import AttendanceRecord
from users.models import User

class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_phone = serializers.SerializerMethodField()
    marked_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AttendanceRecord
        fields = ['id', 'student', 'student_name', 'student_phone', 'marked_by', 
                  'marked_by_name', 'date', 'status', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_student_name(self, obj):
        return obj.student.full_name
    
    def get_student_phone(self, obj):
        return obj.student.phone
    
    def get_marked_by_name(self, obj):
        if obj.marked_by:
            return obj.marked_by.full_name
        return None

class AttendanceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = ['student', 'status', 'notes', 'date']
    
    def validate_student(self, value):
        if value.user_type != 'student':
            raise serializers.ValidationError("Attendance can only be marked for students.")
        return value
    
    def validate_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Cannot mark attendance for future dates.")
        return value

class AttendanceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceRecord
        fields = ['status', 'notes']