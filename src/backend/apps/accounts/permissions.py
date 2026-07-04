from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User

Role = User.Role

# Write access per module, mirroring the permission matrix in SYSTEM_SPEC §6.
# Reads are open to every authenticated user (all users view all data);
# viewers are read-only everywhere by omission from every entry.
# Suppliers/customers follow the use-case diagram: purchase users manage
# suppliers/parties, sale users manage customers.
ROLE_MATRIX: dict[str, frozenset] = {
    "users": frozenset({Role.ADMIN}),
    "locations": frozenset({Role.ADMIN}),
    "currencies": frozenset({Role.ADMIN}),
    "exchange_rates": frozenset({Role.ADMIN, Role.PURCHASE, Role.SALE}),
    "gst_rates": frozenset({Role.ADMIN, Role.PURCHASE, Role.SALE}),
    "categories": frozenset({Role.ADMIN, Role.PURCHASE, Role.SALE}),
    "suppliers": frozenset({Role.ADMIN, Role.PURCHASE}),
    "customers": frozenset({Role.ADMIN, Role.SALE}),
    "products": frozenset({Role.ADMIN, Role.PURCHASE}),
    "purchases": frozenset({Role.ADMIN, Role.PURCHASE}),
    "shipments": frozenset({Role.ADMIN, Role.PURCHASE}),
    "sales": frozenset({Role.ADMIN, Role.SALE}),
    "stock_adjustments": frozenset({Role.ADMIN}),
    "valuation": frozenset({Role.ADMIN}),
}


class ModulePermission(BasePermission):
    """Read for any authenticated user; writes per ROLE_MATRIX via ``view.module``."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.role in ROLE_MATRIX.get(view.module, frozenset({Role.ADMIN}))


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == Role.ADMIN)
