import requests
import time

def trigger():
    print("Triggering Pipeline API...")
    try:
        url = "http://localhost:8000/api/pipeline/run"
        # run endpoint might take query params, not body, based on my previous read?
        # Let's check pipeline.py.
        # run_pipeline(batch_size: int = 1000, ...)
        # It's a POST. Requests often take query params if defined as args in FastAPI.
        # Or I can send as query params.
        
        resp = requests.post(url, params={"batch_size": 100})
        
        if resp.status_code == 200:
            print("Success!")
            print(resp.json())
        else:
            print(f"Failed: {resp.status_code}")
            print(resp.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger()
