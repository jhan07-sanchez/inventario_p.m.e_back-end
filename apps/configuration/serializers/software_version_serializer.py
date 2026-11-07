from rest_framework import serializers

from apps.configuration.dto import (
    ChangelogEntryDto,
    SoftwareVersionCreateDto,
    SoftwareVersionUpdateDto,
)
from apps.configuration.models import SoftwareVersion, VersionChangelogEntry


class VersionChangelogEntrySerializer(serializers.ModelSerializer):
    """
    Serializer para representar una entrada individual de changelog.
    """

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )

    class Meta:
        model = VersionChangelogEntry
        fields = (
            "id_entry",
            "category",
            "category_display",
            "title",
            "description",
            "order",
            "created_at",
        )


class SoftwareVersionListSerializer(serializers.ModelSerializer):
    """
    Serializer resumido para listar versiones (historial y administración).
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    total_changes = serializers.SerializerMethodField()
    published_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SoftwareVersion
        fields = (
            "id_version",
            "version",
            "name",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "published_at",
            "published_by_name",
            "total_changes",
            "created_at",
            "updated_at",
        )

    def get_total_changes(self, obj) -> int:
        if hasattr(obj, "total_changes"):
            return obj.total_changes
        return obj.changelog_entries.count()

    def get_published_by_name(self, obj) -> str | None:
        if obj.published_by:
            return obj.published_by.get_full_name() or obj.published_by.username
        return None


class SoftwareVersionDetailSerializer(serializers.ModelSerializer):
    """
    Serializer detallado con entradas de changelog completas y requisitos.
    """

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    changelog_entries = VersionChangelogEntrySerializer(many=True, read_only=True)
    changelog_grouped = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    published_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SoftwareVersion
        fields = (
            "id_version",
            "version",
            "name",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "published_at",
            "description",
            "min_compatible_version",
            "prerequisites",
            "upgrade_instructions",
            "changelog_entries",
            "changelog_grouped",
            "created_by_name",
            "published_by_name",
            "created_at",
            "updated_at",
        )

    def get_created_by_name(self, obj) -> str | None:
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_published_by_name(self, obj) -> str | None:
        if obj.published_by:
            return obj.published_by.get_full_name() or obj.published_by.username
        return None

    def get_changelog_grouped(self, obj) -> dict:
        grouped = {}
        for entry in obj.changelog_entries.all():
            cat = entry.category
            if cat not in grouped:
                grouped[cat] = {
                    "category": cat,
                    "category_display": entry.get_category_display(),
                    "entries": [],
                }
            grouped[cat]["entries"].append({
                "id_entry": entry.id_entry,
                "title": entry.title,
                "description": entry.description,
                "order": entry.order,
            })
        return grouped


class ChangelogEntryCreateSerializer(serializers.Serializer):
    """
    Serializer para agregar una entrada de changelog a una versión.
    """

    category = serializers.ChoiceField(
        choices=VersionChangelogEntry.Category.choices,
        required=True,
    )
    title = serializers.CharField(
        max_length=255,
        required=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    order = serializers.IntegerField(
        required=False,
        default=0,
    )

    def to_dto(self) -> ChangelogEntryDto:
        return ChangelogEntryDto(
            category=self.validated_data["category"],
            title=self.validated_data["title"],
            description=self.validated_data.get("description", ""),
            order=self.validated_data.get("order", 0),
        )


class SoftwareVersionCreateSerializer(serializers.Serializer):
    """
    Serializer para registrar una nueva versión del software en borrador.
    """

    version = serializers.CharField(max_length=20, required=True)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(
        choices=SoftwareVersion.Priority.choices,
        default=SoftwareVersion.Priority.RECOMMENDED,
        required=False,
    )
    min_compatible_version = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )
    prerequisites = serializers.CharField(required=False, allow_blank=True, default="")
    upgrade_instructions = serializers.CharField(required=False, allow_blank=True, default="")
    changelog_entries = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )

    def validate_version(self, value: str) -> str:
        norm_v = value.strip()
        if not SoftwareVersion.SEMVER_REGEX.match(norm_v):
            raise serializers.ValidationError(
                f"El formato '{value}' no es un SemVer válido (ejemplo: 1.2.0)."
            )
        return norm_v

    def to_dto(self) -> SoftwareVersionCreateDto:
        return SoftwareVersionCreateDto(
            version=self.validated_data["version"],
            name=self.validated_data.get("name", ""),
            description=self.validated_data.get("description", ""),
            priority=self.validated_data.get("priority", SoftwareVersion.Priority.RECOMMENDED),
            min_compatible_version=self.validated_data.get("min_compatible_version", ""),
            prerequisites=self.validated_data.get("prerequisites", ""),
            upgrade_instructions=self.validated_data.get("upgrade_instructions", ""),
            changelog_entries=self.validated_data.get("changelog_entries", []),
        )


class SoftwareVersionUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar una versión en borrador.
    """

    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=SoftwareVersion.Priority.choices, required=False
    )
    min_compatible_version = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    prerequisites = serializers.CharField(required=False, allow_blank=True)
    upgrade_instructions = serializers.CharField(required=False, allow_blank=True)

    def to_dto(self) -> SoftwareVersionUpdateDto:
        return SoftwareVersionUpdateDto(
            name=self.validated_data.get("name"),
            description=self.validated_data.get("description"),
            priority=self.validated_data.get("priority"),
            min_compatible_version=self.validated_data.get("min_compatible_version"),
            prerequisites=self.validated_data.get("prerequisites"),
            upgrade_instructions=self.validated_data.get("upgrade_instructions"),
        )


class PublishVersionSerializer(serializers.Serializer):
    """
    Serializer para confirmar la publicación de una versión.
    """

    force = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Fuerza la publicación aun si la versión no es superior a la última publicada.",
    )
    force_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Motivo justificado para forzar la publicación.",
    )

    def validate(self, attrs):
        if attrs.get("force") and not attrs.get("force_reason", "").strip():
            raise serializers.ValidationError(
                {"force_reason": "Debe especificar un motivo si fuerza la publicación."}
            )
        return attrs


class WithdrawVersionSerializer(serializers.Serializer):
    """
    Serializer para retirar una versión publicada.
    """

    reason = serializers.CharField(
        required=True,
        min_length=5,
        help_text="Motivo del retiro de la versión.",
    )
