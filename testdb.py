# use requests to get data from the database as a test
import requests

def test_signup():
    response = requests.post("http://localhost:3030/signup", json={"username": "test", "auth0_feedback": "test"})
    assert response.json() == {"message": "Signup successful"}

    response = requests.post("http://localhost:3030/signup", json={"username": "test", "auth0_feedback": "test"})
    assert response.json() == {"message": "Signup failed"}