"""图像处理服务模块

这个模块负责处理上传的图片，使用通义千问API识别图片中的文本，并提取关键信息。
"""

import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

# 导入图像处理库
try:
    from PIL import Image
except ImportError:
    logging.warning("图像处理依赖库未安装，请安装pillow")

# 导入通义千问图像理解服务
from agent.app.services.qwen_vision_service import QwenVisionService

class ImageService:
    """图像处理服务类，负责从图片中提取文本和结构化信息"""
    
    def __init__(self):
        """初始化图像处理服务"""
        # 初始化通义千问图像理解服务
        self.qwen_service = QwenVisionService()
    
    async def process_image(self, image_path: str, image_type: str = "auto") -> Dict[str, Any]:
        """处理图像并提取结构化信息
        
        Args:
            image_path: 图像文件路径
            image_type: 图像类型，可以是'hotel', 'flight'或'auto'(自动检测)
            
        Returns:
            包含提取信息的字典
        """
        try:
            # 使用通义千问API提取结构化信息
            extracted_info = await self.qwen_service.extract_structured_info(image_path, image_type)
            # 添加图像类型信息
            extracted_info["detected_type"] = image_type
            return extracted_info
        except Exception as e:
            logging.error(f"通义千问API处理失败: {e}")
            return {"error": f"图像处理失败: {e}"}
        
        return extracted_info
    
    # 已移除本地图像预处理方法，完全依赖通义千问API进行图像分析
    
    def _detect_image_type(self, text: str) -> str:
        """根据文本内容自动检测图像类型"""
        # 酒店关键词
        hotel_keywords = [
            "hotel", "酒店", "check-in", "check-out", "reservation", "booking", 
            "room", "房间", "入住", "退房", "预订", "住宿", "accommodation"
        ]
        
        # 机票关键词
        flight_keywords = [
            "flight", "航班", "airline", "航空", "ticket", "机票", "departure", 
            "arrival", "boarding", "passenger", "旅客", "airport", "机场", 
            "seat", "座位", "baggage", "行李"
        ]
        
        # 计算关键词匹配数
        hotel_count = sum(1 for keyword in hotel_keywords if keyword.lower() in text.lower())
        flight_count = sum(1 for keyword in flight_keywords if keyword.lower() in text.lower())
        
        # 根据匹配数确定类型
        if hotel_count > flight_count:
            return "hotel"
        elif flight_count > hotel_count:
            return "flight"
        else:
            # 如果无法确定，返回通用类型
            return "general"
    
    def _extract_hotel_info(self, text: str) -> Dict[str, Any]:
        """从酒店相关图像中提取信息"""
        info = {
            "personal": {
                "name": None,
                "email": None,
                "phone": None,
                "dob": None,
                "membership_number": None,
                "preferences": []
            },
            "hotel": {
                "name": None,
                "confirmation_number": None,
                "booking_date": None,
                "stay_period": None,
                "membership_number": None,
                "price": None,
                "check_in_time": None,
                "check_out_time": None,
                "guests": {
                    "adults": None,
                    "children": None
                },
                "room_type": None,
                "rooms_booked": None,
                "address": None,
                "invoice_number": None,
                "additional_services": []
            }
        }
        
        # 提取酒店名称
        hotel_name_patterns = [
            r"(?i)hotel[:\s]+([\w\s]+)",
            r"(?i)酒店[：:\s]+([\w\s]+)",
            r"(?i)([\w\s]+)\s+hotel",
            r"(?i)([\w\s]+)\s+酒店"
        ]
        for pattern in hotel_name_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["name"] = match.group(1).strip()
                break
        
        # 提取确认号
        confirmation_patterns = [
            r"(?i)confirmation[\s#:]+([\w\d-]+)",
            r"(?i)confirmation number[\s#:]+([\w\d-]+)",
            r"(?i)booking[\s#:]+([\w\d-]+)",
            r"(?i)reservation[\s#:]+([\w\d-]+)",
            r"(?i)订单号[\s#：:]+([\w\d-]+)",
            r"(?i)预订号[\s#：:]+([\w\d-]+)"
        ]
        for pattern in confirmation_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["confirmation_number"] = match.group(1).strip()
                break
        
        # 提取预订日期
        booking_date_patterns = [
            r"(?i)booking date[\s:]+([\d/\.-]+)",
            r"(?i)date of booking[\s:]+([\d/\.-]+)",
            r"(?i)预订日期[\s：:]+([\d/\.-]+)",
            r"(?i)下单日期[\s：:]+([\d/\.-]+)"
        ]
        for pattern in booking_date_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["booking_date"] = match.group(1).strip()
                break
        
        # 提取入住时间段
        stay_period_patterns = [
            r"(?i)stay(?:\s+period)?[\s:]+([\d/\.-]+)\s*(?:to|-|–|~)\s*([\d/\.-]+)",
            r"(?i)check-in[\s:]+([\d/\.-]+)\s+check-out[\s:]+([\d/\.-]+)",
            r"(?i)arrival[\s:]+([\d/\.-]+)\s+departure[\s:]+([\d/\.-]+)",
            r"(?i)入住[\s：:]+([\d/\.-]+)\s+退房[\s：:]+([\d/\.-]+)"
        ]
        for pattern in stay_period_patterns:
            match = re.search(pattern, text)
            if match:
                check_in = match.group(1).strip()
                check_out = match.group(2).strip()
                info["hotel"]["stay_period"] = f"{check_in} to {check_out}"
                info["hotel"]["check_in_time"] = check_in
                info["hotel"]["check_out_time"] = check_out
                break
        
        # 提取会员号
        membership_patterns = [
            r"(?i)membership[\s#:]+([\w\d-]+)",
            r"(?i)member[\s#:]+([\w\d-]+)",
            r"(?i)会员[\s#：:]+([\w\d-]+)",
            r"(?i)会员号[\s#：:]+([\w\d-]+)"
        ]
        for pattern in membership_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["membership_number"] = match.group(1).strip()
                info["personal"]["membership_number"] = match.group(1).strip()
                break
        
        # 提取价格
        price_patterns = [
            r"(?i)price[\s:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)total[\s:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)amount[\s:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)价格[\s：:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)总价[\s：:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)金额[\s：:]*[$€£¥]?\s*(\d+[\d,.]*)"
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["price"] = match.group(1).strip()
                break
        
        # 提取房间类型
        room_type_patterns = [
            r"(?i)room type[\s:]+([\w\s]+)",
            r"(?i)room[\s:]+([\w\s]+)",
            r"(?i)房型[\s：:]+([\w\s]+)",
            r"(?i)房间类型[\s：:]+([\w\s]+)"
        ]
        for pattern in room_type_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["room_type"] = match.group(1).strip()
                break
        
        # 提取地址
        address_patterns = [
            r"(?i)address[\s:]+([\w\s,.-]+)",
            r"(?i)location[\s:]+([\w\s,.-]+)",
            r"(?i)地址[\s：:]+([\w\s,.-]+)",
            r"(?i)位置[\s：:]+([\w\s,.-]+)"
        ]
        for pattern in address_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["address"] = match.group(1).strip()
                break
        
        # 提取发票号
        invoice_patterns = [
            r"(?i)invoice[\s#:]+([\w\d-]+)",
            r"(?i)receipt[\s#:]+([\w\d-]+)",
            r"(?i)发票[\s#：:]+([\w\d-]+)",
            r"(?i)收据[\s#：:]+([\w\d-]+)"
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text)
            if match:
                info["hotel"]["invoice_number"] = match.group(1).strip()
                break
        
        # 提取个人信息
        # 姓名
        name_patterns = [
            r"(?i)name[\s:]+([\w\s]+)",
            r"(?i)guest[\s:]+([\w\s]+)",
            r"(?i)姓名[\s：:]+([\w\s]+)",
            r"(?i)客人[\s：:]+([\w\s]+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                info["personal"]["name"] = match.group(1).strip()
                break
        
        # 邮箱
        email_pattern = r'[\w\.-]+@[\w\.-]+\.[\w]+'  
        email_match = re.search(email_pattern, text)
        if email_match:
            info["personal"]["email"] = email_match.group(0)
        
        # 电话
        phone_patterns = [
            r"(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",  # 国际格式
            r"\d{3}[\s.-]?\d{3,4}[\s.-]?\d{4}",  # 国内格式
            r"\+\d{1,3}[\s-]?\d{6,14}"  # 简化国际格式
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                info["personal"]["phone"] = phone_match.group(0)
                break
        
        # 使用NLP进一步提取和验证信息
        if self.nlp:
            self._enhance_extraction_with_nlp(text, info)
        
        return info
    
    def _extract_flight_info(self, text: str) -> Dict[str, Any]:
        """从机票相关图像中提取信息"""
        info = {
            "personal": {
                "name": None,
                "email": None,
                "phone": None,
                "dob": None,
                "membership_number": None,
                "preferences": []
            },
            "flight": {
                "name": None,
                "confirmation_number": None,
                "ticket_number": None,
                "booking_date": None,
                "membership_number": None,
                "airline": None,
                "flight_number": None,
                "depart_time": None,
                "arrival_time": None,
                "baggage_allowance": None,
                "price": None,
                "invoice_number": None,
                "depart_airport": {
                    "code": None,
                    "name": None,
                    "address": None
                },
                "arrival_airport": {
                    "code": None,
                    "name": None,
                    "address": None
                },
                "additional_services": []
            }
        }
        
        # 提取航空公司
        airline_patterns = [
            r"(?i)airline[\s:]+([\w\s]+)",
            r"(?i)carrier[\s:]+([\w\s]+)",
            r"(?i)航空公司[\s：:]+([\w\s]+)",
            r"(?i)航司[\s：:]+([\w\s]+)"
        ]
        for pattern in airline_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["airline"] = match.group(1).strip()
                break
        
        # 提取订单号/确认号
        confirmation_patterns = [
            r"(?i)confirmation[\s#:]+([\w\d-]+)",
            r"(?i)confirmation number[\s#:]+([\w\d-]+)",
            r"(?i)booking[\s#:]+([\w\d-]+)",
            r"(?i)reservation[\s#:]+([\w\d-]+)",
            r"(?i)订单号[\s#：:]+([\w\d-]+)",
            r"(?i)预订号[\s#：:]+([\w\d-]+)"
        ]
        for pattern in confirmation_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["confirmation_number"] = match.group(1).strip()
                break
        
        # 提取票号
        ticket_patterns = [
            r"(?i)ticket[\s#:]+([\w\d-]+)",
            r"(?i)ticket number[\s#:]+([\w\d-]+)",
            r"(?i)e-ticket[\s#:]+([\w\d-]+)",
            r"(?i)机票号[\s#：:]+([\w\d-]+)",
            r"(?i)票号[\s#：:]+([\w\d-]+)"
        ]
        for pattern in ticket_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["ticket_number"] = match.group(1).strip()
                break
        
        # 提取预订日期
        booking_date_patterns = [
            r"(?i)booking date[\s:]+([\d/\.-]+)",
            r"(?i)date of booking[\s:]+([\d/\.-]+)",
            r"(?i)预订日期[\s：:]+([\d/\.-]+)",
            r"(?i)下单日期[\s：:]+([\d/\.-]+)"
        ]
        for pattern in booking_date_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["booking_date"] = match.group(1).strip()
                break
        
        # 提取会员号
        membership_patterns = [
            r"(?i)membership[\s#:]+([\w\d-]+)",
            r"(?i)member[\s#:]+([\w\d-]+)",
            r"(?i)frequent flyer[\s#:]+([\w\d-]+)",
            r"(?i)会员[\s#：:]+([\w\d-]+)",
            r"(?i)会员号[\s#：:]+([\w\d-]+)",
            r"(?i)常旅客[\s#：:]+([\w\d-]+)"
        ]
        for pattern in membership_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["membership_number"] = match.group(1).strip()
                info["personal"]["membership_number"] = match.group(1).strip()
                break
        
        # 提取航班号
        flight_number_patterns = [
            r"(?i)flight[\s#:]+([\w\d-]+)",
            r"(?i)flight number[\s#:]+([\w\d-]+)",
            r"(?i)航班[\s#：:]+([\w\d-]+)",
            r"(?i)航班号[\s#：:]+([\w\d-]+)"
        ]
        for pattern in flight_number_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["flight_number"] = match.group(1).strip()
                break
        
        # 提取起飞时间
        depart_time_patterns = [
            r"(?i)departure[\s:]+([\d/\.-]+\s*[\d:]+\s*[APap][Mm]?)",
            r"(?i)depart[\s:]+([\d/\.-]+\s*[\d:]+\s*[APap][Mm]?)",
            r"(?i)起飞[\s：:]+([\d/\.-]+\s*[\d:]+)",
            r"(?i)出发[\s：:]+([\d/\.-]+\s*[\d:]+)"
        ]
        for pattern in depart_time_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["depart_time"] = match.group(1).strip()
                break
        
        # 提取到达时间
        arrival_time_patterns = [
            r"(?i)arrival[\s:]+([\d/\.-]+\s*[\d:]+\s*[APap][Mm]?)",
            r"(?i)arrive[\s:]+([\d/\.-]+\s*[\d:]+\s*[APap][Mm]?)",
            r"(?i)到达[\s：:]+([\d/\.-]+\s*[\d:]+)",
            r"(?i)落地[\s：:]+([\d/\.-]+\s*[\d:]+)"
        ]
        for pattern in arrival_time_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["arrival_time"] = match.group(1).strip()
                break
        
        # 提取行李额度
        baggage_patterns = [
            r"(?i)baggage[\s:]+([\d\w\s]+)",
            r"(?i)baggage allowance[\s:]+([\d\w\s]+)",
            r"(?i)checked bag[\s:]+([\d\w\s]+)",
            r"(?i)行李[\s：:]+([\d\w\s]+)",
            r"(?i)行李额[\s：:]+([\d\w\s]+)",
            r"(?i)托运行李[\s：:]+([\d\w\s]+)"
        ]
        for pattern in baggage_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["baggage_allowance"] = match.group(1).strip()
                break
        
        # 提取价格
        price_patterns = [
            r"(?i)price[\s:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)total[\s:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)amount[\s:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)价格[\s：:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)总价[\s：:]*[$€£¥]?\s*(\d+[\d,.]*)",
            r"(?i)金额[\s：:]*[$€£¥]?\s*(\d+[\d,.]*)"
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["price"] = match.group(1).strip()
                break
        
        # 提取发票号
        invoice_patterns = [
            r"(?i)invoice[\s#:]+([\w\d-]+)",
            r"(?i)receipt[\s#:]+([\w\d-]+)",
            r"(?i)发票[\s#：:]+([\w\d-]+)",
            r"(?i)收据[\s#：:]+([\w\d-]+)"
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["invoice_number"] = match.group(1).strip()
                break
        
        # 提取机场信息
        # 出发机场
        depart_airport_patterns = [
            r"(?i)from[\s:]+([\w\s]+)",
            r"(?i)departure airport[\s:]+([\w\s]+)",
            r"(?i)depart[\s:]+([\w\s]+)",
            r"(?i)出发机场[\s：:]+([\w\s]+)",
            r"(?i)始发地[\s：:]+([\w\s]+)"
        ]
        for pattern in depart_airport_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["depart_airport"]["name"] = match.group(1).strip()
                break
        
        # 提取机场代码
        airport_code_pattern = r'\b([A-Z]{3})\b'
        airport_codes = re.findall(airport_code_pattern, text)
        if len(airport_codes) >= 2:
            info["flight"]["depart_airport"]["code"] = airport_codes[0]
            info["flight"]["arrival_airport"]["code"] = airport_codes[1]
        
        # 到达机场
        arrival_airport_patterns = [
            r"(?i)to[\s:]+([\w\s]+)",
            r"(?i)arrival airport[\s:]+([\w\s]+)",
            r"(?i)arrive[\s:]+([\w\s]+)",
            r"(?i)到达机场[\s：:]+([\w\s]+)",
            r"(?i)目的地[\s：:]+([\w\s]+)"
        ]
        for pattern in arrival_airport_patterns:
            match = re.search(pattern, text)
            if match:
                info["flight"]["arrival_airport"]["name"] = match.group(1).strip()
                break
        
        # 提取个人信息
        # 姓名
        name_patterns = [
            r"(?i)passenger[\s:]+([\w\s]+)",
            r"(?i)name[\s:]+([\w\s]+)",
            r"(?i)旅客[\s：:]+([\w\s]+)",
            r"(?i)姓名[\s：:]+([\w\s]+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                info["personal"]["name"] = match.group(1).strip()
                info["flight"]["name"] = match.group(1).strip()
                break
        
        # 邮箱
        email_pattern = r'[\w\.-]+@[\w\.-]+\.[\w]+'
        email_match = re.search(email_pattern, text)
        if email_match:
            info["personal"]["email"] = email_match.group(0)
        
        # 电话
        phone_patterns = [
            r"(?:\+\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}"]  # 国际格式