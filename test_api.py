#!/usr/bin/env python3
"""
Test script using FastAPI TestClient to verify endpoints are working correctly.
"""
from fastapi.testclient import TestClient
from fastapi_playground_poc.app import app

# Create test client
client = TestClient(app)


def test_api():
    print("🧪 Testing FastAPI User Management Endpoints")
    print("=" * 50)

    # Test 1: GET /users (should return empty list initially)
    print("\n1️⃣ Testing GET /users (get all users)")
    response = client.get("/users")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    users = response.json()
    print("   ✅ GET /users works correctly")

    # Test 2: POST /user (create a new user)
    print("\n2️⃣ Testing POST /user (create user)")
    user_data = {"name": "John Doe"}
    response = client.post("/user", json=user_data)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    created_user = response.json()
    assert "id" in created_user
    assert created_user["name"] == "John Doe"
    user_id = created_user["id"]
    print("   ✅ POST /user works correctly")

    # Test 3: GET /user/{user_id} (get specific user)
    print(f"\n3️⃣ Testing GET /user/{user_id} (get specific user)")
    response = client.get(f"/user/{user_id}")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == user_id
    assert user["name"] == "John Doe"
    print("   ✅ GET /user/{user_id} works correctly")

    # Test 4: GET /users (should now return the created user)
    print("\n4️⃣ Testing GET /users again (should show created user)")
    response = client.get("/users")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 1
    # Find our created user
    our_user = next((u for u in users if u["id"] == user_id), None)
    assert our_user is not None
    assert our_user["name"] == "John Doe"
    print("   ✅ GET /users shows created user correctly")

    # Test 5: GET /user/999999 (test error handling for non-existent user)
    print("\n5️⃣ Testing GET /user/999999 (non-existent user)")
    response = client.get("/user/999999")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 404
    error_response = response.json()
    assert "detail" in error_response
    print("   ✅ Error handling works correctly")

    # Test 6: Test root endpoint
    print("\n6️⃣ Testing GET / (root endpoint)")
    response = client.get("/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    assert "message" in response.json()
    print("   ✅ Root endpoint works correctly")

    # Test 7: Test health endpoint
    print("\n7️⃣ Testing GET /health (health check)")
    response = client.get("/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("   ✅ Health endpoint works correctly")

    print("\n🎉 All tests passed! FastAPI application is working correctly.")
    print("\n📋 Summary:")
    print("   ✅ POST /user - Creates users successfully")
    print("   ✅ GET /user/{user_id} - Retrieves specific users")
    print("   ✅ GET /users - Lists all users")
    print("   ✅ GET / - Root endpoint works")
    print("   ✅ GET /health - Health check works")
    print("   ✅ Error handling - Returns 404 for non-existent users")


if __name__ == "__main__":
    test_api()
