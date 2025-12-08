import requests
import json

def fetch_inspection_dashboard():
    url = "https://fsmapi.s4servicesync.com/api/inspection/summarydashboard"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://fsm.s4servicesync.com",
        "Referer": "https://fsm.s4servicesync.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "x-tenant": "Boston Train-TAX"
    }
    
    cookies = {
        "AUTH-TOKEN": "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJzZXJ2aWNlc3luYyIsInN1YiI6ImZvcnVzZTE5ODFAZ21haWwuY29tIiwiaWF0IjoxNzY0OTU2NzkyLCJleHAiOjE3NjQ5NjAzOTJ9.yR9-YTQRAJC2ZF8Jf7i_orP0lltENuhcjE_uyzi5ezL_h3uQQGa0fBQme81iFT6Hod__ee5hsImfglIr2PqckQ"
    }
    
    # Query parameters
    params = {
        "year": 2025,
        "scale": "Monthly",
        "assignedId": 3361
    }
    
    try:
        print(f"Sending request to: {url}")
        print(f"Query parameters: {params}")
        response = requests.get(
            url,
            headers=headers,
            cookies=cookies,
            params=params
        )
        
        print(f"Response status: {response.status_code}")
        response.raise_for_status()
        
        # Parse response as JSON
        data = response.json()
        
        # Save to JSON file
        with open("inspection_dashboard_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response saved to inspection_dashboard_response.json")
        
        # Display record count
        if isinstance(data, dict):
            if "content" in data:
                print(f"Total elements: {data.get('totalElements', 'N/A')}")
                print(f"Records received: {len(data['content'])}")
            elif "data" in data:
                print(f"Records received: {len(data['data'])}")
            else:
                print(f"Response keys: {list(data.keys())}")
        elif isinstance(data, list):
            print(f"Records received: {len(data)}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Raw response: {response.text}")
        return None

if __name__ == "__main__":
    fetch_inspection_dashboard()

