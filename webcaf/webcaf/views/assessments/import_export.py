import logging
from io import BytesIO

from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView

from webcaf.webcaf.forms.assessment import ImportAssessmentExcelForm
from webcaf.webcaf.models import Configuration
from webcaf.webcaf.utils.excel_exporter import create_assessment_template_workbook
from webcaf.webcaf.utils.excel_importer import (
    ExcelImportError,
    excel_to_assessment_json,
)
from webcaf.webcaf.utils.permission import UserRoleCheckMixin


class ImportAssessmentExcelView(UserRoleCheckMixin, FormView):
    """
    Allows users to import a CAF Excel file.
    """

    login_url = "/oidc/authenticate/"
    template_name = "assessment/import-excel.html"
    form_class = ImportAssessmentExcelForm
    logger = logging.getLogger("ImportAssessmentExcelView")

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["breadcrumbs"] = [
            {"url": reverse("my-account"), "text": "My account"},
            {"url": "#", "text": "Import CAF Excel file"},
        ]
        return data

    def form_valid(self, form):
        excel_file = form.cleaned_data["excel_file"]

        try:
            excel_to_assessment_json(excel_file)
        except ExcelImportError as ex:
            messages.error(self.request, str(ex))
            return self.form_invalid(form)
        except Exception as ex:
            self.logger.exception("Failed to import assessment Excel file")
            messages.error(self.request, f"Failed to import Excel file: {ex}")
            return self.form_invalid(form)

        messages.success(self.request, "Imported Excel file successfully.")
        return redirect(reverse("my-account"))


class ExportAssessmentTemplateView(UserRoleCheckMixin, View):
    """
    Returns the blank CAF Excel template.
    """

    login_url = "/oidc/authenticate/"

    def get_allowed_roles(self) -> list[str]:
        return ["organisation_lead"]

    def get(self, request, *args, **kwargs):
        configuration = Configuration.objects.get_default_config()
        framework_id = configuration.get_default_framework()
        workbook = create_assessment_template_workbook(framework_id)
        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return FileResponse(
            output,
            as_attachment=True,
            filename=f"{framework_id}-assessment-template.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
