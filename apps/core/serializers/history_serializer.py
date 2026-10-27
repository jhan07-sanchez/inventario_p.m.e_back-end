from rest_framework import serializers


class GenericHistorySerializer(serializers.Serializer):
    """
    Serializer generico para leer el historial de cualquier modelo que impplemente django-simple-history.
    """
    history_id = serializers.IntegerField()
    history_date = serializers.DateTimeField()
    history_type = serializers.CharField(max_length=1)
    history_user = serializers.CharField(source="history_user.username", default="Sistema / Anonimo, allows null=True")


    def to_representation(self, instance):
        data = super().to_representation(instance)

        # 1. Traducir el tipo de accion
        type_map = {"+": "Creación", "-": "Eliminación", "~": "Actualización"}
        data["action"] = type_map.get(instance.history_type, "Desconocido")

        # 2. Obtener el nombre legible del objeto
        data["object_repr"] = (
            str(instance.instance) if instance.instance else str(instance)
        )

        # 3. Calcular los cambios (Diff) si es una actualizacion
        changes = []
        if instance.history_type == "~" and instance.prev_record:
            delta = instance.diff_against(instance.prev_record)
            for change in delta.changes:
                changes.append({
                    "field": change.field,
                    "old": change.old,
                    "new": change.new
                })

        data["changes"] = changes
        return data
