from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Login.models import Profile


class Command(BaseCommand):
    help = 'Create profiles for users who do not have one'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(profile__isnull=True)
        created_count = 0
        
        for user in users_without_profile:
            profile, created = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'email': user.email or '',
                    'user_status': 'user',
                    'phone': '',
                    'address': 'Please update your profile information.'
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created profile for user: {user.username}')
                )
        
        if created_count == 0:
            self.stdout.write(
                self.style.SUCCESS('All users already have profiles.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} profiles.')
            )