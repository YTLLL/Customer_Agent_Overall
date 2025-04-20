"""图像分析模型模块

这个模块定义了与图像分析相关的数据模型。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

class PersonalInfo(BaseModel):
    """个人信息模型"""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    membership_number: Optional[str] = None
    preferences: List[str] = Field(default_factory=list)

class AirportInfo(BaseModel):
    """机场信息模型"""
    code: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None

class FlightInfo(BaseModel):
    """机票信息模型"""
    name: Optional[str] = None
    confirmation_number: Optional[str] = None
    ticket_number: Optional[str] = None
    booking_date: Optional[str] = None
    membership_number: Optional[str] = None
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    depart_time: Optional[str] = None
    arrival_time: Optional[str] = None
    baggage_allowance: Optional[str] = None
    price: Optional[str] = None
    invoice_number: Optional[str] = None
    depart_airport: AirportInfo = Field(default_factory=AirportInfo)
    arrival_airport: AirportInfo = Field(default_factory=AirportInfo)
    additional_services: List[str] = Field(default_factory=list)

class GuestInfo(BaseModel):
    """客人信息模型"""
    adults: Optional[int] = None
    children: Optional[int] = None

class HotelInfo(BaseModel):
    """酒店信息模型"""
    name: Optional[str] = None
    confirmation_number: Optional[str] = None
    booking_date: Optional[str] = None
    stay_period: Optional[str] = None
    membership_number: Optional[str] = None
    price: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    guests: GuestInfo = Field(default_factory=GuestInfo)
    room_type: Optional[str] = None
    rooms_booked: Optional[int] = None
    address: Optional[str] = None
    invoice_number: Optional[str] = None
    additional_services: List[str] = Field(default_factory=list)

class ImageAnalysis(BaseModel):
    """图像分析结果模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_filename: str
    image_path: str
    detected_type: str
    raw_text: Optional[str] = None
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    hotel: Optional[HotelInfo] = None
    flight: Optional[FlightInfo] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class ImageAnalysisSummary(BaseModel):
    """图像分析汇总模型"""
    total_images: int
    types: Dict[str, int]
    personal_info: Dict[str, Any]
    hotel_info: Dict[str, Any]
    flight_info: Dict[str, Any]