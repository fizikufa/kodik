from fastapi import UploadFile, File
from .file_extractor import extract_text, MAX_FILE_SIZE, SUPPORTED_EXTENSIONS, IMAGE_EXTENSIONS
import base64, mimetypes

@router.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(400, f"Формат {ext} не поддерживается")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(400, "Файл слишком большой (макс. 10MB)")

    if ext in IMAGE_EXTENSIONS:
        mime = mimetypes.guess_type(file.filename)[0] or "image/jpeg"
        b64 = base64.b64encode(data).decode()
        return {"type": "image", "media_type": mime, "data": b64, "filename": file.filename}
    else:
        text = await extract_text(file.filename, data)
        if len(text) > 100_000:  # обрезаем если слишком большой
            text = text[:100_000] + "\n\n[... файл обрезан, превышен лимит контекста]"
        return {"type": "text", "content": text, "filename": file.filename}
