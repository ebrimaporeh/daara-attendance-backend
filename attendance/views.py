# attendance/views.py
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
from django.db.models import Q, Count, Case, When, IntegerField
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer, AttendanceCreateSerializer, AttendanceUpdateSerializer
from users.models import User
from anamuslimah_project.pagination import CustomPageNumberPagination, LargeResultsSetPagination

@extend_schema_view(
    list=extend_schema(
        tags=['Attendance'],
        summary="List attendance records",
        description="Returns a paginated list of attendance records. Admins see all, students see only their own.",
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page (default: 20, max: 100)'),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, description='Filter by status (present, absent, late, excused, sick)'),
            OpenApiParameter(name='date', type=str, location=OpenApiParameter.QUERY, description='Filter by date (YYYY-MM-DD)'),
            OpenApiParameter(name='start_date', type=str, location=OpenApiParameter.QUERY, description='Filter by start date (YYYY-MM-DD)'),
            OpenApiParameter(name='end_date', type=str, location=OpenApiParameter.QUERY, description='Filter by end date (YYYY-MM-DD)'),
            OpenApiParameter(name='student_id', type=int, location=OpenApiParameter.QUERY, description='Filter by student ID (admins only)'),
            OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY, description='Search by student name or phone'),
        ],
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
    queryset = AttendanceRecord.objects.all().select_related('student', 'marked_by')
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    pagination_class = CustomPageNumberPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = AttendanceRecord.objects.all().select_related('student', 'marked_by')
        
        # Filter by user type
        if user.user_type == 'admin':
            queryset = AttendanceRecord.objects.all()
        else:
            queryset = AttendanceRecord.objects.filter(student=user)
        
        # Apply filters
        status = self.request.query_params.get('status')
        if status and status in ['present', 'absent', 'late', 'excused', 'sick']:
            queryset = queryset.filter(status=status)
        
        date = self.request.query_params.get('date')
        if date:
            try:
                queryset = queryset.filter(date=date)
            except:
                pass
        
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            try:
                queryset = queryset.filter(date__range=[start_date, end_date])
            except:
                pass
        elif start_date:
            try:
                queryset = queryset.filter(date__gte=start_date)
            except:
                pass
        elif end_date:
            try:
                queryset = queryset.filter(date__lte=end_date)
            except:
                pass
        
        # Admin can filter by student
        student_id = self.request.query_params.get('student_id')
        if user.user_type == 'admin' and student_id:
            try:
                queryset = queryset.filter(student_id=int(student_id))
            except:
                pass
        
        # Search by student name or phone
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search) |
                Q(student__last_name__icontains=search) |
                Q(student__phone__icontains=search) |
                Q(student__fathers_first_name__icontains=search)
            )
        
        # Order by date (newest first) and then by student name
        return queryset.order_by('-date', 'student__first_name', 'student__last_name')
    
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
        summary="Get student attendance with pagination",
        description="Get paginated attendance records for a specific student. Admins can access any student, students can only access their own.",
        parameters=[
            OpenApiParameter(name='student_id', type=int, location=OpenApiParameter.PATH, description='Student ID'),
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page'),
        ],
        responses={200: AttendanceRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def get_student_attendance(self, request, student_id=None):
        """Get paginated attendance records for a specific student"""
        user = request.user
        
        # Check permission
        if user.user_type != 'admin' and user.id != int(student_id):
            return Response(
                {"error": "Permission denied"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            student = User.objects.get(id=student_id, user_type='student')
            attendance = AttendanceRecord.objects.filter(student=student).order_by('-date')
            
            # Apply pagination
            page = self.paginate_queryset(attendance)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(attendance, many=True)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"error": "Student not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance by date range with pagination",
        description="Get paginated attendance records within a specific date range.",
        parameters=[
            OpenApiParameter(name='start_date', type=str, location=OpenApiParameter.QUERY, description='Start date (YYYY-MM-DD)', required=True),
            OpenApiParameter(name='end_date', type=str, location=OpenApiParameter.QUERY, description='End date (YYYY-MM-DD)', required=True),
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page'),
        ],
        responses={200: AttendanceRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='date-range')
    def get_by_date_range(self, request):
        """Get paginated attendance records for a date range"""
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
            
            records = self.get_queryset().filter(date__range=[start, end]).order_by('-date')
            
            # Apply pagination
            page = self.paginate_queryset(records)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
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
                
                total_students = User.objects.filter(user_type='student').count()
                
                summary = {
                    'date': date_str,
                    'present': records.filter(status='present').count(),
                    'absent': records.filter(status='absent').count(),
                    'excused': records.filter(status='excused').count(),
                    'late': records.filter(status='late').count(),
                    'sick': records.filter(status='sick').count(),
                    'total': records.count(),
                    'total_students': total_students,
                    'attendance_rate': round(
                        (records.filter(status='present').count() / total_students * 100) 
                        if total_students > 0 else 0, 2
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
        summary="Get today's attendance with pagination",
        description="Get paginated attendance records and summary for today.",
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page'),
        ],
        responses={200: OpenApiResponse(description="Today's attendance data")}
    )
    @action(detail=False, methods=['get'], url_path='today')
    def get_today_attendance(self, request):
        """Get today's attendance records with pagination"""
        today = timezone.now().date()
        records = self.get_queryset().filter(date=today).order_by('student__first_name', 'student__last_name')
        
        # Apply pagination
        page = self.paginate_queryset(records)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            summary = {
                'present': records.filter(status='present').count(),
                'absent': records.filter(status='absent').count(),
                'excused': records.filter(status='excused').count(),
                'late': records.filter(status='late').count(),
                'sick': records.filter(status='sick').count(),
                'total': records.count()
            }
            
            response_data = {
                'date': today,
                'summary': summary,
                'records': serializer.data
            }
            
            # Add pagination info to the response
            response_data['pagination'] = {
                'current_page': page.number,
                'total_pages': page.paginator.num_pages,
                'total_items': page.paginator.count,
                'has_next': page.has_next(),
                'has_previous': page.has_previous(),
                'page_size': page.paginator.per_page
            }
            
            return Response(response_data)
        
        serializer = self.get_serializer(records, many=True)
        return Response({
            'date': today,
            'summary': {
                'present': records.filter(status='present').count(),
                'absent': records.filter(status='absent').count(),
                'excused': records.filter(status='excused').count(),
                'late': records.filter(status='late').count(),
                'sick': records.filter(status='sick').count(),
                'total': records.count()
            },
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
        date_str = request.data.get('date', timezone.now().date())
        
        # Parse date if provided as string
        if isinstance(date_str, str):
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            date = date_str
        
        created_records = []
        errors = []
        
        # Check for existing records on this date
        existing_students = AttendanceRecord.objects.filter(date=date).values_list('student_id', flat=True)
        
        for record_data in records_data:
            record_data['date'] = date
            
            # Check if record already exists
            if record_data.get('student') in existing_students:
                errors.append({
                    'student_id': record_data.get('student'),
                    'error': 'Attendance already marked for this student on this date'
                })
                continue
            
            serializer = AttendanceCreateSerializer(data=record_data)
            if serializer.is_valid():
                record = serializer.save(marked_by=request.user)
                created_records.append({
                    'id': record.id,
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
            'errors': errors,
            'total_processed': len(records_data),
            'total_success': len(created_records),
            'total_errors': len(errors)
        }, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance statistics",
        description="Get overall attendance statistics with pagination for trend data.",
        responses={200: OpenApiResponse(description="Attendance statistics")}
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def get_statistics(self, request):
        """Get overall attendance statistics"""
        queryset = self.get_queryset()
        
        # Get all months with data
        months = queryset.dates('date', 'month', order='DESC')[:12]
        
        monthly_data = []
        for month in months:
            start_date = month
            end_date = datetime(month.year, month.month, monthrange(month.year, month.month)[1]).date()
            month_records = queryset.filter(date__range=[start_date, end_date])
            
            total = month_records.count()
            present = month_records.filter(status='present').count()
            
            monthly_data.append({
                'month': month.strftime('%Y-%m'),
                'attendance_rate': round((present / total * 100) if total > 0 else 0, 2),
                'present': present,
                'absent': month_records.filter(status='absent').count(),
                'late': month_records.filter(status='late').count(),
                'excused': month_records.filter(status='excused').count(),
                'sick': month_records.filter(status='sick').count(),
                'total': total
            })
        
        # Overall statistics
        total_records = queryset.count()
        total_present = queryset.filter(status='present').count()
        
        return Response({
            'overall_rate': round((total_present / total_records * 100) if total_records > 0 else 0, 2),
            'total_records': total_records,
            'monthly_trend': monthly_data,
            'status_breakdown': {
                'present': queryset.filter(status='present').count(),
                'absent': queryset.filter(status='absent').count(),
                'late': queryset.filter(status='late').count(),
                'excused': queryset.filter(status='excused').count(),
                'sick': queryset.filter(status='sick').count()
            }
        })