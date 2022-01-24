"""
Copyright (c) 2022 Adam Lisichin, Hubert Decyusz, Wojciech Nowicki, Gustaw Daczkowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

author: Hubert Decyusz

description: File registers Examination model and its model admin with custom model form in admin interface.
"""
from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model

from .models import Examination

User = get_user_model()


class ExaminationModelForm(forms.ModelForm):
    """Examination form with filtered doctor and patient choice fields."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # filter doctors and patients
        self.fields['doctor'].queryset = User.objects.doctors()
        self.fields['patient'].queryset = User.objects.patients()

    class Meta:
        model = Examination
        fields = "__all__"


class ExaminationAdmin(admin.ModelAdmin):
    form = ExaminationModelForm


admin.site.register(Examination, ExaminationAdmin)
