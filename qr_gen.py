import qrcode
from PIL import Image, ImageDraw, ImageFont
import os

def generate_kisanpukar_qr():
    """
    KisanPukar AI ka WhatsApp QR Code banao
    Scan karne pe WhatsApp khulega with pre-filled message
    """
    
    # Twilio sandbox number + join code
    whatsapp_number = "14155238886"
    join_message = "join list-stream"
    
    # WhatsApp deep link
    whatsapp_url = f"https://wa.me/{whatsapp_number}?text={join_message}"
    
    print(f"QR Code URL: {whatsapp_url}")
    
    # QR Code banao
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    qr.add_data(whatsapp_url)
    qr.make(fit=True)
    
    # Green color QR
    qr_img = qr.make_image(
        fill_color="#1B5E20",
        back_color="white"
    ).convert('RGB')
    
    # Canvas banao branding ke liye
    qr_width, qr_height = qr_img.size
    canvas_width = qr_width + 40
    canvas_height = qr_height + 160
    
    # White background
    canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
    
    # Green header
    header = Image.new('RGB', (canvas_width, 80), color='#1B5E20')
    canvas.paste(header, (0, 0))
    
    # QR code paste karo
    canvas.paste(qr_img, (20, 90))
    
    # Green footer
    footer = Image.new('RGB', (canvas_width, 70), color='#1B5E20')
    canvas.paste(footer, (0, qr_height + 90))
    
    # Text add karo
    draw = ImageDraw.Draw(canvas)
    
    # Header text
    draw.text(
        (canvas_width // 2, 25),
        "🌾 کسان پکار AI",
        fill="white",
        anchor="mm"
    )
    draw.text(
        (canvas_width // 2, 55),
        "KisanPukar AI — Scan to Start",
        fill="white",
        anchor="mm"
    )
    
    # Footer text
    draw.text(
        (canvas_width // 2, qr_height + 105),
        "WhatsApp pe scan karein",
        fill="white",
        anchor="mm"
    )
    draw.text(
        (canvas_width // 2, qr_height + 135),
        "پاکستانی کسان کا ڈیجیٹل ساتھی 🇵🇰",
        fill="white",
        anchor="mm"
    )
    
    # Save karo
    output_path = "kisanpukar_qr.png"
    canvas.save(output_path, "PNG", quality=95)
    print(f"\n✅ QR Code saved: {output_path}")
    print(f"📍 Location: D:\\agribot\\{output_path}")
    print(f"\n📱 Test karne ke liye:")
    print(f"   Yeh URL browser mein kholo:")
    print(f"   {whatsapp_url}")
    
    return output_path

if __name__ == "__main__":
    generate_kisanpukar_qr()