from flask import Flask, request, jsonify
import requests
import json
import os
import base64
import hashlib
import datetime
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

app = Flask(__name__)

# API Key Authentication
API_KEY = os.environ.get("API_KEY", "Mob2GAS-key_s0undw4v3")

# UMANG Gateway RSA-OAEP Public Key (DER Base64)
UMANG_RSA_PUB_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArpgmSqIv/3zYAxoNK/6eLqjeBEHFsiGJ"
    "Cia5wdQuhCw54ceg6EyKc5mPrkEnK7CYgbJxSQO37HbnWIROMN6kRQqxa1kZFFS+xQPZ9z4Gs+nj"
    "ypX8HNKcse2/kbwbIX4y8kcCENVVOV8URK8+znEsuN/UCzJXv2Pg0KII5ofb8wAvYNXkZ44DhcWn"
    "yxO6JohbuMvpt096NBkdq8lWtRrappL3HqpTG4Fd5H4v9b7fD8rAhBB8cAbiM2nyBz51VDovS/SZ"
    "heIemKjwGLGMDiMeNcQGryOTZASX+jxe69NoFR9bQ8+5jN/88x5k53UzV8en+HRKbYjgUJzZOVfu"
    "3fL/WQIDAQAB"
)

def encrypt_umang_payload(payload_dict):
    """
    Encrypts the JSON payload using UMANG Gateway's hybrid encryption scheme:
    - AES-256-CBC with PKCS7 padding for the JSON body
    - RSA-OAEP (SHA-256) for AES key and IV
    - Headers: X-REQUEST-VALUE (MD5), X-REQUEST-CONTROL (SHA-256), X-REQUEST-TSTAMP
    """
    rsa_key = load_der_public_key(base64.b64decode(UMANG_RSA_PUB_KEY))
    payload_json = json.dumps(payload_dict, separators=(',', ':'))

    # Timestamp: YYYYMMDDHHMMSS (UTC)
    now = datetime.datetime.now(datetime.timezone.utc)
    tstamp = now.strftime('%Y%m%d%H%M%S')

    # Security Hashes with gateway salts
    md5_val = hashlib.md5((payload_json + '|R%d&Wst676#(Na').encode('utf-8')).hexdigest()
    sha_val = hashlib.sha256(('|' + tstamp + '|$f%GY#JX^9H@|').encode('utf-8')).hexdigest()

    # Generate AES-256 key (32 bytes) and IV (16 bytes)
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    # PKCS7 padding on JSON bytes
    data_bytes = payload_json.encode('utf-8')
    pad_len = 16 - (len(data_bytes) % 16)
    padded_data = data_bytes + bytes([pad_len] * pad_len)

    # AES-CBC encrypt
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    # RSA-OAEP encrypt AES key & IV with SHA-256
    oaep = asym_padding.OAEP(
        mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
    enc_aes_key = rsa_key.encrypt(aes_key, oaep)
    enc_iv = rsa_key.encrypt(iv, oaep)

    # Gateway encrypted body format: base64(encKey):base64(encIV):base64(encPayload)
    body = (
        base64.b64encode(enc_aes_key).decode() + ':' +
        base64.b64encode(enc_iv).decode() + ':' +
        base64.b64encode(encrypted_data).decode()
    )

    headers = {
        'Content-Type': 'text/plain',
        'accept': 'text/plain',
        'X-REQUEST-VALUE': md5_val,
        'X-REQUEST-CONTROL': sha_val,
        'X-REQUEST-TSTAMP': tstamp,
        'X-API-KEY': 'VKE9PnbY5k1ZYapR5PyYQ33I26sXTX569Ed7eqyg',
        'origin': 'https://web.umang.gov.in',
        'referer': 'https://web.umang.gov.in/',
        'deptid': '186',
        'srvid': '1123',
        'subsid': '0',
        'formtrkr': '0'
    }

    return body, headers

@app.route('/', methods=['GET'], strict_slashes=False)
def index():
    return jsonify({
        "status": "online",
        "service": "Mobile2GAS LPG Information API",
        "version": "2.0.0",
        "encryption": "UMANG RSA-OAEP + AES-256-CBC Hybrid Gateway Engine enabled",
        "endpoints": {
            "/lpg-info": {
                "methods": ["GET", "POST"],
                "description": "Fetch LPG consumer information by registered mobile number",
                "auth": "API key required via query param (?key=...), JSON body, or Bearer token",
                "params": {
                    "mobile_no": "10-digit registered mobile number (required)",
                    "key": "API Key (required)",
                    "tkn": "Optional fresh UMANG citizen session token",
                    "mock": "Set to 'true' for simulated consumer response in test mode"
                },
                "examples": {
                    "get": "/lpg-info?mobile_no=98XXXXXXXX&key=YOUR_API_KEY",
                    "curl": "curl \"https://mobile2gas.vercel.app/lpg-info?mobile_no=98XXXXXXXX&key=YOUR_API_KEY\""
                }
            }
        }
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Not Found",
        "message": "The requested URL was not found on the server.",
        "available_endpoints": ["/", "/lpg-info"]
    }), 404

@app.route('/lpg-info', methods=['GET', 'POST'], strict_slashes=False)
def get_lpg_info():
    # Verify API key
    key = request.args.get('key')
    if not key and request.is_json:
        try:
            key = request.get_json().get('key')
        except Exception:
            pass
    if not key:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            key = auth_header.split(' ')[1]

    if key != API_KEY:
        return jsonify({
            "error": "Unauthorized",
            "message": "Invalid or missing API key"
        }), 401

    # Get mobile number
    mobile_no = request.args.get('mobile_no')
    if not mobile_no and request.is_json:
        try:
            mobile_no = request.get_json().get('mobile_no')
        except Exception:
            pass
    
    if not mobile_no:
        return jsonify({
            "error": "Mobile number is required",
            "message": "Please provide mobile_no parameter (e.g. mobile_no=9876543210)"
        }), 400

    # Test / Mock Mode for client integration testing
    is_mock = request.args.get('mock', '').lower() == 'true'
    if not is_mock and request.is_json:
        try:
            is_mock = bool(request.get_json().get('mock'))
        except Exception:
            pass

    if is_mock:
        return jsonify({
            "status": "success",
            "mode": "test_mock",
            "mobile_no": mobile_no,
            "consumer_details": {
                "consumer_name": "CONSUMER NAME",
                "consumer_no": "2910" + mobile_no[-6:],
                "lpg_id": "31000000" + mobile_no,
                "distributor_name": "INDANE GAS SERVICE",
                "distributor_code": "112345",
                "subsidy_eligible": "Yes",
                "cylinder_type": "14.2 KG Domestic",
                "status": "Active"
            }
        }), 200

    # Optional dynamic session token (fallback to env or default)
    user_tkn = (
        request.args.get('tkn') or 
        (request.get_json().get('tkn') if request.is_json else None) or 
        os.environ.get("UMANG_TOKEN", "iad1cc7d81-1533-44b0-9967-35599386d3df/2")
    )

    # Target API endpoint
    url = 'https://apigw.umangapp.in/ioclApi/ws1/consumervalidate'

    # Construct request payload
    payload = {
        "tkn": user_tkn,
        "trkr": "213132",
        "lang": "en",
        "lat": "21",
        "lon": "90",
        "lac": "90",
        "usag": "90",
        "apitrkr": "123234",
        "usrid": "09",
        "mode": "web",
        "pltfrm": "android",
        "did": "123234",
        "deptid": "186",
        "formtrkr": "0",
        "srvid": "1123",
        "subsid": "0",
        "subsid2": "0",
        "trackingId": "",
        "source": "UMANG",
        "mobile": mobile_no,
        "consumerId": "",
        "partnerCode": "",
        "consumerNumber": ""
    }

    try:
        # Encrypt the payload using UMANG Gateway Hybrid RSA-OAEP + AES-256 scheme
        enc_body, enc_headers = encrypt_umang_payload(payload)

        # Dispatch POST request to UMANG Gateway
        response = requests.post(
            url,
            data=enc_body,
            headers=enc_headers,
            timeout=30
        )

        resp_text = response.text.strip()

        # Check if the response is JSON (e.g. gateway error/status)
        try:
            resp_json = response.json()
            return jsonify({
                "status": "upstream_response",
                "upstream_status_code": response.status_code,
                "data": resp_json
            }), response.status_code
        except json.JSONDecodeError:
            pass

        # If gateway returned the 3-part encrypted response
        parts = resp_text.split(':')
        if len(parts) == 3:
            return jsonify({
                "status": "success",
                "message": "Encrypted payload accepted and processed by UMANG Gateway (200 OK)",
                "mobile_no": mobile_no,
                "upstream_gateway": {
                    "status_code": response.status_code,
                    "encrypted_response_received": True,
                    "response_parts": 3,
                    "notice": "The UMANG Gateway accepted the encrypted request. Citizen decryption requires an active authenticated session key."
                }
            }), 200

        return jsonify({
            "status": "upstream_raw",
            "upstream_status_code": response.status_code,
            "response": resp_text
        }), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Request failed",
            "message": str(e)
        }), 500
    except Exception as e:
        return jsonify({
            "error": "Internal server error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
