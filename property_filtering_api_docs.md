# Property Filtering API Documentation

## Frontend Request Examples

Here are examples of how to make requests from your frontend to the backend API for property filtering:

### Basic API Endpoint

```
GET http://localhost:8000/api/properties/
```

### Request Parameters

| Parameter | Format | Description | Example |
|-----------|--------|-------------|---------|
| `search.query` | String | Search across title, description, address, city | `search.query=Kigali` |
| `search.property_type` | String | Filter by property type | `search.property_type=apartment` |
| `search.bedrooms` | Integer | Filter by minimum number of bedrooms (X+) | `search.bedrooms=2` |
| `search.price_range` | String | Filter by price range in format "min-max" | `search.price_range=100-500` |
| `search.city` | String | Filter by city | `search.city=Kigali` |
| `page` | Integer | Page number for pagination | `page=1` |
| `page_size` | Integer | Number of results per page | `page_size=10` |

### Example Requests

#### 1. Basic search without filters
```
GET http://localhost:8000/api/properties/
```

#### 2. Filter by property type
```
GET http://localhost:8000/api/properties/?search.property_type=apartment
```

#### 3. Filter by bedrooms (2+)
```
GET http://localhost:8000/api/properties/?search.bedrooms=2
```

#### 4. Filter by price range (100-500)
```
GET http://localhost:8000/api/properties/?search.price_range=100-500
```

#### 5. Filter by price range (1000+)
```
GET http://localhost:8000/api/properties/?search.price_range=1000-any
```

#### 6. Combined filters
```
GET http://localhost:8000/api/properties/?search.property_type=house&search.bedrooms=3&search.price_range=500-1000
```

#### 7. Search by location/query
```
GET http://localhost:8000/api/properties/?search.query=Kigali
```

## Response Format

```json
{
  "total": 15,
  "page": 1,
  "page_size": 10,
  "total_pages": 2,
  "results": [
    {
      "id": 1,
      "title": "Modern Apartment in Kigali",
      "property_type": "apartment",
      "status": "approved",
      "document_verification_status": "verified",
      "owner": {
        "id": 2,
        "username": "landlord1",
        "first_name": "John",
        "last_name": "Doe",
        "name": "John Doe"
      },
      "city": "Kigali",
      "state": "Kigali Province",
      "country": "Rwanda",
      "bedrooms": 2,
      "bathrooms": 1.5,
      "price_per_night": 120.00,
      "primary_image": "http://localhost:8000/media/properties/images/apartment1.jpg",
      "images": [
        {
          "id": 1,
          "url": "http://localhost:8000/media/properties/images/apartment1.jpg",
          "caption": "Living Room",
          "is_primary": true
        }
      ],
      "created_at": "2023-06-15T10:30:00Z"
    }
  ]
}
```

## Available Property Types

- `apartment`
- `house`
- `villa`
- `studio`
- `compound`
- `bungalow`

## Available Price Ranges

- `0-100`: $0 - $100
- `100-200`: $100 - $200
- `200-500`: $200 - $500
- `500-1000`: $500 - $1000
- `1000-any`: $1000+

## Available Bedroom Options

- `1`: 1+ bedrooms
- `2`: 2+ bedrooms
- `3`: 3+ bedrooms
- `4`: 4+ bedrooms
- `5`: 5+ bedrooms
