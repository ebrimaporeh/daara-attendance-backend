from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone
from datetime import datetime
from calendar import monthrange
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer, AttendanceCreateSerializer, AttendanceUpdateSerializer
from users.models import User

@extend_schema_view(
    list=extend_schema(
        tags=['Attendance'],
        summary="List attendance records",
        description="Returns a list of attendance records. Admins see all, students see only their own.",
        responses={200: AttendanceRecordSerializer(many=True)}
    ),
    create=extend_schema(
        tags=['Attendance'],
        summary="Create attendance record",
        description="Create a new attendance record. Only accessible by admin users.",
        request=AttendanceCreateSerializer,
        responses={201: AttendanceRecordSerializer}
    ),
    retrieve=extend_schema(
        tags=['Attendance'],
        summary="Get attendance record",
        description="Retrieve a specific attendance record by ID.",
        responses={200: AttendanceRecordSerializer}
    ),
    update=extend_schema(
        tags=['Attendance'],
        summary="Update attendance record",
        description="Update an existing attendance record. Only accessible by admin users.",
        responses={200: AttendanceRecordSerializer}
    ),
    destroy=extend_schema(
        tags=['Attendance'],
        summary="Delete attendance record",
        description="Delete an attendance record. Only accessible by admin users.",
        responses={204: OpenApiResponse(description="Record deleted successfully")}
    )
)
class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = AttendanceRecord.objects.all()
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return AttendanceRecord.objects.all()
        return AttendanceRecord.objects.filter(student=user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return AttendanceUpdateSerializer
        return AttendanceRecordSerializer
    
    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)
    
    @extend_schema(
        tags=['Attendance'],
        summary="Get student attendance",
        description="Get attendance records for a specific student. Admins can access any student, students can only access their own.",
        parameters=[
            OpenApiParameter(name='student_id', type=int, location=OpenApiParameter.PATH, description='Student ID')
        ],
        responses={200: AttendanceRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def get_student_attendance(self, request, student_id=None):
        """Get attendance records for a specific student"""
        user = request.user
        
        # Check permission
        if user.user_type != 'admin' and user.id != int(student_id):
            return Response(
                {"error": "Permission denied"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = User.objects.get(id=student_id, user_type='student')
            attendance = AttendanceRecord.objects.filter(student=student)
            serializer = self.get_serializer(attendance, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"error": "Student not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance by date range",
        description="Get attendance records within a specific date range.",
        parameters=[
            OpenApiParameter(name='start_date', type=str, location=OpenApiParameter.QUERY, description='Start date (YYYY-MM-DD)', required=True),
            OpenApiParameter(name='end_date', type=str, location=OpenApiParameter.QUERY, description='End date (YYYY-MM-DD)', required=True),
        ],
        responses={200: AttendanceRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='date-range')
    def get_by_date_range(self, request):
        """Get attendance records for a date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {"error": "start_date and end_date are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start > end:
                return Response(
                    {"error": "start_date must be before end_date"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            records = self.get_queryset().filter(date__range=[start, end])
            serializer = self.get_serializer(records, many=True)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance summary",
        description="Get attendance summary for a specific date or month.",
        parameters=[
            OpenApiParameter(name='date', type=str, location=OpenApiParameter.QUERY, description='Date (YYYY-MM-DD)'),
            OpenApiParameter(name='month', type=str, location=OpenApiParameter.QUERY, description='Month (YYYY-MM)'),
        ],
        responses={200: OpenApiResponse(description="Summary statistics")}
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def get_attendance_summary(self, request):
        """Get attendance summary for a specific date or month"""
        date_str = request.query_params.get('date')
        month_str = request.query_params.get('month')
        
        queryset = self.get_queryset()
        
        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                records = queryset.filter(date=date)
                
                summary = {
                    'date': date_str,
                    'present': records.filter(status='present').count(),
                    'absent': records.filter(status='absent').count(),
                    'excused': records.filter(status='excused').count(),
                    'late': records.filter(status='late').count(),
                    'sick': records.filter(status='sick').count(),
                    'total': records.count(),
                    'attendance_rate': round(
                        (records.filter(status='present').count() / records.count() * 100) 
                        if records.count() > 0 else 0, 2
                    )
                }
                return Response(summary)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        elif month_str:
            try:
                year, month = map(int, month_str.split('-'))
                start_date = datetime(year, month, 1).date()
                end_date = datetime(year, month, monthrange(year, month)[1]).date()
                
                records = queryset.filter(date__range=[start_date, end_date])
                
                summary = {
                    'month': month_str,
                    'year': year,
                    'month_name': datetime(year, month, 1).strftime('%B'),
                    'present': records.filter(status='present').count(),
                    'absent': records.filter(status='absent').count(),
                    'excused': records.filter(status='excused').count(),
                    'late': records.filter(status='late').count(),
                    'sick': records.filter(status='sick').count(),
                    'total_records': records.count(),
                    'unique_students': records.values('student').distinct().count(),
                }
                return Response(summary)
            except (ValueError, IndexError):
                return Response(
                    {"error": "Invalid month format. Use YYYY-MM"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {"error": "Please provide either date or month parameter"}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @extend_schema(
        tags=['Attendance'],
        summary="Get today's attendance",
        description="Get attendance records and summary for today.",
        responses={200: OpenApiResponse(description="Today's attendance data")}
    )
    @action(detail=False, methods=['get'], url_path='today')
    def get_today_attendance(self, request):
        """Get today's attendance records"""
        today = timezone.now().date()
        records = self.get_queryset().filter(date=today)
        serializer = self.get_serializer(records, many=True)
        
        summary = {
            'present': records.filter(status='present').count(),
            'absent': records.filter(status='absent').count(),
            'excused': records.filter(status='excused').count(),
            'late': records.filter(status='late').count(),
            'sick': records.filter(status='sick').count(),
            'total': records.count()
        }
        
        return Response({
            'date': today,
            'summary': summary,
            'records': serializer.data
        })
    
    @extend_schema(
        tags=['Attendance'],
        summary="Bulk create attendance",
        description="Create multiple attendance records at once. Only accessible by admin users.",
        request={
            'type': 'object',
            'properties': {
                'records': {'type': 'array', 'items': {'type': 'object'}},
                'date': {'type': 'string', 'format': 'date'}
            }
        },
        responses={201: OpenApiResponse(description="Bulk creation results")}
    )
    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create_attendance(self, request):
        """Create multiple attendance records at once (admin only)"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Only admins can create bulk attendance"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        records_data = request.data.get('records', [])
        date = request.data.get('date', timezone.now().date())
        
        created_records = []
        errors = []
        
        for record_data in records_data:
            record_data['date'] = date
            serializer = AttendanceCreateSerializer(data=record_data)
            if serializer.is_valid():
                record = serializer.save(marked_by=request.user)
                created_records.append({
                    'student_id': record.student.id,
                    'student_name': record.student.full_name,
                    'status': record.status
                })
            else:
                errors.append({
                    'student_id': record_data.get('student'),
                    'errors': serializer.errors
                })
        
        return Response({
            'message': f'Created {len(created_records)} records',
            'created': created_records,
            'errors': errors
        }, status=status.HTTP_201_CREATED)