from common.supabase_client import get_supabase
import time
import json

def test_start_run():
    sb = get_supabase()
    print("Inserting START_RUN command...")
    
    payload = {
        "version": "v4",
        "config_overrides": {
            "symbols": ["DOGE/USDT"]
        }
    }
    
    data = {
        "command": "START_RUN",
        "payload": payload,
        "status": "PENDING",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")
    }
    
    res = sb.client.table("commands").insert(data).execute()
    cmd_id = res.data[0]['id']
    print(f"Command inserted with ID: {cmd_id}")
    
    print("Waiting for status update...")
    for _ in range(10):
        time.sleep(2)
        res = sb.client.table("commands").select("*").eq("id", cmd_id).execute()
        status = res.data[0]['status']
        result = res.data[0].get('result')
        print(f"Current Status: {status}, Result: {result}")
        
        if status in ["COMPLETED", "FAILED"]:
            break
            
    print("Test finished.")

if __name__ == "__main__":
    test_start_run()
