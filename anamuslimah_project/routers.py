from rest_framework.routers import DefaultRouter
from users.views import UserViewSet
from attendance.views import AttendanceViewSet

# Create a single router instance
router = DefaultRouter()

# Register all ViewSets - endpoints remain the same
router.register(r'users', UserViewSet)        # /api/users/
router.register(r'attendance', AttendanceViewSet)  # /api/attendance/