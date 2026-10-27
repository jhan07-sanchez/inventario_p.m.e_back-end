from django.core.management.base import BaseCommand

from apps.configuration.models import GlobalParameter


class Command(BaseCommand):
    help = "Pobla la base de datos con los parámetros globales por defecto."

    def handle(self, *args, **options):
        self.stdout.write("Inicializando parámetros globales...")

        parametros = [
            # --- PUNTO 2: Usuarios y Seguridad ---
            {
                "key": "SECURITY_PASSWORD_MIN_LENGTH",
                "value": "8",
                "data_type": GlobalParameter.DataType.INTEGER,
                "description": "Longitud mínima de las contraseñas de usuario.",
            },
            {
                "key": "SECURITY_SESSION_TIMEOUT_MINUTES",
                "value": "60",
                "data_type": GlobalParameter.DataType.INTEGER,
                "description": "Minutos de inactividad antes de cerrar sesión.",
            },
            {
                "key": "SECURITY_MAX_LOGIN_ATTEMPTS",
                "value": "5",
                "data_type": GlobalParameter.DataType.INTEGER,
                "description": "Intentos fallidos antes de bloquear la cuenta.",
            },
            # --- PUNTO 3: Parámetros de Inventario ---
            {
                "key": "INVENTORY_ALLOW_NEGATIVE_STOCK",
                "value": "false",
                "data_type": GlobalParameter.DataType.BOOLEAN,
                "description": "Permitir ventas si el stock llega a cero.",
            },
            {
                "key": "INVENTORY_DEFAULT_LOW_STOCK_ALERT",
                "value": "5",
                "data_type": GlobalParameter.DataType.INTEGER,
                "description": "Cantidad por defecto para alertar bajo stock.",
            },
            # --- PUNTO 4: Preferencias del Sistema ---
            {
                "key": "SYSTEM_DEFAULT_CURRENCY",
                "value": "COP",
                "data_type": GlobalParameter.DataType.STRING,
                "description": "Código ISO de la moneda principal de la empresa.",
            },
            {
                "key": "SYSTEM_DEFAULT_TAX_RATE",
                "value": "0.19",
                "data_type": GlobalParameter.DataType.DECIMAL,
                "description": "Porcentaje de IVA por defecto (ej. 0.19 para 19%).",
            },
            {
                "key": "SYSTEM_DATE_FORMAT",
                "value": "DD/MM/YYYY",
                "data_type": GlobalParameter.DataType.STRING,
                "description": "Formato de visualización de fechas en el sistema.",
            },
            {
                "key": "SYSTEM_ITEMS_PER_PAGE",
                "value": "10",
                "data_type": GlobalParameter.DataType.INTEGER,
                "description": "Cantidad de registros por página en las tablas.",
            },
            {
                "key": "SYSTEM_THEME",
                "value": "light",
                "data_type": GlobalParameter.DataType.STRING,
                "description": "Tema visual del sistema (light / dark).",
            },
        ]

        for p in parametros:
            obj, created = GlobalParameter.objects.get_or_create(
                key=p["key"],
                defaults={
                    "value": p["value"],
                    "data_type": p["data_type"],
                    "description": p["description"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"✔ Creado: {p['key']}"))
            else:
                self.stdout.write(f"ℹ Ya existía: {p['key']}")

        self.stdout.write(
            self.style.SUCCESS("¡Parámetros inicializados correctamente!")
        )
