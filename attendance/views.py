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
from django.db.models import Q, Count
from .models import AttendanceRecord
from .serializers import AttendanceRecordSerializer, AttendanceCreateSerializer, AttendanceUpdateSerializer
from users.models import User
from anamuslimah_project.pagination import CustomPageNumberPagination


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

        if user.user_type == 'admin':
            queryset = AttendanceRecord.objects.all().select_related('student', 'marked_by')
        else:
            queryset = AttendanceRecord.objects.filter(student=user).select_related('student', 'marked_by')

        # Status filter
        status_param = self.request.query_params.get('status')
        if status_param and status_param in ['present', 'absent', 'late', 'excused', 'sick']:
            queryset = queryset.filter(status=status_param)

        # Date filters
        date = self.request.query_params.get('date')
        if date:
            try:
                queryset = queryset.filter(date=date)
            except Exception:
                pass

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            try:
                queryset = queryset.filter(date__range=[start_date, end_date])
            except Exception:
                pass
        elif start_date:
            try:
                queryset = queryset.filter(date__gte=start_date)
            except Exception:
                pass
        elif end_date:
            try:
                queryset = queryset.filter(date__lte=end_date)
            except Exception:
                pass

        # Admin-only: filter by student
        student_id = self.request.query_params.get('student_id')
        if user.user_type == 'admin' and student_id:
            try:
                queryset = queryset.filter(student_id=int(student_id))
            except Exception:
                pass

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search) |
                Q(student__last_name__icontains=search) |
                Q(student__phone__icontains=search) |
                Q(student__fathers_first_name__icontains=search)
            )

        return queryset.order_by('-date', 'student__first_name', 'student__last_name')

    def get_serializer_class(self):
        if self.action == 'create':
            return AttendanceCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return AttendanceUpdateSerializer
        return AttendanceRecordSerializer

    def perform_create(self, serializer):
        serializer.save(marked_by=self.request.user)

    # -------------------------------------------------------------------------
    # TODAY — Workflow A
    # Returns ALL students merged with their attendance record for today.
    # Students with no record get status="unmarked" so the frontend knows they
    # haven't been assessed yet (not assumed absent).
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Get today's attendance session",
        description=(
            "Returns all students merged with today's attendance records. "
            "Students with no record have status='unmarked' — they have NOT been "
            "assessed yet. Only students explicitly marked appear in the DB. "
            "Supports pagination and search so teachers can find students quickly."
        ),
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page'),
            OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY, description='Search by name or phone'),
            OpenApiParameter(name='status', type=str, location=OpenApiParameter.QUERY, description='Filter: present|absent|late|excused|sick|unmarked'),
        ],
        responses={200: OpenApiResponse(description="Session data with merged student+attendance list")}
    )
    @action(detail=False, methods=['get'], url_path='today')
    def get_today_attendance(self, request):
        """
        Workflow A: returns all students with their attendance status for today.
        'unmarked' means no record exists yet — not absent.
        """
        today = timezone.now().date()

        # All active students
        students_qs = User.objects.filter(user_type='student').order_by('first_name', 'last_name')

        # Search support
        search = request.query_params.get('search', '').strip()
        if search:
            students_qs = students_qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(fathers_first_name__icontains=search)
            )

        # Build a map of today's records keyed by student_id
        today_records = AttendanceRecord.objects.filter(
            date=today
        ).select_related('student', 'marked_by')

        record_map = {r.student_id: r for r in today_records}

        # Merge students with their record
        merged = []
        for student in students_qs:
            record = record_map.get(student.id)
            merged.append({
                'student_id': student.id,
                'student_name': f"{student.first_name} {student.last_name}",
                'student_phone': getattr(student, 'phone', ''),
                # Attendance fields — None/unmarked if no record
                'record_id': record.id if record else None,
                'status': record.status if record else 'unmarked',
                'notes': record.notes if record else '',
                'marked_by_name': record.marked_by.full_name if record and record.marked_by else None,
                'marked_at': record.updated_at.isoformat() if record else None,
            })

        # Status filter (including 'unmarked')
        status_filter = request.query_params.get('status', '').strip()
        valid_statuses = ['present', 'absent', 'late', 'excused', 'sick', 'unmarked']
        if status_filter and status_filter in valid_statuses:
            merged = [m for m in merged if m['status'] == status_filter]

        # Summary counts (before pagination, after search+filter)
        summary = {
            'total_students': students_qs.count(),
            'present': sum(1 for m in merged if m['status'] == 'present'),
            'absent': sum(1 for m in merged if m['status'] == 'absent'),
            'late': sum(1 for m in merged if m['status'] == 'late'),
            'excused': sum(1 for m in merged if m['status'] == 'excused'),
            'sick': sum(1 for m in merged if m['status'] == 'sick'),
            'unmarked': sum(1 for m in merged if m['status'] == 'unmarked'),
            'marked': sum(1 for m in merged if m['status'] != 'unmarked'),
        }

        # Manual pagination
        paginator = self.pagination_class()
        from rest_framework.request import Request
        page_size = int(request.query_params.get('page_size', paginator.page_size or 50))
        page_num = int(request.query_params.get('page', 1))
        start = (page_num - 1) * page_size
        end = start + page_size
        total = len(merged)
        page_data = merged[start:end]

        return Response({
            'date': today,
            'summary': summary,
            'pagination': {
                'current_page': page_num,
                'page_size': page_size,
                'total_items': total,
                'total_pages': -(-total // page_size),  # ceiling division
                'has_next': end < total,
                'has_previous': page_num > 1,
            },
            'students': page_data,
        })

    # -------------------------------------------------------------------------
    # UPSERT — create or update a single attendance record
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Upsert attendance record",
        description="Create or update attendance for a student on a given date. Idempotent.",
        request={
            'type': 'object',
            'required': ['student', 'date', 'status'],
            'properties': {
                'student': {'type': 'integer'},
                'date': {'type': 'string', 'format': 'date'},
                'status': {'type': 'string', 'enum': ['present', 'absent', 'late', 'excused', 'sick']},
                'notes': {'type': 'string'},
            }
        },
        responses={200: AttendanceRecordSerializer}
    )
    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert_attendance(self, request):
        """Create or update attendance for a student on a given date."""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Only admins can mark attendance"},
                status=status.HTTP_403_FORBIDDEN
            )

        student_id = request.data.get('student')
        date_str = request.data.get('date')
        status_value = request.data.get('status')
        notes = request.data.get('notes', '')

        if not student_id or not date_str or not status_value:
            return Response(
                {"error": "student, date, and status are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_statuses = ['present', 'absent', 'late', 'excused', 'sick']
        if status_value not in valid_statuses:
            return Response(
                {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = User.objects.get(id=student_id, user_type='student')
        except User.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        record, created = AttendanceRecord.objects.update_or_create(
            student=student,
            date=date_obj,
            defaults={
                'status': status_value,
                'notes': notes,
                'marked_by': request.user,
            }
        )

        serializer = AttendanceRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # CLOSE SESSION — bulk mark all unmarked students as absent for a date
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Close attendance session",
        description=(
            "Marks all students who have NO attendance record for the given date as 'absent'. "
            "This finalises the session. Only unmarked students are affected — "
            "already-marked students are untouched."
        ),
        request={
            'type': 'object',
            'properties': {
                'date': {'type': 'string', 'format': 'date', 'description': 'Defaults to today'},
                'notes': {'type': 'string', 'description': 'Note appended to auto-absent records'},
            }
        },
        responses={200: OpenApiResponse(description="Close session results")}
    )
    @action(detail=False, methods=['post'], url_path='close-session')
    def close_session(self, request):
        """
        Finalise a session: all students with no record for the date are marked absent.
        Safe to call multiple times — already-marked students are never changed.
        """
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Only admins can close a session"},
                status=status.HTTP_403_FORBIDDEN
            )

        date_str = request.data.get('date')
        notes = request.data.get('notes', 'Absent - session closed')

        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().date()

        # Find students who already have a record for this date
        already_marked_ids = AttendanceRecord.objects.filter(
            date=target_date
        ).values_list('student_id', flat=True)

        # Students with no record
        unmarked_students = User.objects.filter(
            user_type='student'
        ).exclude(id__in=already_marked_ids)

        created_count = 0
        records_to_create = []
        for student in unmarked_students:
            records_to_create.append(AttendanceRecord(
                student=student,
                date=target_date,
                status='absent',
                notes=notes,
                marked_by=request.user,
            ))

        if records_to_create:
            AttendanceRecord.objects.bulk_create(records_to_create)
            created_count = len(records_to_create)

        # Summary after closing
        all_records = AttendanceRecord.objects.filter(date=target_date)
        summary = {
            'present': all_records.filter(status='present').count(),
            'absent': all_records.filter(status='absent').count(),
            'late': all_records.filter(status='late').count(),
            'excused': all_records.filter(status='excused').count(),
            'sick': all_records.filter(status='sick').count(),
            'total': all_records.count(),
        }

        return Response({
            'message': f'Session closed. {created_count} students marked absent.',
            'date': target_date,
            'auto_marked_absent': created_count,
            'already_marked': len(already_marked_ids),
            'summary': summary,
        }, status=status.HTTP_200_OK)

    # -------------------------------------------------------------------------
    # BULK CREATE
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Bulk create attendance",
        description="Create multiple attendance records at once. Admin only.",
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
        """Create multiple attendance records at once (admin only)."""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Only admins can create bulk attendance"},
                status=status.HTTP_403_FORBIDDEN
            )

        records_data = request.data.get('records', [])
        date_str = request.data.get('date')

        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            date = timezone.now().date()

        created_records = []
        errors = []
        existing_student_ids = set(
            AttendanceRecord.objects.filter(date=date).values_list('student_id', flat=True)
        )

        for record_data in records_data:
            record_data['date'] = date
            student_id = record_data.get('student')

            if student_id in existing_student_ids:
                errors.append({
                    'student_id': student_id,
                    'error': 'Attendance already marked for this student on this date'
                })
                continue

            serializer = AttendanceCreateSerializer(data=record_data)
            if serializer.is_valid():
                record = serializer.save(marked_by=request.user)
                created_records.append({
                    'id': record.id,
                    'student_id': record.student.id,
                    'student_name': record.student.get_full_name(),
                    'status': record.status
                })
                existing_student_ids.add(student_id)
            else:
                errors.append({'student_id': student_id, 'errors': serializer.errors})

        return Response({
            'message': f'Created {len(created_records)} records',
            'created': created_records,
            'errors': errors,
            'total_processed': len(records_data),
            'total_success': len(created_records),
            'total_errors': len(errors)
        }, status=status.HTTP_201_CREATED)

    # -------------------------------------------------------------------------
    # STUDENT ATTENDANCE (paginated)
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Get student attendance history",
        parameters=[
            OpenApiParameter(name='student_id', type=int, location=OpenApiParameter.PATH),
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY),
        ],
        responses={200: AttendanceRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='student/(?P<student_id>[^/.]+)')
    def get_student_attendance(self, request, student_id=None):
        """Get paginated attendance records for a specific student."""
        user = request.user
        if user.user_type != 'admin' and user.id != int(student_id):
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        try:
            student = User.objects.get(id=student_id, user_type='student')
        except User.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        attendance = AttendanceRecord.objects.filter(student=student).order_by('-date')
        page = self.paginate_queryset(attendance)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(attendance, many=True)
        return Response(serializer.data)

    # -------------------------------------------------------------------------
    # DATE RANGE
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance by date range",
        parameters=[
            OpenApiParameter(name='start_date', type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='end_date', type=str, location=OpenApiParameter.QUERY, required=True),
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY),
        ],
        responses={200: AttendanceRecordSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='date-range')
    def get_by_date_range(self, request):
        """Get paginated attendance records for a date range."""
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
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        records = self.get_queryset().filter(date__range=[start, end]).order_by('-date')
        page = self.paginate_queryset(records)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance summary",
        parameters=[
            OpenApiParameter(name='date', type=str, location=OpenApiParameter.QUERY),
            OpenApiParameter(name='month', type=str, location=OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiResponse(description="Summary statistics")}
    )
    @action(detail=False, methods=['get'], url_path='summary')
    def get_attendance_summary(self, request):
        """Get attendance summary for a specific date or month."""
        date_str = request.query_params.get('date')
        month_str = request.query_params.get('month')
        queryset = self.get_queryset()

        if date_str:
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            records = queryset.filter(date=date)
            total_students = User.objects.filter(user_type='student').count()
            present_count = records.filter(status='present').count()

            return Response({
                'date': date_str,
                'present': present_count,
                'absent': records.filter(status='absent').count(),
                'excused': records.filter(status='excused').count(),
                'late': records.filter(status='late').count(),
                'sick': records.filter(status='sick').count(),
                'total_marked': records.count(),
                'total_students': total_students,
                'unmarked': total_students - records.count(),
                'attendance_rate': round(
                    (present_count / total_students * 100) if total_students > 0 else 0, 2
                )
            })

        elif month_str:
            try:
                year, month = map(int, month_str.split('-'))
                start_date = datetime(year, month, 1).date()
                end_date = datetime(year, month, monthrange(year, month)[1]).date()
            except (ValueError, IndexError):
                return Response(
                    {"error": "Invalid month format. Use YYYY-MM"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            records = queryset.filter(date__range=[start_date, end_date])
            return Response({
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
            })

        return Response(
            {"error": "Please provide either date or month parameter"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------
    @extend_schema(
        tags=['Attendance'],
        summary="Get attendance statistics",
        responses={200: OpenApiResponse(description="Attendance statistics")}
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def get_statistics(self, request):
        """Get overall attendance statistics with monthly trend."""
        queryset = self.get_queryset()
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
                'sick': queryset.filter(status='sick').count(),
            }
        })