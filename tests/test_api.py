import sys
import os
import pytest
import tempfile
import sqlite3
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as app_module
from app import app as flask_app

from flask import Flask, render_template, request, redirect, session, jsonify, g
import sqlite3
import smtplib
from email.mime.text import MIMEText
import os
import secrets
import time
import hashlib
from datetime import datetime
from dotenv import load_dotenv
import traceback  
import logging  
from logging.handlers import RotatingFileHandler
from werkzeug.security import generate_password_hash, check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
@pytest.fixture
def client():
    original_conn = app_module.conn
    original_cur = app_module.cur

    db_fd, db_path = tempfile.mkstemp()
    test_conn = sqlite3.connect(db_path, check_same_thread=False)
    test_cur = test_conn.cursor()

    test_cur.executescript('''
        CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        last_login TIMESTAMP,
        role TEXT DEFAULT 'user');
                           
        CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT);
                           
        CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        user_id INTEGER,
        category_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (category_id) REFERENCES categories(id));
                           
        CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id));
                           
        CREATE TABLE IF NOT EXISTS auth_tokens(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        token TEXT UNIQUE,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id));
    ''')
    
    hashed = generate_password_hash('password123')
    test_cur.execute(
        'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
        ('Test User', 'test@example.com', hashed, 'user')
    )

    test_cur.execute(
        'INSERT INTO categories (name, description) VALUES (?, ?)',
        ('Тестовая категория', 'Описание')
    )

    test_conn.commit()

    app_module.conn = test_conn
    app_module.cur = test_cur

    with flask_app.test_client() as client:
        yield client

    app_module.conn = original_conn
    app_module.cur = original_cur
    test_conn.close()
    os.close(db_fd)
    os.unlink(db_path)


def test_get_posts(client):
    response = client.get('/api/v1/posts')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'data' in json_data
    
def test_get_single_post_not_found(client):
    response = client.get('/api/v1/posts/999')
    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['success'] is False

def test_login_success(client):
    response = client.post('/api/v1/login', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True

def test_login_wrong_password(client):
    response = client.post('/api/v1/login', json={
        'email': 'test@example.com',
        'password': 'wrong'
    })
    assert response.status_code == 401
    json_data = response.get_json()
    assert json_data['success'] is False

def add_user(name, email, password):
    hashed_password = generate_password_hash(password)
    cur.execute('INSERT INTO users(name, email, password, last_login) VALUE'
                [name, email, hashed_password, datetime.now()])
    conn.commit()
    cur.execute('SELECT id FROM users WHERE email = ?', [email])
    return cur.fetchone()[0]

def get_user_by_id(user_id):
    cur.execute('SELECT * FROM users WHERE id = ?', [user_id])
    return cur.fetchone()          

def get_user_by_email(email):
    cur.execute('SELECT * FROM users WHERE email = ?', [email])
    return cur.fetchone()

def update_last_login(user_id):
    cur.execute('UPDATE users SET last_login ')    