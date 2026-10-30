from rest_framework import serializers


class GenericHistorySerializer(serializers.Serializer):
    """
    Serializer genérico para leer el historial de cualquier modelo que implemente
    django-simple-history, protegiendo datos sensibles y estandarizando los diffs.
    """

    history_id = serializers.IntegerField()
    history_date = serializers.DateTimeField()
    history_type = serializers.CharField(max_length=1)
    history_user = serializers.SerializerMethodField()

    SENSITIVE_FIELDS = frozenset({
        "password",
        "token",
        "secret",
        "refresh_token",
        "access_token",
    })

    def get_history_user(self, obj) -> str:
        user = getattr(obj, "history_user", None)
        if user:
            return getattr(user, "username", str(user))
        return "Sistema / Anónimo"

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # 1. Traducir el tipo de acción
        type_map = {"+": "Creación", "-": "Eliminación", "~": "Actualización"}
        data["action"] = type_map.get(instance.history_type, "Desconocido")

        # 2. Obtener el nombre legible del objeto
        data["object_repr"] = (
            str(instance.instance) if instance.instance else str(instance)
        )

        # 3. Calcular los cambios (Diff) si es una actualización
        changes = []
        if instance.history_type == "~" and instance.prev_record:
            try:
                delta = instance.diff_against(instance.prev_record)
                for change in delta.changes:
                    field_name = change.field
                    old_val = change.old
                    new_val = change.new

                    # Enmascarar datos sensibles para prevenir fugas de contraseñas/secretos
                    if field_name.lower() in self.SENSITIVE_FIELDS:
                        old_val = "********" if old_val else None
                        new_val = "********" if new_val else None

                    changes.append({
                        "field": field_name,
                        "old": str(old_val) if old_val is not None else None,
                        "new": str(new_val) if new_val is not None else None,
                    })
            except Exception:
                changes = []

        data["changes"] = changes
        return data


class ConfigurationAuditHistorySerializer(serializers.Serializer):
    """
    Adaptador para presentar registros de ConfigurationAudit en el contrato
    unificado del endpoint SystemHistoryViewSet.
    """

    history_id = serializers.IntegerField(source="id")
    history_date = serializers.DateTimeField(source="created_at")
    history_user = serializers.SerializerMethodField()
    action = serializers.SerializerMethodField()
    object_repr = serializers.CharField(source="parameter_key")
    changes = serializers.SerializerMethodField()

    def get_history_user(self, obj) -> str:
        if obj.user:
            return getattr(obj.user, "username", str(obj.user))
        return "Sistema / Anónimo"

    def get_action(self, obj) -> str:
        return obj.get_action_display()

    def get_changes(self, obj) -> list:
        if obj.action == "UPDATE":
            return [
                {
                    "field": "value",
                    "old": str(obj.old_value) if obj.old_value is not None else None,
                    "new": str(obj.new_value) if obj.new_value is not None else None,
                }
            ]
        return []

