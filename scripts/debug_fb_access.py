import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_access():
    token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
    if not token:
        print("Error: FACEBOOK_PAGE_ACCESS_TOKEN not found in .env")
        print("Please copy the 'Access Token' from Graph API Explorer and put it in .env first.")
        return

    print(f"Checking user info...")
    me_url = f"https://graph.facebook.com/v21.0/me?fields=id,name&access_token={token}"
    me_res = requests.get(me_url).json()
    print(f"Token User: {me_res.get('name')} (ID: {me_res.get('id')})")

    print(f"Checking token permissions...")
    debug_url = f"https://graph.facebook.com/v21.0/debug_token?input_token={token}&access_token={token}"
    # This might require app secret if using app token, but for user token it often works with me
    # Let's try simpler: me/permissions
    perm_url = f"https://graph.facebook.com/v21.0/me/permissions?access_token={token}"
    perm_res = requests.get(perm_url).json()
    
    perms = [p['permission'] for p in perm_res.get('data', []) if p['status'] == 'granted']
    print(f"Granted Permissions: {', '.join(perms)}")
    
    if 'pages_show_list' not in perms:
        print("!!! WARNING: 'pages_show_list' permission is MISSING from this token.")
    if 'instagram_basic' not in perms:
        print("!!! WARNING: 'instagram_basic' permission is MISSING from this token.")

    print("\nChecking Facebook Pages (me/accounts)...")
    url = f"https://graph.facebook.com/v21.0/me/accounts?access_token={token}"
    res = requests.get(url).json()

    pages = res.get("data", [])
    if not pages:
        print("No Facebook Pages found in 'me/accounts'.")
        print("Attempting to test the IDs from your screenshot directly...")
        
        # Test Page ID from screenshot: 974037085800517
        page_id = "974037085800517"
        print(f"\nTesting Page ID: {page_id}")
        p_url = f"https://graph.facebook.com/v21.0/{page_id}?fields=name,instagram_business_account&access_token={token}"
        p_res = requests.get(p_url).json()
        
        if "error" in p_res:
            print(f"  [ERROR] Cannot access Page {page_id}: {p_res['error']['message']}")
        else:
            print(f"  [SUCCESS] Found Page: {p_res.get('name')}")
            ig_biz = p_res.get("instagram_business_account")
            if ig_biz:
                print(f"  [FOUND] Instagram Business ID: {ig_biz['id']}")
            else:
                print("  [NOT FOUND] No Instagram Business Account linked to this page.")
                
        # Test Instagram ID from screenshot: 17841446874281790
        ig_id = "17841446874281790"
        print(f"\nTesting Instagram ID: {ig_id}")
        ig_url = f"https://graph.facebook.com/v21.0/{ig_id}?fields=username&access_token={token}"
        ig_res = requests.get(ig_url).json()

        if "error" in ig_res:
            print(f"  [ERROR] Cannot access Instagram Account {ig_id}: {ig_res['error']['message']}")
        else:
            print(f"  [SUCCESS] Found Instagram Account: @{ig_res.get('username')}")
    else:
        for page in pages:
            # (Existing logic for listing pages)
            print(f"\nPage Name: {page['name']}")
            print(f"Page ID: {page['id']}")
            ig_url = f"https://graph.facebook.com/v21.0/{page['id']}?fields=instagram_business_account&access_token={token}"
            ig_res = requests.get(ig_url).json()
            ig_biz = ig_res.get("instagram_business_account")
            if ig_biz:
                print(f"  [FOUND] Instagram Business ID: {ig_biz['id']}")
            else:
                print("  [NOT FOUND] No Instagram Business Account linked.")

if __name__ == "__main__":
    check_access()
