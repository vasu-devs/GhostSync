from PIL import Image, ImageDraw, ImageFont

# Create a modern dark blue splash screen
width, height = 600, 350
bg_color = "#1a1a2e"  # Dark blue/black
accent_color = "#3B8ED0" # GhostSync Blue

img = Image.new('RGB', (width, height), color=bg_color)
d = ImageDraw.Draw(img)

# Add decorative graphic (abstract ghost/sync shape)
d.ellipse((250, 100, 350, 200), outline=accent_color, width=3)
d.line((200, 150, 400, 150), fill=accent_color, width=2)
d.line((300, 50, 300, 250), fill=accent_color, width=2)

# Text (Simulated font since we might not have custom ones)
# Ideally we'd use a TTF, but default will ensure it runs
try:
    # Try to load a nicer font if available
    font_large = ImageFont.truetype("arialbd.ttf", 40)
    font_small = ImageFont.truetype("arial.ttf", 14)
except:
    font_large = ImageFont.load_default()
    font_small = ImageFont.load_default()

# Draw Title
text = "GhostSync Pro"
text_w = d.textlength(text, font=font_large) if hasattr(d, 'textlength') else 200
d.text(((width-text_w)/2, 220), text, fill="white", font=font_large)

# Draw Loading text
status = "Initializing Secure Bridge..."
status_w = d.textlength(status, font=font_small) if hasattr(d, 'textlength') else 150
d.text(((width-status_w)/2, 280), status, fill="gray", font=font_small)

# Draw Progress Bar container
bar_w, bar_h = 400, 4
bar_x, bar_y = (width - bar_w)/2, 310
d.rectangle((bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), fill="#333333")

# Draw Progress (Indeterminate look)
d.rectangle((bar_x, bar_y, bar_x + 100, bar_y + bar_h), fill=accent_color)

img.save("splash.png")
print("Splash image created.")
