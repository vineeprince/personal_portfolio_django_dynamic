from django import forms

class ResumeUploadForm(forms.Form):
    resume_file = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control'}))