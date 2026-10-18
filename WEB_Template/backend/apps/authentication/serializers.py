"""
JWT Authentication – Serializers
"""
import logging

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.mdt import roles


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Rozšířený JWT serializer – přidá user data do tokenu."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Přidat custom claims do JWT payload
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        return token


class UserSerializer(serializers.ModelSerializer):
    """Serializer pro čtení dat uživatele."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'is_staff', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer pro registraci nového uživatele."""
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(
            queryset=User.objects.all(),
            message="Uživatel s tímto e-mailem již existuje."
        )]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label='Potvrzení hesla'
    )
    # MDT (T-319): odbornost je povinná, řadí podklad „pro mě“; roli (prohlížející) může předseda změnit
    specialty = serializers.ChoiceField(choices=roles.SPECIALTIES, write_only=True, label='Odbornost')
    # T-338: tituly a šablona klíčových údajů už při registraci (docs/SABLONY_LEKARE.md R5)
    title_before = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=40)
    title_after = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=40)
    templates = serializers.JSONField(write_only=True, required=False)
    preset = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=40)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'specialty',
                  'title_before', 'title_after', 'templates', 'preset']
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Hesla se neshodují."})
        from apps.mdt.templates import clean_templates
        attrs['templates'] = clean_templates(attrs.get('templates'))
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        specialty = validated_data.pop('specialty')
        titles = {k: validated_data.pop(k).strip() for k in ('title_before', 'title_after') if k in validated_data}
        templates, preset = validated_data.pop('templates', {}), validated_data.pop('preset', '')
        with transaction.atomic():
            user = User.objects.create_user(**validated_data)
            roles.assign(user, role=roles.VIEWER, specialty=specialty)
            if titles:
                from apps.mdt.models import UserProfile
                UserProfile.objects.filter(user=user).update(**titles)
            from apps.mdt.templates import save_templates
            save_templates(user, templates, preset)
        try:                                           # T-328: lékař v IRIS pro výběr přítomných a úkoly
            roles.ensure_practitioner(user)
        except Exception:                              # registrace na IRIS nečeká
            logging.getLogger(__name__).warning('Lékaře pro %s se nepodařilo založit v IRIS', user.username)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer pro změnu hesla."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    new_password2 = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Nesprávné aktuální heslo.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Nová hesla se neshodují."})
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
