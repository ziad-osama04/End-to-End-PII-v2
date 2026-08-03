import io
import json
import pandas as pd
import pytesseract
from PIL import Image
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from pydantic import BaseModel
from src.detection.pii_detector import get_detector, KEEP_VISIBLE
from masking_service.pdf_masking import mask_pdf

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
            # A PDF is masked in place and returned as a PDF with the SAME
            # structure (pages, layout, fonts, images) -- only the PII regions
            # are redacted. Reuse the contract service's PDF masker so the demo
            # and the API behave identically.
            def detect_spans(text: str):
                results = detector.analyzer.analyze(text=text, language="nl")
                results = [r for r in results if r.entity_type not in KEEP_VISIBLE]
                return [(r.start, r.end, r.entity_type) for r in results]

            masked_pdf, _entities = mask_pdf(content, detect_spans)
            return Response(
                content=masked_pdf,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="masked_{file.filename}"'
                    )
                },
            )

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
