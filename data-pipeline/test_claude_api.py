#!/usr/bin/env python3
"""
Test Claude API Connection
Quick test to verify API key and model access
"""

import os
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

def test_claude_api():
    """Test Claude API connection and model"""

    print("="*80)
    print("Claude API Test")
    print("="*80 + "\n")

    # Check if API key exists
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("✗ CLAUDE_API_KEY not found in .env file")
        print("  Please add: CLAUDE_API_KEY=sk-ant-...")
        return False

    print(f"✓ API key found: {api_key[:15]}...{api_key[-4:]}")
    print(f"  Length: {len(api_key)} characters\n")

    # Test connection
    print("Testing connection to Claude API...")
    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Simple test request
        print("Sending test message...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Reply with exactly: 'API test successful'"}
            ]
        )

        response_text = response.content[0].text
        print(f"✓ Response received: {response_text}")
        print(f"  Model used: {response.model}")
        print(f"  Tokens used: input={response.usage.input_tokens}, output={response.usage.output_tokens}")

        print("\n" + "="*80)
        print("✓ Claude API is working correctly!")
        print("="*80)
        return True

    except anthropic.AuthenticationError as e:
        print(f"\n✗ Authentication Error: {e}")
        print("  Your API key is invalid or expired")
        print("  Get a new key from: https://console.anthropic.com/")
        return False

    except anthropic.PermissionDeniedError as e:
        print(f"\n✗ Permission Denied: {e}")
        print("  Your API key doesn't have access to this model")
        return False

    except anthropic.RateLimitError as e:
        print(f"\n✗ Rate Limit Error: {e}")
        print("  You've hit the rate limit - wait a bit and try again")
        return False

    except anthropic.APIError as e:
        print(f"\n✗ API Error: {e}")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Status code: {e.status_code if hasattr(e, 'status_code') else 'N/A'}")
        return False

    except Exception as e:
        print(f"\n✗ Unexpected Error: {e}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_claude_api()
    exit(0 if success else 1)