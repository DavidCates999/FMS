import requests
import json

def fetch_leads():
    url = "https://fsmapi.s4servicesync.com/api/grid-data/leads"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://fsm.s4servicesync.com",
        "Referer": "https://fsm.s4servicesync.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "x-tenant": "Boston Train-TAX"
    }
    
    cookies = {
        "AUTH-TOKEN": "eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJzZXJ2aWNlc3luYyIsInN1YiI6ImZvcnVzZTE5ODFAZ21haWwuY29tIiwiaWF0IjoxNzY1MTIyNzQ3LCJleHAiOjE3NjUxMjYzNDd9.m7Lr5aSbUxDQphCv8gb5-Mr4hbyPFzmV61Pl1_beQgp2P8DLfYGYwbVrZ4UhXk5JOZL8FuK-1iOlwEi5mp5yNA"
    }
    
    # Query parameters
    params = {
        "startDate": "12/1/2021",
        "endDate": "12/31/2021"
    }
    
    payload = {"group":[],"skip":0,"sort":[],"take":133}
    
    try:
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            params=params,
            json=payload
        )
        
        response.raise_for_status()
        
        # Parse response as JSON
        data = response.json()
        
        # Save to JSON file
        with open("leads_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response saved to leads_response.json")
        print(f"Total records received: {len(data) if isinstance(data, list) else 'N/A (object response)'}")
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON response: {e}")
        print(f"Raw response: {response.text}")
        return None

if __name__ == "__main__":
    fetch_leads()

