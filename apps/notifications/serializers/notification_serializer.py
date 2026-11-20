from rest_framework import serializers

from apps.notifications.models.notification import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializador de lectura para notificaciones del usuario.
    Expone campos enriquecidos con etiquetas legibles para frontend.
    """

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    priority_display = serializers.CharField(
        source="get_priority_display", read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            "id_notification",
            "company_id",
            "recipient_id",
            "title",
            "message",
            "category",
            "category_display",
            "priority",
            "priority_display",
            "event_type",
            "action_url",
            "origin_id",
            "metadata",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationUnreadCountSerializer(serializers.Serializer):
    """
    Serializador para la respuesta del endpoint de conteo no leídas.
    """

    unread_count = serializers.IntegerField(min_value=0)
    company_id = serializers.IntegerField(allow_null=True)
