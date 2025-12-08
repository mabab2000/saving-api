"""
Debug FCM token characters
"""

token = "f1BdLGhuEMfj7H1bVz9gJ3:APA91bF1BdLGhuEMfj7H1bVz9gJ3K4L5M6N7O8P9Q0R1S2T3U4V5W6X7Y8Z9A0B1C2D3E4F5G6H7I8J9K0L1M2N3O4P5Q6R7S8T9U0V1W2X3Y4Z5A6"

print(f"Token length: {len(token)}")
print(f"Token: {token}")

# Check for invalid characters
import re
valid_chars = re.match(r'^[A-Za-z0-9_:.-]+$', token)
print(f"Valid chars: {valid_chars is not None}")

# Find invalid characters
invalid_chars = []
for char in token:
    if not re.match(r'[A-Za-z0-9_:.-]', char):
        if char not in invalid_chars:
            invalid_chars.append(char)

if invalid_chars:
    print(f"Invalid characters found: {invalid_chars}")
    for char in invalid_chars:
        print(f"  '{char}' (ASCII: {ord(char)})")
else:
    print("No invalid characters found")

# Real FCM token analysis - checking length requirements
if len(token) >= 140:
    print("✅ Length check passed")
else:
    print("❌ Length check failed")