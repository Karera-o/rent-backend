from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from ninja_jwt.tokens import RefreshToken

User = get_user_model()

class UserAPITestCase(TestCase):
    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password123',
            role=User.Role.ADMIN,
            is_staff=True
        )
        
        self.agent_user = User.objects.create_user(
            username='agent',
            email='agent@example.com',
            password='password123',
            role=User.Role.AGENT
        )
        
        self.tenant_user = User.objects.create_user(
            username='tenant',
            email='tenant@example.com',
            password='password123',
            role=User.Role.TENANT
        )
        
        # Set up API client
        self.client = APIClient()
    
    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    
    def test_user_registration(self):
        """Test user registration endpoint"""
        url = '/api/users/register'
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'password123',
            'first_name': 'New',
            'last_name': 'User',
            'role': User.Role.TENANT
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.count(), 4)  # 3 from setup + 1 new
        self.assertEqual(User.objects.get(username='newuser').email, 'newuser@example.com')
    
    def test_user_login(self):
        """Test user login and token generation"""
        url = '/api/token/'
        data = {
            'username': 'tenant',
            'password': 'password123'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_get_user_profile(self):
        """Test getting user profile"""
        # Get token for tenant user
        tokens = self.get_tokens_for_user(self.tenant_user)
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        url = '/api/users/profile'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'tenant')
        self.assertEqual(response.data['email'], 'tenant@example.com')
        self.assertEqual(response.data['role'], User.Role.TENANT)
    
    def test_update_user_profile(self):
        """Test updating user profile"""
        # Get token for tenant user
        tokens = self.get_tokens_for_user(self.tenant_user)
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        url = '/api/users/profile'
        data = {
            'first_name': 'Updated',
            'last_name': 'User',
            'phone_number': '1234567890'
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'User')
        self.assertEqual(response.data['phone_number'], '1234567890')
        
        # Verify database was updated
        updated_user = User.objects.get(id=self.tenant_user.id)
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'User')
        self.assertEqual(updated_user.phone_number, '1234567890')
    
    def test_change_password(self):
        """Test changing user password"""
        # Get token for tenant user
        tokens = self.get_tokens_for_user(self.tenant_user)
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        url = '/api/users/change-password'
        data = {
            'old_password': 'password123',
            'new_password': 'newpassword123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Password changed successfully')
        
        # Verify password was changed by trying to login with new password
        login_url = '/api/token/'
        login_data = {
            'username': 'tenant',
            'password': 'newpassword123'
        }
        
        login_response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(login_response.status_code, 200)
        self.assertIn('access', login_response.data)
