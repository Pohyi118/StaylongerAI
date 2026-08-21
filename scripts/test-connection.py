"""
Quick test script to verify backend API endpoints are working correctly
"""
import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app, build_dashboard_payload, build_customer_directory

def test_dashboard_data():
    """Test that dashboard data is properly formatted"""
    try:
        data = build_dashboard_payload()
        assert "title" in data
        assert "metrics" in data
        assert "chartData" in data
        assert len(data["metrics"]) == 4
        assert len(data["chartData"]) == 7
        print("✓ Dashboard data structure is valid")
        return True
    except Exception as e:
        print(f"✗ Dashboard data test failed: {e}")
        return False

def test_customer_data():
    """Test that customer data is properly formatted"""
    try:
        data = build_customer_directory()
        assert isinstance(data, list)
        assert len(data) == 7
        assert all("name" in customer for customer in data)
        assert all("health" in customer for customer in data)
        print("✓ Customer data structure is valid")
        return True
    except Exception as e:
        print(f"✗ Customer data test failed: {e}")
        return False

def test_api_endpoints():
    """Test that all API routes are registered"""
    try:
        routes = [route.path for route in app.routes]
        required_routes = ["/", "/health", "/api/dashboard", "/api/customers", "/webhook"]
        
        for route in required_routes:
            if route in routes:
                print(f"✓ Route {route} is registered")
            else:
                print(f"✗ Route {route} is missing")
                return False
        return True
    except Exception as e:
        print(f"✗ API endpoints test failed: {e}")
        return False

def main():
    print("=" * 50)
    print("Backend Connection Test")
    print("=" * 50)
    print()
    
    results = []
    
    print("Testing dashboard data...")
    results.append(test_dashboard_data())
    print()
    
    print("Testing customer data...")
    results.append(test_customer_data())
    print()
    
    print("Testing API endpoints...")
    results.append(test_api_endpoints())
    print()
    
    print("=" * 50)
    if all(results):
        print("✓ All tests passed!")
        print()
        print("To start the servers, run:")
        print("  .\\scripts\\start-dev.bat")
        print()
        print("Or manually:")
        print("  Backend:  cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("  Frontend: cd frontend && npm run dev")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
