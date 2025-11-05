"""
Custom middleware to handle session issues during database restoration
"""

class SessionSafeMiddleware:
    """
    Middleware to handle session saving issues during database restoration
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if this is a session-safe response
        if hasattr(response, 'get') and response.get('X-No-Session-Save'):
            # Prevent session from being saved
            if hasattr(request, 'session'):
                request.session.modified = False
                request.session.accessed = False
                # Mark the session as not needing to be saved
                request.session._session_key = None
                
        return response

    def process_exception(self, request, exception):
        """
        Handle exceptions that might be related to session table issues
        """
        exception_str = str(exception).lower()
        
        # Check if this is a session-related database error
        if 'django_session' in exception_str and 'does not exist' in exception_str:
            print(f"Session table error caught by middleware: {exception}")
            
            # Clear session data to prevent further errors
            if hasattr(request, 'session'):
                try:
                    request.session.clear()
                    request.session.modified = False
                    request.session.accessed = False
                except:
                    pass
            
            # Import here to avoid circular imports
            from django.shortcuts import redirect
            from django.contrib import messages
            
            # Add a message and redirect
            try:
                messages.info(request, "Database session error detected. System is recovering...")
                return redirect('/user/backups/')
            except:
                # If even this fails, return a simple HTTP response
                from django.http import HttpResponse
                return HttpResponse("Database session error. Please refresh the page.", status=200)
        
        # Let other exceptions pass through
        return None