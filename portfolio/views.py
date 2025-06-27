from django.shortcuts import render, redirect
from django.conf import settings
from .models import Profile, Project, Skill
from .forms import ResumeUploadForm
import PyPDF2
import os
import re

def portfolio_view(request):
    profile = Profile.objects.first()  # Assuming only one profile for a personal portfolio
    projects = Project.objects.all()
    skills = Skill.objects.all()
    context = {
        'profile': profile,
        'projects': projects,
        'skills': skills,
    }
    return render(request, 'portfolio/portfolio.html', context)

def parse_resume(text):
    parsed_data = {
        'profile': {},
        'projects': [],
        'skills': []
    }

    # --- Profile Information ---
    # Name (simple regex, assumes name is at the beginning or prominent)
    name_match = re.search(r'^[A-Z][a-z]+(?: [A-Z][a-z]+){1,2}', text, re.MULTILINE)
    if name_match:
        parsed_data['profile']['name'] = name_match.group(0).strip()

    # Email
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    if email_match:
        parsed_data['profile']['email'] = email_match.group(0)

    # LinkedIn
    linkedin_match = re.search(r'(https?://www\.linkedin\.com/in/[\w-]+)', text)
    if linkedin_match:
        parsed_data['profile']['linkedin'] = linkedin_match.group(0)

    # GitHub
    github_match = re.search(r'(https?://github\.com/[\w-]+)', text)
    if github_match:
        parsed_data['profile']['github'] = github_match.group(0)

    # About/Summary (very basic, looks for common section headers)
    about_match = re.search(r'(?:SUMMARY|ABOUT ME|PROFILE)\s*\n([\s\S]+?)(?=\n(?:EDUCATION|EXPERIENCE|SKILLS|PROJECTS|$))', text, re.IGNORECASE)
    if about_match:
        parsed_data['profile']['about'] = about_match.group(1).strip()

    # --- Skills ---
    skills_section_match = re.search(r'(?:SKILLS|TECHNICAL SKILLS)\s*\n([\s\S]+?)(?=\n(?:EDUCATION|EXPERIENCE|PROJECTS|$))', text, re.IGNORECASE)
    if skills_section_match:
        skills_text = skills_section_match.group(1)
        # Split by common delimiters like commas, newlines, or bullet points
        skills_list = re.split(r'[,•\n-]\s*', skills_text)
        # Clean up and add to parsed data
        for skill in skills_list:
            skill = skill.strip()
            if skill and len(skill) < 50: # Basic length check to avoid parsing errors
                parsed_data['skills'].append({'name': skill})

    # --- Projects (more complex, requires pattern matching for title, description, URL) ---
    # This is a very simplified project extraction. Real-world parsing is much harder.
    # It looks for "PROJECTS" section and then tries to find lines that might be project titles.
    projects_section_match = re.search(r'(?:PROJECTS)\s*\n([\s\S]+?)(?=\n(?:EDUCATION|EXPERIENCE|SKILLS|$))', text, re.IGNORECASE)
    if projects_section_match:
        projects_text = projects_section_match.group(1)
        # Split by lines that might indicate a new project (e.g., bolded text, all caps)
        project_entries = re.split(r'\n(?=[A-Z][A-Z\s]+(?:\n|$))', projects_text) # Looks for new line followed by all caps
        
        for entry in project_entries:
            entry = entry.strip()
            if not entry:
                continue
            
            title_match = re.match(r'([^\n]+)', entry)
            if title_match:
                title = title_match.group(1).strip()
                description = entry[len(title):].strip() # Rest of the entry is description
                url_match = re.search(r'(https?://[^\s]+)', description)
                url = url_match.group(0) if url_match else None
                
                # Clean description by removing URL if found
                if url:
                    description = description.replace(url, '').strip()

                parsed_data['projects'].append({
                    'title': title,
                    'description': description,
                    'url': url
                })

    return parsed_data

def upload_resume_view(request):
    extracted_text = ""
    parsed_data = {}
    db_update_status = "No resume uploaded or processed."

    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume_file = request.FILES['resume_file']
            file_path = os.path.join(settings.MEDIA_ROOT, 'resumes', resume_file.name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb+') as destination:
                for chunk in resume_file.chunks():
                    destination.write(chunk)

            if resume_file.name.endswith('.pdf'):
                try:
                    with open(file_path, 'rb') as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        for page_num in range(len(reader.pages)):
                            page = reader.pages[page_num]
                            extracted_text += page.extract_text() + "\n"
                    
                    # --- Phase 2: Parse and Update DB ---
                    parsed_data = parse_resume(extracted_text)
                    
                    try:
                        # Update Profile
                        profile_data = parsed_data.get('profile', {})
                        if profile_data:
                            profile, created = Profile.objects.get_or_create(pk=1) # Assuming single profile
                            profile.name = profile_data.get('name', profile.name)
                            profile.email = profile_data.get('email', profile.email)
                            profile.linkedin = profile_data.get('linkedin', profile.linkedin)
                            profile.github = profile_data.get('github', profile.github)
                            profile.about = profile_data.get('about', profile.about)
                            profile.save()
                            db_update_status = "Profile updated. "
                        else:
                            db_update_status = "No profile data extracted. "

                        # Add Skills (clear existing and add new ones from resume)
                        if parsed_data.get('skills'):
                            Skill.objects.all().delete() # Clear existing skills
                            for skill_data in parsed_data['skills']:
                                Skill.objects.create(**skill_data)
                            db_update_status += "Skills updated. "
                        else:
                            db_update_status += "No skills extracted. "

                        # Add Projects (clear existing and add new ones from resume)
                        if parsed_data.get('projects'):
                            Project.objects.all().delete() # Clear existing projects
                            for project_data in parsed_data['projects']:
                                Project.objects.create(**project_data)
                            db_update_status += "Projects updated."
                        else:
                            db_update_status += "No projects extracted."

                        db_update_status = "Database updated successfully based on resume data."

                    except Exception as db_e:
                        db_update_status = f"Error updating database: {db_e}"

                except Exception as e:
                    extracted_text = f"Error extracting text: {e}"
                    db_update_status = "Text extraction failed, no database update."
            else:
                extracted_text = "Only PDF files are supported for text extraction at the moment."
                db_update_status = "Unsupported file type, no database update."
    else:
        form = ResumeUploadForm()

    return render(request, 'portfolio/resume_analysis_result.html', {
        'form': form,
        'extracted_text': extracted_text,
        'parsed_data': parsed_data,
        'db_update_status': db_update_status
    })
