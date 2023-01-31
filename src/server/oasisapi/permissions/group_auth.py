from functools import reduce

from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import BasePermission


def get_group_names(groups: list) -> set:
    """
    Take a list of Group objects and return set of name strings.

    :param groups: List of Group objects
    :return: Set of names
    """
    if not groups:
        return set()
    return set(map(lambda g: g.name, groups))


def verify_and_get_groups(user: settings.AUTH_USER_MODEL, groups):
    """
    This function compares the groups parameter with the groups the user belongs to and raise an exception when:

    - The user don't belong to any of the groups.
    - Either the users group or the groups parameter is empty, but not both.

    :param user: The current user as a auth user model object
    :param groups: A list of Group objects.
    :return: The intersection of the current users groups and the groups parameter.
    """

    user_groups = user.groups.all()

    if not groups:
        if groups is None:
            return list(user_groups)
        elif len(user_groups) == 0 and len(groups) == 0:
            return []
        elif not user.is_superuser and not user.is_staff:
            raise ValidationError({'groups': 'user is required to specify groups'})
    elif not user.is_superuser and not user.is_staff:
        user_group_names = get_group_names(user_groups)
        group_names = get_group_names(groups)
        user_not_in_groups = list(group_names - user_group_names)
        if user_not_in_groups and len(user_not_in_groups) == len(group_names):
            raise ValidationError({'groups': f'user is not member of group(s): {user_not_in_groups}'})
        return list(filter(lambda ug: ug.name not in user_not_in_groups, groups))

    return groups


def validate_and_update_groups(partial: bool, user: settings.AUTH_USER_MODEL, attrs: dict):
    """
    Convenient function to call from serializers validation functions to make sure the user belongs to
    the groups in attrs and updates it if needed.

    :param partial: Is this a partial update like PATCH? Do only this validation if the groups attribute is set.
    :param user: Current user.
    :param attrs: Attributes from the validation function.
    """

    if not partial or (partial and not attrs.get('groups') is None):
        attrs['groups'] = verify_and_get_groups(user, attrs.get('groups'))


def validate_data_files(user: settings.AUTH_USER_MODEL, data_files: list):
    """
    Verified that the user has access to all data files.

    :param user: Current user
    :param data_files: List of data files
    """

    if data_files:
        for data_file in data_files:
            try:
                verify_and_get_groups(user, data_file.groups.all())
            except ValidationError:
                raise ValidationError({'data_files': f'You are not allowed to use data file {data_file.id}'})


def validate_user_is_owner(user: settings.AUTH_USER_MODEL, obj):
    """
    Checks if the users belongs to the objects groups or is a super user/admin.

    :param user: Current user
    :param obj: Model object with groups.
    :return: True if user is allowed to modify object, False otherwise.
    """

    if user.is_superuser or user.is_staff:
        return True

    if hasattr(obj, 'groups'):

        instance_groups = set(obj.groups.all())

        if len(instance_groups) > 0:
            user_groups = set(user.groups.all())
            diff = instance_groups - user_groups

            if len(diff) == len(instance_groups):
                return False

    return True


def verify_user_is_in_obj_groups(user: settings.AUTH_USER_MODEL, obj, message: str):
    """
    Makes sure the user is allowed to modify the model object, or will raise an exception.

    :param user: Current user
    :param obj: A model object with groups.
    :param message: The message to set in the exception.
    """
    if not validate_user_is_owner(user, obj):
        raise PermissionDenied(message)


class IsMemberOfObjectGroupPermission(BasePermission):
    """
    A permission class used in views to protect users from modify content unless they are a member of the group.

    Is used by VerifyGroupAccessModelViewSet to protect all endpoints except for GET.
    """

    def __init__(self, model, sub_model_attribute=None):
        self.model = model
        self.sub_model_attribute = sub_model_attribute

    def has_permission(self, request, view):

        user = request.user

        if user.is_superuser:
            return True

        pk = view.kwargs.get('pk')
        if pk:

            obj_filter = self.model.objects.filter(pk=pk)
            if obj_filter.exists():
                obj = obj_filter[0]

                if self.sub_model_attribute:
                    obj = getattr(obj, self.sub_model_attribute)

                if obj:
                    return validate_user_is_owner(user, obj)

        return True


class VerifyGroupAccessModelViewSet(viewsets.ModelViewSet):
    """
    Class can be inherited to control read/write access to a viewset / endpoints.

    All HTTP methods (except the ones defined in group_access_method_whitelist) and has a pk set will be
    checked if the user belongs to the objects groups.

    The user will only see objects from the groups it belongs to.

    """

    # What model is this? Analysis, Portfolio etc.
    group_access_model = None

    # Set if the parent to group_access_model own the groups relations
    group_access_sub_model = None
    group_access_sub_attribute = None

    # Whitelisted HTTP methods - all others requests will be checked
    group_access_method_whitelist = ["GET"]

    # Permission class to verify modify requests
    group_access_write_permission = IsMemberOfObjectGroupPermission

    def get_queryset(self):
        """
        Unless the user is a super user build a query to filter models available for the current user. This will hide
        model objects from groups the user don't belong to.

        :return: A QuerySet of model objects available for current user.
        """

        if self.queryset:
            return self.queryset

        if self.group_access_model:
            user = self.request.user

            if user.is_superuser:
                return self.group_access_model.objects.all()

            user_groups = self.request.user.groups.all()
            if self.group_access_sub_model:
                if len(user_groups) == 0:
                    user_sub_models = self.group_access_sub_model.objects.filter(groups=None)
                else:
                    query = reduce(lambda q, value: q | Q(groups=value), user_groups, Q(groups=None))
                    user_sub_models = self.group_access_sub_model.objects.filter(query)

                if len(user_sub_models) == 0:
                    return self.group_access_model.objects.none()

                query = reduce(lambda q, value: q | Q(portfolio=value), user_sub_models, Q())
            else:
                if len(user_groups) == 0:
                    query = Q(groups=None)
                else:
                    query = reduce(lambda q, value: q | Q(groups=value), user_groups, Q())

            return self.group_access_model.objects.filter(query).distinct()
        else:
            raise ValueError('Group access enabled without any specified group_access_sub_model')

    def get_permissions(self):
        """
        Return either the default class_permissions or append our group_access_model to it on http modify requests.

        :return: List of permission objects to control this endpoints access.
        """

        class_permissions = [permission() for permission in self.permission_classes]

        if self.group_access_model:
            if self.request.method not in self.group_access_method_whitelist:
                return class_permissions + [self.group_access_write_permission(
                    self.group_access_model, sub_model_attribute=self.group_access_sub_attribute)]

        return class_permissions

    def create(self, request, *args, **kwargs):
        self.create_missing_groups(request)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.create_missing_groups(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.create_missing_groups(request)
        return super().partial_update(request, *args, **kwargs)

    def create_missing_groups(self, request):
        """
        For admin/staff users create missing groups. This allows admin to create resources for groups not yet
        replicated from keycloak.

        :param request: Http request.
        """
        user = request.user
        if user:
            if user.is_superuser or user.is_staff:
                groups = request.data.get('groups', [])
                for group in groups:
                    Group.objects.get_or_create(name=group)
