from rest_framework import status
from rest_framework.views import APIView

from apps.core.security import HasPermission
from apps.core.views.base_viewset import BaseResponseMixin
from apps.finance.docs.finance_docs import finance_dashboard_schema
from apps.finance.selectors.finance_dashboard_selector import FinanceDashboardSelector
from apps.users.permissions import IsAuthenticatedAndActive


class FinanceDashboardView(BaseResponseMixin, APIView):
    """
    Vista de API para el Dashboard Consolidado de Tesorería y Métricas Financieras.
    """

    permission_classes = [IsAuthenticatedAndActive, HasPermission("finance.view")]

    @finance_dashboard_schema
    def get(self, request, *args, **kwargs):
        company_id = request.query_params.get("company_id")
        period = request.query_params.get("period")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        metrics = FinanceDashboardSelector.get_dashboard_metrics(
            company_id=int(company_id) if company_id else None,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

        return self.success_response(
            message="Métricas del dashboard financiero obtenidas exitosamente.",
            code="FINANCE_DASHBOARD_METRICS_FETCHED",
            data=metrics,
            status_code=status.HTTP_200_OK,
        )

