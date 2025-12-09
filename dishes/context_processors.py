"""
Context processors to make data available to all templates
"""

def user_location(request):
    """Add user location to all template contexts"""
    location = request.session.get('user_location')
    return {
        'user_location': location
    }
