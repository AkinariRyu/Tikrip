# downloader/views.py
from django.shortcuts import render, redirect
from .forms import CustomUserCreationForm 
from .models import DownloadHistory 
from django.contrib.auth.decorators import login_required 

def register_view(request):
    if request.user.is_authenticated:
        return redirect('cabinet')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login') 
    else:
        form = CustomUserCreationForm()
    return render(request, 'downloader/register.html', {'form': form})

def home_view(request):
    return render(request, 'downloader/home.html')

@login_required
def cabinet_view(request):
    history = DownloadHistory.objects.filter(user=request.user).order_by('-download_date')
    context = {
        'history': history
    }
    return render(request, 'downloader/cabinet.html', context)