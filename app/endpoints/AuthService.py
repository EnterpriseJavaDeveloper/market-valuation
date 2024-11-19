from datetime import datetime, timedelta

import jwt
from flask import jsonify
from werkzeug.security import check_password_hash

from flask import current_app

from app.models.Users import Users

# users = {
#     "user1": "password_hash1",
#     "user2": "password_hash2",
#     "admin": "scrypt:32768:8:1$nv9gU8x896vs2XzC$eef85636aa11bfd10db14b7696e0e587c8bc02bb4cbdb8e8f90a416405550ea5ee453320ffb8ea1ea443e9f9c3b7e6251721604800720a68b2e69d3c7be811e1"}


class AuthService:

    @staticmethod
    def generate_token(username, email):
        payload = {
            'exp': datetime.utcnow() + timedelta(hours=1),
            'iat': datetime.utcnow(),
            'sub': username,
            'email': email
        }
        return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    @staticmethod
    def login(data):
        username = data.get('username')
        password = data.get('password')

        user = Users.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):

        # if username in users and check_password_hash(users[username], password):
            email = "user@example.com"  # Replace with actual email retrieval logic
            token = AuthService.generate_token(username, email)
            return jsonify({'token': token})

        return jsonify({'message': 'Invalid credentials'}), 401