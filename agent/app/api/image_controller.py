"""图像识别控制器模块

这个模块提供了处理上传图片并提取结构化信息的API端点。
"""

import os
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from pydantic import BaseModel

from agent.app.services.image_service import ImageService
from agent.app.services.db_service import DBService

# 创建路由器
router = APIRouter(prefix="/api/images", tags=["images"])

# 依赖注入
def get_image_service():
    return ImageService()

def get_db_service():
    return DBService()

# 模型定义
class ImageAnalysisResponse(BaseModel):
    """图像分析响应模型"""
    image_id: str
    detected_type: str
    extracted_info: Dict[str, Any]
    raw_text: Optional[str] = None

class ImageBatchAnalysisResponse(BaseModel):
    """批量图像分析响应模型"""
    results: List[ImageAnalysisResponse]
    summary: Dict[str, Any]

# 上传目录配置
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    image: UploadFile = File(...),
    image_type: str = Form("auto"),
    image_service: ImageService = Depends(get_image_service),
    db_service: DBService = Depends(get_db_service)
):
    """分析单张图片并提取结构化信息"""
    # 生成唯一文件名
    image_id = str(uuid.uuid4())
    file_extension = os.path.splitext(image.filename)[1]
    image_path = os.path.join(UPLOAD_DIR, f"{image_id}{file_extension}")
    
    try:
        # 保存上传的图片
        with open(image_path, "wb") as f:
            content = await image.read()
            f.write(content)
        
        # 处理图片并提取信息
        extracted_info = await image_service.process_image(image_path, image_type)
        
        # 保存分析结果到数据库
        analysis_result = {
            "image_id": image_id,
            "original_filename": image.filename,
            "image_path": image_path,
            "detected_type": extracted_info.get("detected_type", "unknown"),
            "extracted_info": extracted_info
        }
        
        # 这里可以添加保存到数据库的代码
        # db_service.save_image_analysis(analysis_result)
        
        # 构建响应
        response = ImageAnalysisResponse(
            image_id=image_id,
            detected_type=extracted_info.get("detected_type", "unknown"),
            extracted_info=extracted_info,
            raw_text=extracted_info.get("raw_text")
        )
        
        return response
        
    except Exception as e:
        # 删除临时文件
        if os.path.exists(image_path):
            os.remove(image_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理图片时出错: {str(e)}"
        )

@router.post("/analyze-batch", response_model=ImageBatchAnalysisResponse)
async def analyze_images_batch(
    images: List[UploadFile] = File(...),
    image_type: str = Form("auto"),
    image_service: ImageService = Depends(get_image_service),
    db_service: DBService = Depends(get_db_service)
):
    """批量分析多张图片并提取结构化信息"""
    results = []
    image_paths = []
    
    try:
        # 处理每张图片
        for image in images:
            # 生成唯一文件名
            image_id = str(uuid.uuid4())
            file_extension = os.path.splitext(image.filename)[1]
            image_path = os.path.join(UPLOAD_DIR, f"{image_id}{file_extension}")
            image_paths.append(image_path)
            
            # 保存上传的图片
            with open(image_path, "wb") as f:
                content = await image.read()
                f.write(content)
            
            # 处理图片并提取信息
            extracted_info = await image_service.process_image(image_path, image_type)
            
            # 保存分析结果到数据库
            analysis_result = {
                "image_id": image_id,
                "original_filename": image.filename,
                "image_path": image_path,
                "detected_type": extracted_info.get("detected_type", "unknown"),
                "extracted_info": extracted_info
            }
            
            # 这里可以添加保存到数据库的代码
            # db_service.save_image_analysis(analysis_result)
            
            # 添加到结果列表
            results.append(ImageAnalysisResponse(
                image_id=image_id,
                detected_type=extracted_info.get("detected_type", "unknown"),
                extracted_info=extracted_info,
                raw_text=extracted_info.get("raw_text")
            ))
        
        # 生成汇总信息
        summary = _generate_summary(results)
        
        return ImageBatchAnalysisResponse(
            results=results,
            summary=summary
        )
        
    except Exception as e:
        # 删除临时文件
        for path in image_paths:
            if os.path.exists(path):
                os.remove(path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量处理图片时出错: {str(e)}"
        )

def _generate_summary(results: List[ImageAnalysisResponse]) -> Dict[str, Any]:
    """生成批量分析的汇总信息"""
    summary = {
        "total_images": len(results),
        "types": {},
        "personal_info": {},
        "hotel_info": {},
        "flight_info": {}
    }
    
    # 统计图片类型
    for result in results:
        detected_type = result.detected_type
        if detected_type in summary["types"]:
            summary["types"][detected_type] += 1
        else:
            summary["types"][detected_type] = 1
    
    # 合并个人信息
    for result in results:
        info = result.extracted_info
        
        # 合并个人信息
        if "personal" in info and info["personal"]:
            for key, value in info["personal"].items():
                if value and (key not in summary["personal_info"] or not summary["personal_info"][key]):
                    summary["personal_info"][key] = value
        
        # 合并酒店信息
        if "hotel" in info and info["hotel"] and result.detected_type == "hotel":
            for key, value in info["hotel"].items():
                if value and (key not in summary["hotel_info"] or not summary["hotel_info"][key]):
                    summary["hotel_info"][key] = value
        
        # 合并机票信息
        if "flight" in info and info["flight"] and result.detected_type == "flight":
            for key, value in info["flight"].items():
                if value and (key not in summary["flight_info"] or not summary["flight_info"][key]):
                    summary["flight_info"][key] = value
    
    return summary

@router.get("/{image_id}", response_model=ImageAnalysisResponse)
async def get_image_analysis(
    image_id: str,
    db_service: DBService = Depends(get_db_service)
):
    """获取指定图片的分析结果"""
    # 从数据库获取分析结果
    # analysis_result = db_service.get_image_analysis(image_id)
    
    # 模拟数据库查询
    analysis_result = None
    
    if not analysis_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到图片ID为 {image_id} 的分析结果"
        )
    
    return ImageAnalysisResponse(
        image_id=analysis_result["image_id"],
        detected_type=analysis_result["detected_type"],
        extracted_info=analysis_result["extracted_info"],
        raw_text=analysis_result["extracted_info"].get("raw_text")
    )