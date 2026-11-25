import re
from typing import Tuple

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.models.company_sequence import CompanySequence


class CompanySequenceService:
    """
    Servicio encargado de la asignación transaccional y concurrente de consecutivos
    empresariales independientes (para Ventas, Facturas, Compras, etc.).

    Utiliza bloqueos pesimistas a nivel de fila (SELECT FOR UPDATE) dentro de una
    transacción atómica para evitar colisiones de numeración (Race Conditions)
    garantizando unicidad por empresa.
    """

    @classmethod
    @transaction.atomic
    def get_next_number(
        cls,
        company_id: int,
        document_type: str = CompanySequence.DocumentType.SALE,
        prefix: str = "VTA",
        padding: int = 6,
    ) -> Tuple[int, str]:
        """
        Obtiene e incrementa atómicamente el siguiente consecutivo para la empresa y tipo de documento.

        Retorna:
            tuple: (int: siguiente número entero, str: código formateado ej. 'VTA-000001')
        """
        if not company_id:
            raise ValidationError(
                "No se puede generar un consecutivo sin una empresa activa (company_id no válido)."
            )

        # 1. Bloqueo de fila exclusivo para la empresa y tipo de documento
        sequence = (
            CompanySequence.objects.select_for_update()
            .filter(company_id=company_id, document_type=document_type)
            .first()
        )

        if not sequence:
            # Inicializar contador respetando consecutivos históricos existentes
            initial_count = cls._calculate_initial_seed(
                company_id, document_type, prefix
            )

            sequence, _ = CompanySequence.objects.select_for_update().get_or_create(
                company_id=company_id,
                document_type=document_type,
                defaults={
                    "prefix": prefix,
                    "current_number": initial_count,
                    "padding": padding,
                },
            )

        # 2. Incrementar número de forma atómica
        sequence.current_number += 1
        sequence.save(update_fields=["current_number", "updated_at"])

        formatted_number = (
            f"{sequence.prefix}-{sequence.current_number:0{sequence.padding}d}"
        )
        return sequence.current_number, formatted_number

    @classmethod
    def _calculate_initial_seed(
        cls,
        company_id: int,
        document_type: str,
        prefix: str,
    ) -> int:
        """
        Determina el número base inicial inspeccionando registros existentes
        para no colisionar con numeraciones históricas previas a esta migración.
        """
        if document_type == CompanySequence.DocumentType.SALE:
            from apps.sales.models.sale import Sale

            # Buscar todas las ventas históricas de la empresa
            existing_numbers = list(
                Sale.all_objects.filter(company_id=company_id).values_list(
                    "sale_number", flat=True
                )
                if hasattr(Sale, "all_objects")
                else Sale.objects.filter(company_id=company_id).values_list(
                    "sale_number", flat=True
                )
            )

            pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
            max_num = 0
            for s_num in existing_numbers:
                if not s_num:
                    continue
                match = pattern.match(str(s_num).strip())
                if match:
                    try:
                        val = int(match.group(1))
                        if val > max_num:
                            max_num = val
                    except (ValueError, TypeError):
                        pass

            return max_num

        return 0
