#!/usr/bin/env python
"""
Test script for property filtering functionality.
This script tests the property filtering API with various filter combinations.
"""

import requests
import json
from pprint import pprint

# Base URL for the API
BASE_URL = "http://localhost:8000/api/properties/"

def test_property_filters():
    """Test various property filter combinations"""
    
    # Test 1: Basic search without filters
    print("\n=== Test 1: Basic search without filters ===")
    response = requests.get(BASE_URL)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    print(f"Total Pages: {data.get('total_pages', 0)}")
    
    # Test 2: Filter by property type
    print("\n=== Test 2: Filter by property type (apartment) ===")
    params = {"search.property_type": "apartment"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # Test 3: Filter by bedrooms (2+)
    print("\n=== Test 3: Filter by bedrooms (2+) ===")
    params = {"search.bedrooms": 2}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # Test 4: Filter by price range (100-500)
    print("\n=== Test 4: Filter by price range (100-500) ===")
    params = {"search.price_range": "100-500"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # Test 5: Filter by price range (1000+)
    print("\n=== Test 5: Filter by price range (1000+) ===")
    params = {"search.price_range": "1000-any"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # Test 6: Combined filters (property type + bedrooms + price range)
    print("\n=== Test 6: Combined filters (house + 3+ bedrooms + price 500-1000) ===")
    params = {
        "search.property_type": "house",
        "search.bedrooms": 3,
        "search.price_range": "500-1000"
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # Test 7: Search by location/query
    print("\n=== Test 7: Search by location (Kigali) ===")
    params = {"search.query": "Kigali"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # Test 8: Filter by city
    print("\n=== Test 8: Filter by city (Kigali) ===")
    params = {"search.city": "Kigali"}
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    print(f"Status Code: {response.status_code}")
    print(f"Total Properties: {data.get('total', 0)}")
    
    # If there are results, print the first property details
    if data.get('total', 0) > 0 and data.get('results'):
        print("\nSample Property Details:")
        property_data = data['results'][0]
        print(f"ID: {property_data.get('id')}")
        print(f"Title: {property_data.get('title')}")
        print(f"Type: {property_data.get('property_type')}")
        print(f"City: {property_data.get('city')}")
        print(f"Bedrooms: {property_data.get('bedrooms')}")
        print(f"Price: ${property_data.get('price_per_night')}")

if __name__ == "__main__":
    test_property_filters()
