from PIL import Image, ImageDraw

def make_image_round(input_path, output_path):
    # Görseli aç
    img = Image.open(input_path).convert("RGBA")

    # Kareye kırp (gerekirse)
    width, height = img.size
    min_dim = min(width, height)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim
    img = img.crop((left, top, right, bottom))

    # Maske oluştur (yuvarlak)
    mask = Image.new('L', (min_dim, min_dim), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, min_dim, min_dim), fill=255)

    # Yeni görseli maske ile birleştir
    result = Image.new('RGBA', (min_dim, min_dim), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)

    # Kaydet
    result.save(output_path, format="PNG")

# Örnek kullanım
make_image_round("Select_Theater1.png", "Select_Theater.png")
