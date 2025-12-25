import io
import os
import torch
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from diffusers import StableDiffusionInpaintPipeline, UNet2DConditionModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_CHECKPOINT_PATH = os.path.join(BASE_DIR, "Models", "diffusion")
MODEL_ID = "runwayml/stable-diffusion-inpainting"
IMG_SIZE = 512

if torch.cuda.is_available():
    DEVICE = "cuda"
    DTYPE = torch.float16
    print("GPU")
else:
    DEVICE = "cpu"
    DTYPE = torch.float32
    print("CPU")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipe = None

print("\n" + "="*50)
print("Start load model")

try:
    print("1. Loading Base Pipeline (RunwayML)...")
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=DTYPE,
        safety_checker=None,
        use_safetensors=False 
    ).to(DEVICE)
    print("Base Pipeline OK.")

    print(f"2. Loading Fine-tuned UNet from {MODEL_CHECKPOINT_PATH}...")
    
    if os.path.exists(MODEL_CHECKPOINT_PATH):
        is_safetensors = os.path.exists(os.path.join(MODEL_CHECKPOINT_PATH, "diffusion_pytorch_model.safetensors"))
        
        try:
            print(f"Detected Custom Model type: {'Safetensors' if is_safetensors else 'Bin'}")
            unet = UNet2DConditionModel.from_pretrained(
                MODEL_CHECKPOINT_PATH, 
                torch_dtype=DTYPE,
                use_safetensors=is_safetensors 
            ).to(DEVICE)
            
            pipe.unet = unet
            print("Custom UNet loaded successfully!")
        except Exception as e:
            print(f"Error load UNet: {e}")
    else:
        print("Run Base Model.")

    if DEVICE == "cuda":
        pipe.enable_attention_slicing()

except Exception as e:
    print(f"FATAL ERROR: {e}")
    pipe = None

print("="*50 + "\n")

def process_inference_plate(
    crop_img_pil: Image.Image, 
    rotate=0, 
    translate_x=0, 
    translate_y=0,
    scale_factor=1.0,
    prompt="",
    steps=30,
    guidance=7.5,
    seed=42
):
    crop_img = crop_img_pil.convert("RGBA")
    w, h = crop_img.size
    
    target_w = int(IMG_SIZE * 0.25 * scale_factor) 
    scale_ratio = target_w / w
    target_h = int(h * scale_ratio)
    
    crop_resized = crop_img.resize((target_w, target_h), Image.BICUBIC)
    
    crop_rotated = crop_resized.rotate(-rotate, expand=True, resample=Image.BICUBIC, fillcolor=(0,0,0,0))
    new_w, new_h = crop_rotated.size
    
    center_x = (IMG_SIZE - new_w) // 2
    center_y = int(IMG_SIZE * 0.65)
    
    pos_x = int(center_x + translate_x)
    pos_y = int(center_y + translate_y)
    
    image = Image.new("RGB", (IMG_SIZE, IMG_SIZE), (127, 127, 127))
    image.paste(crop_rotated, (pos_x, pos_y), mask=crop_rotated)
    
    mask = Image.new("L", (IMG_SIZE, IMG_SIZE), 255)
    plate_alpha = crop_rotated.split()[-1]
    plate_shape_black = Image.new("L", (new_w, new_h), 0)
    mask.paste(plate_shape_black, (pos_x, pos_y), mask=plate_alpha)
    
    negative_prompt = "low quality, blurry, distorted, text, watermark, bad anatomy, cropped"
    print(f"Generating: '{prompt}' | Seed: {seed}")
    generator = torch.Generator(device=DEVICE).manual_seed(seed)
    
    result = pipe(
        prompt=prompt,
        negative_prompt=negative_prompt,
        image=image,
        mask_image=mask,
        num_inference_steps=steps,
        guidance_scale=guidance,
        strength=1.0,
        generator=generator
    ).images[0]
    
    result.paste(crop_rotated, (pos_x, pos_y), mask=crop_rotated)
    
    return result
@app.get("/")
def health_check():
    return {"status": "ok", "model_loaded": pipe is not None}

@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    prompt: str = Form("a photo of a car"),
    x: float = Form(0),
    y: float = Form(0),
    rotation: float = Form(0),
    scale: float = Form(1.0),
    steps: int = Form(30),
    guidance: float = Form(7.5),
    seed: int = Form(42)
):
    if pipe is None:
        raise HTTPException(status_code=500, detail="Model failed to load. Check server logs.")

    try:
        contents = await file.read()
        plate_img = Image.open(io.BytesIO(contents))
        
        output_image = process_inference_plate(
            crop_img_pil=plate_img,
            rotate=rotation,
            translate_x=x,
            translate_y=y,
            scale_factor=scale,
            prompt=prompt,
            steps=steps,
            guidance=guidance,
            seed=seed
        )
        
        img_byte_arr = io.BytesIO()
        output_image.save(img_byte_arr, format='PNG')
        return Response(content=img_byte_arr.getvalue(), media_type="image/png")
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)