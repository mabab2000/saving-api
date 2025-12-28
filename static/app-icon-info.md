# Saving App Icon Information

Since we cannot directly create PNG files in this environment, you'll need to:

1. **Convert the SVG to PNG**: Use the app-icon.svg file in the static folder and convert it to PNG format
2. **Create app-icon.png**: Save as 512x512 pixels for best quality
3. **Alternative**: Create your custom app icon with your preferred design tool

## Current Icon Features:
- Green background representing growth and savings
- Pink piggy bank as the main savings symbol  
- Gold coins scattered around
- "RWF" text to indicate Rwanda Franc currency
- Optimized for push notifications

## Icon URL in notifications:
The notification system is configured to use: `https://saving-api.mababa.app/static/app-icon.png`

Make sure to place your final PNG icon at: `static/app-icon.png`