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

@extend_schema_view(
    list=extend_schema(
        tags=['Users'],
        summary="List all users",
        description="Returns a list of all users. Only accessible by admin users.",
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
    
    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'admin':
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
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
        summary="Get students list",
        description="Returns a list of all users with student role. Only accessible by admin users.",
        responses={200: UserListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='students')
    def get_students(self, request):
        """Get all users with student role"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can access this endpoint."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        students = User.objects.filter(user_type='student')
        serializer = UserListSerializer(students, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        tags=['Users'],
        summary="Get admins list",
        description="Returns a list of all users with admin role. Only accessible by admin users.",
        responses={200: UserListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='admins')
    def get_admins(self, request):
        """Get all users with admin role"""
        if request.user.user_type != 'admin':
            return Response(
                {"error": "Permission denied. Only admins can access this endpoint."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        admins = User.objects.filter(user_type='admin')
        serializer = UserListSerializer(admins, many=True)
        return Response(serializer.data)
    
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
        
        user.user_type = new_role
        user.save()
        
        return Response({
            "message": f"User role changed to {new_role} successfully",
            "user_id": user.id,
            "user_name": user.full_name,
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
        responses={200: OpenApiResponse(description="Successfully logged out")}
    )
    @action(detail=False, methods=['post'], url_path='logout')
    def logout(self, request):
        """Logout by blacklisting refresh token"""
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                return Response(
                    {"message": "Successfully logged out"}, 
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"error": "Refresh token is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
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