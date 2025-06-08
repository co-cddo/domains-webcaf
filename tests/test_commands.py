from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import User
from webcaf.webcaf.models import UserProfile, Organisation, System


class CreateUsersCommandTest(TestCase):

    def test_command_creates_users_when_none_exist(self):
        call_command('add_seed_data')
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(UserProfile.objects.count(), 2)
        superuser = User.objects.get(username='admin')
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)      
        user = User.objects.get(username='user')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        
    def test_command_handles_existing_users(self):
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        UserProfile.objects.create(user=superuser)        
        user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='password'
        )       
        UserProfile.objects.create(user=user)     
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(UserProfile.objects.count(), 2) 
        call_command('add_seed_data')
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(UserProfile.objects.count(), 2)

    def test_command_creates_organisation(self):
        self.assertEqual(Organisation.objects.count(), 0)
        call_command('add_seed_data')
        self.assertEqual(Organisation.objects.count(), 1)
        
        org = Organisation.objects.first()
        self.assertEqual(org.name, 'An Organisation')
        
        user = User.objects.get(username='user')
        user_profile = UserProfile.objects.get(user=user)
        self.assertEqual(user_profile.organisation, org)
        
    def test_command_creates_systems(self):
        self.assertEqual(System.objects.count(), 0)
        call_command('add_seed_data')
        self.assertEqual(System.objects.count(), 2)
        
        org = Organisation.objects.first()
        systems = System.objects.all()
        
        system_names = [system.name for system in systems]
        self.assertIn('Big System', system_names)
        self.assertIn('Little System', system_names)
        
        for system in systems:
            self.assertEqual(system.organisation, org)
