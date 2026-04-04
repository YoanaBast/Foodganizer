from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwnerOrModeratorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return (
            request.user == obj.created_by or
            request.user.groups.filter(name='Moderator').exists()
        )

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
