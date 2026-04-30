from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from .models import User
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserResponseSerializer,
    UserDetailSerializer, UserUpdateSerializer, ChangePasswordSerializer,
    UserListSerializer
)
from anamuslimah_project.pagination import CustomPageNumberPagination
from django.utils import timezone
import django.db.models as models

@extend_schema_view(
    list=extend_schema(
        tags=['Users'],
        summary="List all users",
        description="Returns a paginated list of all users. Only accessible by admin users.",
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page (default: 20, max: 100)'),
            OpenApiParameter(name='user_type', type=str, location=OpenApiParameter.QUERY, description='Filter by user type (student, admin)'),
            OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY, description='Search by name or phone'),
            OpenApiParameter(name='is_active', type=bool, location=OpenApiParameter.QUERY, description='Filter by active status'),
        ],
        responses={200: UserListSerializer(many=True)}
    ),
    retrieve=extend_schema(
        tags=['Users'],
        summary="Get user details",
        description="Retrieve detailed information about a specific user.",
        responses={200: UserDetailSerializer}
    ),
    update=extend_schema(
        tags=['Users'],
        summary="Update user",
        description="Update user information. Users can only update their own profile unless admin.",
        responses={200: UserDetailSerializer}
    ),
    destroy=extend_schema(
        tags=['Users'],
        summary="Delete user",
        description="Delete a user account. Only accessible by admin users.",
        responses={204: OpenApiResponse(description="User deleted successfully")}
    )
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination  # Remove the list brackets
    
    def get_queryset(self):
        user = self.request.user
        
        # Start with base queryset
        if user.user_type == 'admin':
            queryset = User.objects.all()
        else:
            queryset = User.objects.filter(id=user.id)
        
        # Apply filters
        user_type = self.request.query_params.get('user_type')
        if user_type and user_type in ['student', 'admin']:
            queryset = queryset.filter(user_type=user_type)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)
        
        # Search by name or phone
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(fathers_first_name__icontains=search) |
                models.Q(phone__icontains=search)
            )
        
        # Order by most recent first
        return queryset.order_by('-date_joined')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        elif self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return UserUpdateSerializer
        return UserDetailSerializer
    
    @extend_schema(
        tags=['Users'],
        summary="Get students list with pagination",
        description="Returns a paginated list of all users with student role. Only accessible by admin users.",
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page'),
            OpenApiParameter(name='search', type=str, location=OpenApiParameter.QUERY, description='Search by name or phone'),
        ],
        responses={200: UserListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='students')
    def get_students(self, request):
        """Get all users with student role (paginated)"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can access this endpoint."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        students = User.objects.filter(user_type='student').order_by('first_name', 'last_name')
        
        # Apply search filter
        search = request.query_params.get('search')
        if search:
            students = students.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(fathers_first_name__icontains=search) |
                models.Q(phone__icontains=search)
            )
        
        # Apply pagination
        page = self.paginate_queryset(students)
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UserListSerializer(students, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Users'],
        summary="Get admins list with pagination",
        description="Returns a paginated list of all users with admin role. Only accessible by admin users.",
        parameters=[
            OpenApiParameter(name='page', type=int, location=OpenApiParameter.QUERY, description='Page number'),
            OpenApiParameter(name='page_size', type=int, location=OpenApiParameter.QUERY, description='Items per page'),
        ],
        responses={200: UserListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='admins')
    def get_admins(self, request):
        """Get all users with admin role (paginated)"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can access this endpoint."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        admins = User.objects.filter(user_type='admin').order_by('first_name', 'last_name')
        
        # Apply pagination
        page = self.paginate_queryset(admins)
        if page is not None:
            serializer = UserListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = UserListSerializer(admins, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Users'],
        summary="Get user statistics",
        description="Get statistics about users (total, active, by role). Only accessible by admin users.",
        responses={200: OpenApiResponse(description="User statistics")}
    )
    @action(detail=False, methods=['get'], url_path='statistics')
    def get_user_statistics(self, request):
        """Get user statistics (admin only)"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can access this endpoint."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        total_users = User.objects.count()
        total_students = User.objects.filter(user_type='student').count()
        total_admins = User.objects.filter(user_type='admin').count()
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        
        return Response({
            'total_users': total_users,
            'total_students': total_students,
            'total_admins': total_admins,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'recent_users': UserListSerializer(
                User.objects.order_by('-date_joined')[:10], 
                many=True
            ).data
        })
    
    @extend_schema(
        tags=['Users'],
        summary="Change user role",
        description="Change a user's role (student/admin). Only accessible by admin users.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'user_type': {'type': 'string', 'enum': ['student', 'admin']}
                }
            }
        },
        responses={200: OpenApiResponse(description="Role changed successfully")}
    )
    @action(detail=True, methods=['patch'], url_path='change-role')
    def change_user_role(self, request, pk=None):
        """Change user role (admin only)"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can change user roles."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        new_role = request.data.get('user_type')
        
        if new_role not in ['student', 'admin']:
            return Response(
                {"error": "Invalid role. Must be 'student' or 'admin'."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.id == request.user.id:
            return Response(
                {"error": "You cannot change your own role."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_role = user.user_type
        user.user_type = new_role
        user.save()
        
        return Response({
            "message": f"User role changed from {old_role} to {new_role} successfully",
            "user_id": user.id,
            "user_name": user.full_name,
            "old_role": old_role,
            "new_role": new_role
        })
    
    @extend_schema(
        tags=['Users'],
        summary="Get current user profile",
        description="Retrieve the profile of the currently authenticated user.",
        responses={200: UserDetailSerializer}
    )
    @action(detail=False, methods=['get'], url_path='profile')
    def get_profile(self, request):
        """Get current user's profile"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Users'],
        summary="Update current user profile",
        description="Update the profile of the currently authenticated user.",
        request=UserUpdateSerializer,
        responses={200: UserDetailSerializer}
    )
    @action(detail=False, methods=['patch', 'put'], url_path='profile')
    def update_profile(self, request):
        """Update current user's profile"""
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # Return detailed user info
            detail_serializer = UserDetailSerializer(user)
            return Response(detail_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        tags=['Users'],
        summary="Activate/deactivate user",
        description="Activate or deactivate a user account. Only accessible by admin users.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'is_active': {'type': 'boolean'}
                }
            }
        },
        responses={200: OpenApiResponse(description="User status updated")}
    )
    @action(detail=True, methods=['patch'], url_path='toggle-active')
    def toggle_active(self, request, pk=None):
        """Activate/deactivate user (admin only)"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can change user status."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = self.get_object()
        
        if user.id == request.user.id:
            return Response(
                {"error": "You cannot deactivate your own account."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_active = request.data.get('is_active')
        if is_active is None:
            return Response(
                {"error": "is_active field is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = is_active
        user.save()
        
        status_text = "activated" if is_active else "deactivated"
        return Response({
            "message": f"User {status_text} successfully",
            "user_id": user.id,
            "user_name": user.full_name,
            "is_active": user.is_active
        })
    
    @extend_schema(
        tags=['Users'],
        summary="Logout user",
        description="Logout by blacklisting the refresh token.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'refresh_token': {'type': 'string', 'description': 'The refresh token to blacklist'}
                },
                'required': ['refresh_token']
            }
        },
        responses={
            200: OpenApiResponse(description="Successfully logged out"),
            400: OpenApiResponse(description="Invalid refresh token")
        }
    )
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        """
        Logout endpoint - validates token but doesn't blacklist
        Relies on short token lifetimes and frontend cleanup
        """
        refresh_token = request.data.get('refresh') or request.data.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {"error": "Refresh token is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Optional: Validate token format/expiry (without blacklisting)
        try:
            token = RefreshToken(refresh_token)
            # Just to check if token is valid - no blacklist
            print(f"Logout for user: {token['user_id']}")
        except Exception as e:
            # Token might be expired - still return success
            print(f"Invalid token during logout: {e}")
        
        # Always return success
        return Response(
            {"message": "Successfully logged out"}, 
            status=status.HTTP_200_OK
        )



@extend_schema(
    tags=['Authentication'],
    summary="User Registration",
    description="Register a new user account. Users can register as student or admin.",
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(
            description="User registered successfully",
            response={
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user': {'type': 'object'},
                    'refresh': {'type': 'string'},
                    'access': {'type': 'string'}
                }
            }
        ),
        400: OpenApiResponse(description="Validation error")
    }
)
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "User registered successfully",
            "user": UserResponseSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['Authentication'],
    summary="User Login",
    description="Login with phone number and password to receive JWT tokens.",
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(
            description="Login successful",
            response={
                'type': 'object',
                'properties': {
                    'refresh': {'type': 'string'},
                    'access': {'type': 'string'},
                    'user': {'type': 'object'}
                }
            }
        ),
        401: OpenApiResponse(description="Invalid credentials")
    }
)
class LoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Update last login
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserResponseSerializer(user).data
        })


@extend_schema(
    tags=['Authentication'],
    summary="Change Password",
    description="Change password for authenticated user.",
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(
            description="Password changed successfully",
            response={
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'access': {'type': 'string'}
                }
            }
        ),
        400: OpenApiResponse(description="Validation error")
    }
)
class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Generate new tokens after password change
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Password changed successfully",
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        })