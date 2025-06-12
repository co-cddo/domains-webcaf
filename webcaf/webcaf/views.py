from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView

from .forms import TutorialForm

class Index(TemplateView):
    template_name = "index.html"

class TutorialView(FormView):
    template_name = "tutorial.html"
    form_class = TutorialForm
    success_url = reverse_lazy("index")
