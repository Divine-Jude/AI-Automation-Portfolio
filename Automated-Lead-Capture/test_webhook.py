import requests
import json

# Replace this URL with your n8n Webhook Test URL
WEBHOOK_URL = "YOUR_N8N_WEBHOOK_URL_HERE"

def test_webhook():
    # Mock data representing a highly qualified lead form submission
    payload = {
        "firstName": "Sarah",
        "lastName": "Connor",
        "email": "sarah.connor@cyberdyne.com",
        "companyName": "Cyberdyne Systems",
        "jobTitle": "Director of Technology",
        "inquiry": "We are struggling with manual data entry for our robotics division. Do you have any experience automating healthcare or manufacturing robotics workflows?"
    }

    print(f"Sending lead data to: {WEBHOOK_URL}")
    print("Payload:")
    print(json.dumps(payload, indent=2))

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("\n✅ Success! Webhook triggered successfully.")
        print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error triggering webhook: {e}")
        print("Make sure your n8n workflow is active or listening for a test event!")

if __name__ == "__main__":
    if "YOUR_N8N_WEBHOOK_URL_HERE" in WEBHOOK_URL:
        print("⚠️ Please update the WEBHOOK_URL variable in this file with your n8n webhook URL.")
    else:
        test_webhook()
