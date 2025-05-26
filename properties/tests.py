from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from ninja_jwt.tokens import RefreshToken
import tempfile
from PIL import Image
import io
import json

from .models import Property, PropertyImage
from .services import PropertyService

User = get_user_model()

class PropertyModelTestCase(TestCase):
    """Tests for the Property model and service layer."""
    
    def setUp(self):
        """Set up test data."""
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
        
        # Initialize service
        self.property_service = PropertyService()
        
        # Create a test property
        self.test_property = self.property_service.create_property(
            owner=self.agent_user,
            title="Test Property",
            description="A test property description that is long enough to pass validation",
            property_type=Property.PropertyType.APARTMENT,
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Test Country",
            zip_code="12345",
            bedrooms=2,
            bathrooms=1.5,
            area=1000,
            price_per_night=100.00,
            has_wifi=True,
            has_kitchen=True
        )
    
    def test_property_creation(self):
        """Test property creation."""
        self.assertEqual(self.test_property.title, "Test Property")
        self.assertEqual(self.test_property.owner, self.agent_user)
        self.assertEqual(self.test_property.property_type, Property.PropertyType.APARTMENT)
        self.assertEqual(self.test_property.status, Property.PropertyStatus.PENDING)
        self.assertEqual(self.test_property.bedrooms, 2)
        self.assertEqual(self.test_property.bathrooms, 1.5)
        self.assertEqual(self.test_property.price_per_night, 100.00)
        self.assertTrue(self.test_property.has_wifi)
        self.assertTrue(self.test_property.has_kitchen)
    
    def test_property_update(self):
        """Test property update."""
        updated_property = self.property_service.update_property(
            property_id=self.test_property.id,
            owner=self.agent_user,
            title="Updated Property",
            price_per_night=150.00
        )
        
        self.assertEqual(updated_property.title, "Updated Property")
        self.assertEqual(updated_property.price_per_night, 150.00)
        
        # Other fields should remain unchanged
        self.assertEqual(updated_property.bedrooms, 2)
        self.assertEqual(updated_property.bathrooms, 1.5)
    
    def test_property_permissions(self):
        """Test property permissions."""
        # Tenant should not be able to create a property
        with self.assertRaises(ValueError):
            self.property_service.create_property(
                owner=self.tenant_user,
                title="Tenant Property",
                description="A test property description",
                property_type=Property.PropertyType.APARTMENT,
                address="123 Test Street",
                city="Test City",
                state="Test State",
                country="Test Country",
                zip_code="12345",
                bedrooms=2,
                bathrooms=1.5,
                area=1000,
                price_per_night=100.00
            )
        
        # Tenant should not be able to update another user's property
        with self.assertRaises(ValueError):
            self.property_service.update_property(
                property_id=self.test_property.id,
                owner=self.tenant_user,
                title="Tenant Updated Property"
            )
        
        # Admin should be able to update any property
        updated_property = self.property_service.update_property(
            property_id=self.test_property.id,
            owner=self.admin_user,
            status=Property.PropertyStatus.APPROVED
        )
        
        self.assertEqual(updated_property.status, Property.PropertyStatus.APPROVED)


class PropertyAPITestCase(TestCase):
    """Tests for the Property API endpoints."""
    
    def setUp(self):
        """Set up test data."""
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
        
        # Create a test property
        self.property_service = PropertyService()
        self.test_property = self.property_service.create_property(
            owner=self.agent_user,
            title="Test Property",
            description="A test property description that is long enough to pass validation",
            property_type=Property.PropertyType.APARTMENT,
            address="123 Test Street",
            city="Test City",
            state="Test State",
            country="Test Country",
            zip_code="12345",
            bedrooms=2,
            bathrooms=1.5,
            area=1000,
            price_per_night=100.00,
            has_wifi=True,
            has_kitchen=True
        )
        
        # Approve the property
        self.test_property.status = Property.PropertyStatus.APPROVED
        self.test_property.save()
    
    def get_tokens_for_user(self, user):
        """Get JWT tokens for a user."""
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    
    def test_get_property_list(self):
        """Test getting property list."""
        url = '/api/properties/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['title'], "Test Property")
    
    def test_get_property_detail(self):
        """Test getting property detail."""
        url = f'/api/properties/{self.test_property.id}'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], "Test Property")
        self.assertEqual(data['bedrooms'], 2)
        self.assertEqual(data['bathrooms'], '1.5')
        self.assertEqual(data['price_per_night'], '100.00')
    
    def test_create_property(self):
        """Test creating a property."""
        # Get token for agent user
        tokens = self.get_tokens_for_user(self.agent_user)
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        url = '/api/properties/'
        data = {
            'title': 'New Property',
            'description': 'A new property description that is long enough to pass validation',
            'property_type': Property.PropertyType.HOUSE,
            'address': '456 New Street',
            'city': 'New City',
            'state': 'New State',
            'country': 'New Country',
            'zip_code': '54321',
            'bedrooms': 3,
            'bathrooms': 2.0,
            'area': 1500,
            'price_per_night': 150.00,
            'has_wifi': True,
            'has_parking': True
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'New Property')
        self.assertEqual(data['bedrooms'], 3)
        self.assertEqual(data['bathrooms'], '2.0')
        self.assertEqual(data['price_per_night'], '150.00')
        
        # Verify database was updated
        self.assertEqual(Property.objects.count(), 2)
    
    def test_update_property(self):
        """Test updating a property."""
        # Get token for agent user
        tokens = self.get_tokens_for_user(self.agent_user)
        
        # Set authorization header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')
        
        url = f'/api/properties/{self.test_property.id}'
        data = {
            'title': 'Updated Property',
            'price_per_night': 200.00
        }
        
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['title'], 'Updated Property')
        self.assertEqual(data['price_per_night'], '200.00')
        
        # Verify database was updated
        updated_property = Property.objects.get(id=self.test_property.id)
        self.assertEqual(updated_property.title, 'Updated Property')
        self.assertEqual(updated_property.price_per_night, 200.00)

    def test_search_properties_query(self):
        """Test searching properties by query (title, address, city, state)."""
        # Add another property with different fields
        kigali_villa = self.property_service.create_property(
            owner=self.agent_user,
            title="Kigali Villa",
            description="A beautiful villa in Kigali.",
            property_type=Property.PropertyType.VILLA,
            address="456 Kigali Road",
            city="Kigali",
            state="Kigali Province",
            country="Rwanda",
            zip_code="00001",
            bedrooms=4,
            bathrooms=3.0,
            area=2000,
            price_per_night=300.00,
            has_wifi=True,
            has_kitchen=True
        )
        # Ensure property is approved so it appears in search results
        kigali_villa.status = Property.PropertyStatus.APPROVED
        kigali_villa.save()
        # Search by title
        response = self.client.get('/api/properties/', {'query': 'Kigali Villa'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(any(prop['title'] == 'Kigali Villa' for prop in data['results']))
        # Search by address
        response = self.client.get('/api/properties/', {'query': 'Kigali Road'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(any(prop['address'] == '456 Kigali Road' for prop in data['results']))
        # Search by city
        response = self.client.get('/api/properties/', {'query': 'Kigali'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(any('Kigali' in prop['city'] for prop in data['results']))
        # Search by state
        response = self.client.get('/api/properties/', {'query': 'Kigali Province'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(any('Kigali Province' in prop['state'] for prop in data['results']))
