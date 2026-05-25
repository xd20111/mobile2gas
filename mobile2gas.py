from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# API Key Authentication
API_KEY = os.environ.get("API_KEY", "Mob2GAS-key_s0undw4v3")

@app.route('/lpg-info', methods=['GET', 'POST'])
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
            "message": "Please provide mobile_no parameter"
        }), 400
    
    # API endpoint
    url = 'https://apigw.umangapp.in/ioclApi/ws1/consumervalidate'
    
    # Headers from your curl command
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Mobile Safari/537.36',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json',
        'subsid': '0',
        'sec-ch-ua-platform': '"Android"',
        'deptid': '186',
        'tenantid': '',
        'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        'formtrkr': '0',
        'x-api-key': 'VKE9PnbY5k1ZYapR5PyYQ33I26sXTX569Ed7eqyg',
        'sec-ch-ua-mobile': '?1',
        'srvid': '1123',
        'subsid2': '0',
        'origin': 'https://web.umang.gov.in',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'referer': 'https://web.umang.gov.in/',
        'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        'priority': 'u=1, i'
    }
    
    # Cookies
    cookies = {
        'AWSALB': 'lE0YK+DgRyMb35tTzJ0MdnqLQ208FzgWeZ9OzeMisqYuOTJxRaFV8PCn0Vgj4mneJV426VaFo1456Kfjp6ysCpS1xihWZCDi3ioPQxHM+qemZYCMoczbIMjL8Cjz',
        'AWSALBCORS': 'lE0YK+DgRyMb35tTzJ0MdnqLQ208FzgWeZ9OzeMisqYuOTJxRaFV8PCn0Vgj4mneJV426VaFo1456Kfjp6ysCpS1xihWZCDi3ioPQxHM+qemZYCMoczbIMjL8Cjz'
    }
    
    # Request body
    payload = {
        "tkn": "iad1cc7d81-1533-44b0-9967-35599386d3df/2",
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
        "mobile": mobile_no,  # Using the provided mobile number
        "consumerId": "",
        "partnerCode": "",
        "consumerNumber": ""
    }
    
    try:
        # Make the POST request
        response = requests.post(
            url, 
            headers=headers, 
            cookies=cookies, 
            json=payload,
            timeout=30
        )
        
        # Return the raw JSON response
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Request failed",
            "message": str(e)
        }), 500
    except json.JSONDecodeError as e:
        return jsonify({
            "error": "Invalid JSON response",
            "message": str(e),
            "raw_response": response.text
        }), 500

# The POST route is consolidated into the main route above

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)