from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrModeratorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            self.message = 'Authentication required. Please provide a valid JWT token.'
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        is_moderator = request.user.groups.filter(name='Moderator').exists()
        is_owner = getattr(obj, 'created_by', None) == request.user
        if is_moderator or is_owner:
            return True
        owner = getattr(obj, 'created_by', None)
        owner_name = owner.username if owner else 'unknown'
        self.message = (
            f"You do not have permission to modify this object. "
            f"It was created by '{owner_name}'. "
            f"Only the owner or a Moderator can edit or delete it."
        )
        return False


class ReadWriteSerializerMixin:
    """
    read/write serializer switching
    """
    read_serializer = None
    write_serializer = None

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return self.read_serializer
        return self.write_serializer
