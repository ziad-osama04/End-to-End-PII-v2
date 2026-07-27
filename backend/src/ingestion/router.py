import io
import json
import pandas as pd
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from src.detection.pii_detector import get_detector

router = APIRouter()

class ChatRequest(BaseModel):
    text: str

@router.post("/chat")
async def chat_redact(request: ChatRequest):
    detector = get_detector()
    redacted_text = detector.redact_text(request.text)
    return {"redacted_text": redacted_text}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    detector = get_detector()
    content = await file.read()
    filename = file.filename.lower()
    
    try:
        if filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
            redacted = detector.redact_text(text)
            return {"filename": file.filename, "redacted_content": redacted}
            
        elif filename.endswith(".pdf"):
            # Try to extract text first using PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            
            # If no text found, maybe it's a scanned PDF
            if not text.strip():
                # Extract images and OCR
                text = ""
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    for img in page.get_images(full=True):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image = Image.open(io.BytesIO(image_bytes))
                        text += pytesseract.image_to_string(image, lang="nld")
            
            redacted = detector.redact_text(text)
            return {"filename": file.filename, "redacted_content": redacted}
            
        elif filename.endswith((".png", ".jpg", ".jpeg")):
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image, lang="nld")
            redacted = detector.redact_text(text)
            return {"filename": file.filename, "redacted_content": redacted}
            
        elif filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            # Redact all string columns
            for col in df.select_dtypes(include=['object']):
                df[col] = df[col].apply(lambda x: detector.redact_text(str(x)) if pd.notnull(x) else x)
            return {"filename": file.filename, "redacted_content": df.to_csv(index=False)}
            
        elif filename.endswith(".json"):
            data = json.loads(content.decode("utf-8", errors="ignore"))
            
            def redact_json(obj):
                if isinstance(obj, dict):
                    return {k: redact_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [redact_json(v) for v in obj]
                elif isinstance(obj, str):
                    return detector.redact_text(obj)
                else:
                    return obj
                    
            redacted_data = redact_json(data)
            return {"filename": file.filename, "redacted_content": json.dumps(redacted_data, indent=2)}
            
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
