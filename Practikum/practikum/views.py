from django.shortcuts import render


def curs(request):
    return render(request, 'curs/curs.html')
