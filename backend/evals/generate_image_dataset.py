import json
import random
from pathlib import Path
import albumentations as A
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION (Points directly to evals/synthetic_images/dev_200) ---
BASE_DIR = Path("./evals/synthetic_images/dev_200")
AUTHENTIC_DIR = BASE_DIR / "authentic"
TAMPERED_DIR = BASE_DIR / "tampered"

# Auto-create output directories
AUTHENTIC_DIR.mkdir(parents=True, exist_ok=True)
TAMPERED_DIR.mkdir(parents=True, exist_ok=True)

NUM_IMAGES = 12
IMAGE_SIZE = (800, 1000)

# --- ALBUMENTATIONS PIPELINE (Fixed GaussNoise warning) ---
augmentation_pipeline = A.Compose(
    [
        A.Perspective(scale=(0.02, 0.04), p=0.5),
        A.OneOf(
            [
                A.MotionBlur(blur_limit=3, p=0.5),
                A.Defocus(radius=(1, 2), alias_blur=(0.1, 0.4), p=0.5),
            ],
            p=0.4,
        ),
        # Fixed argument for newer Albumentations versions
        A.GaussNoise(p=0.3),
        A.RandomBrightnessContrast(
            brightness_limit=0.12, contrast_limit=0.12, p=0.6
        ),
        A.ImageCompression(quality_range=(50, 85), p=0.7),
    ]
)


def create_base_document(recipient_name, waybill_no, timestamp, address):
    img = Image.new("RGB", IMAGE_SIZE, color=(250, 250, 252))
    draw = ImageDraw.Draw(img)

    try:
        font_header = ImageFont.truetype("arial.ttf", 24)
        font_body = ImageFont.truetype("arial.ttf", 16)
        font_bold = ImageFont.truetype("arialbd.ttf", 18)
    except IOError:
        font_header = font_body = font_bold = ImageFont.load_default()

    draw.rectangle([0, 0, IMAGE_SIZE[0], 60], fill=(40, 20, 60))
    draw.text(
        (30, 18),
        "LOGISTICS EXPRESS — Delivery Verification Receipt",
        fill=(255, 255, 255),
        font=font_header,
    )

    y = 120
    fields = [
        ("Tracking / Waybill No:", waybill_no),
        ("Recipient Name:", recipient_name),
        ("Delivery Status:", "DELIVERED"),
        ("Timestamp:", timestamp),
        ("Destination:", address),
        ("Verification Method:", "Electronic Signature & OTP Match"),
    ]

    field_positions = {}
    for label, val in fields:
        draw.text((40, y), label, fill=(100, 100, 100), font=font_body)
        draw.text((260, y), val, fill=(20, 20, 20), font=font_bold)
        field_positions[label] = (260, y)
        y += 55

    return img, field_positions


def apply_realistic_stamp(img, text="VERIFIED"):
    stamp_layer = Image.new("RGBA", IMAGE_SIZE, (255, 255, 255, 0))
    stamp_draw = ImageDraw.Draw(stamp_layer)

    stamp_draw.rectangle([550, 110, 720, 170], outline=(34, 139, 34, 200), width=3)

    try:
        font_stamp = ImageFont.truetype("arialbd.ttf", 20)
    except IOError:
        font_stamp = ImageFont.load_default()

    stamp_draw.text((568, 128), text, fill=(34, 139, 34, 220), font=font_stamp)

    angle = random.uniform(-5, 5)
    stamp_layer = stamp_layer.rotate(
        angle, resample=Image.BICUBIC, center=(635, 140)
    )

    img = img.convert("RGBA")
    return Image.alpha_composite(img, stamp_layer).convert("RGB")


def apply_realistic_tampering(img, text_pos, original_text):
    draw = ImageDraw.Draw(img)
    x, y = text_pos

    draw.rectangle([x - 2, y - 2, x + 260, y + 25], fill=(250, 250, 252))

    tampered_name = original_text.split()[0] + " K."
    try:
        font_tampered = ImageFont.truetype("times.ttf", 18)
    except IOError:
        font_tampered = ImageFont.load_default()

    draw.text((x, y + 1), tampered_name, fill=(15, 15, 15), font=font_tampered)
    return img, tampered_name


# --- SAMPLE DATA ---
sample_data = [
    ("Siddharth Rao", "TRK-100024", "2026-08-21 10:14 IST", "72 Marine Drive, Nariman Point, MH 400021"),
    ("Prashanth C", "TRK-100001", "2026-08-17 19:29 IST", "45 MG Road, Indiranagar, Bangalore, KA 560038"),
    ("P. Kumar", "TRK-100003", "2026-08-08 07:42 IST", "Plot 12, Cyber City, Phase 2, Gurgaon, HR 122002"),
    ("Priyanka Reddy", "TRK-100007", "2026-08-18 10:22 IST", "88 Residency Road, Bangalore, KA 560025"),
    ("Ananya Iyer", "TRK-100013", "2026-08-14 12:43 IST", "Plot 12, Cyber City, Phase 2, Gurgaon, HR 122002"),
    ("Rajesh Sharma", "TRK-100088", "2026-08-20 15:10 IST", "12 Park Street, Kolkata, WB 700016"),
]

metadata_records = []

for i in range(NUM_IMAGES):
    base_info = sample_data[i % len(sample_data)]
    rec_name, waybill, timestamp, addr = base_info

    img, field_positions = create_base_document(rec_name, waybill, timestamp, addr)
    img = apply_realistic_stamp(img)

    # Alternate: Even = Authentic, Odd = Tampered
    is_tampered = (i % 2 != 0)
    final_name = rec_name

    if is_tampered:
        img, final_name = apply_realistic_tampering(
            img, field_positions["Recipient Name:"], rec_name
        )
        target_dir = TAMPERED_DIR
        prefix = "tampered_"
    else:
        target_dir = AUTHENTIC_DIR
        prefix = "authentic_"

    img_np = np.array(img)
    augmented = augmentation_pipeline(image=img_np)["image"]
    final_img = Image.fromarray(augmented)

    filename = f"{prefix}{i+1:02d}.jpg"
    filepath = target_dir / filename
    final_img.save(filepath, quality=85)

    metadata_records.append(
        {
            "filename": filename,
            "path": str(filepath.as_posix()),
            "waybill_no": waybill,
            "recipient_name": final_name,
            "is_tampered": is_tampered,
            "tampered_field": "Recipient Name" if is_tampered else None,
        }
    )

with open(BASE_DIR / "metadata.json", "w") as f:
    json.dump(metadata_records, f, indent=2)

print(f"Successfully generated {NUM_IMAGES} realistic synthetic documents in '{BASE_DIR}'.")