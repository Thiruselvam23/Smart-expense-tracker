from fastapi import APIRouter, Depends, UploadFile, File
from bson import ObjectId
from datetime import datetime
from app.services.ocr_service import process_receipt
from app.utils.file_utils import validate_image_file, save_upload_file
from app.dependencies import get_current_user
from app.database import get_db

router = APIRouter()


@router.post("/scan", status_code=202)
async def scan_receipt(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    validate_image_file(file)
    filepath = await save_upload_file(file)

    # Create job record
    job = {
        "user_id": ObjectId(current_user["id"]),
        "status": "processing",
        "image_path": filepath,
        "created_at": datetime.utcnow(),
    }
    result = await db.ocr_jobs.insert_one(job)
    job_id = str(result.inserted_id)

    # Process synchronously (for simplicity; can be moved to background task)
    ocr_result = await process_receipt(filepath)

    status = "completed" if ocr_result["success"] else "failed"
    await db.ocr_jobs.update_one(
        {"_id": result.inserted_id},
        {"$set": {
            "status": status,
            "parsed": ocr_result,
            "raw_text": ocr_result.get("raw_text", ""),
            "error_message": ocr_result.get("error") if not ocr_result["success"] else None,
        }},
    )

    return {
        "job_id": job_id,
        "status": status,
        "parsed": ocr_result,
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    job = await db.ocr_jobs.find_one(
        {"_id": ObjectId(job_id), "user_id": ObjectId(current_user["id"])}
    )
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": str(job["_id"]),
        "status": job["status"],
        "parsed": job.get("parsed"),
        "error_message": job.get("error_message"),
        "created_at": job["created_at"],
    }
