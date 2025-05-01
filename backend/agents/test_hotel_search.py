#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试高德MCP服务的酒店搜索功能

该脚本测试高德MCP服务能否正确搜索酒店信息。
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入高德MCP服务
from agent.app.services.gaode_mcp_service import gaode_mcp_service

# 加载环境变量
load_dotenv()


async def test_hotel_search():
    """测试酒店搜索功能"""
    print("=== 测试高德MCP服务酒店搜索功能 ===\n")
    
    # 测试用的酒店名称列表
    hotel_names = [
        "广州汉庭酒店",
        "北京希尔顿酒店",
        "上海浦东丽思卡尔顿酒店",
        "深圳福田香格里拉酒店"
    ]
    
    for hotel_name in hotel_names:
        print(f"\n正在搜索酒店: {hotel_name}")
        try:
            # 调用高德MCP服务搜索酒店
            hotel_info = await gaode_mcp_service.search_hotel(hotel_name)
            
            # 打印搜索结果
            if hotel_info:
                if hotel_info.get("multiple_options"):
                    print(f"找到多个匹配的酒店选项:")
                    for i, hotel in enumerate(hotel_info["hotels"]):
                        print(f"  {i+1}. {hotel['name']} - {hotel.get('district', '')} {hotel.get('formatted_address', '')}")
                else:
                    print(f"成功获取酒店信息:")
                    print(f"  名称: {hotel_info.get('name', '未知')}")
                    print(f"  地址: {hotel_info.get('formatted_address', '未知')}")
                    print(f"  电话: {hotel_info.get('tel', '未知')}")
                    if 'policies' in hotel_info:
                        print("  酒店政策:")
                        policies = hotel_info['policies']
                        print(f"    入住时间: {policies.get('check_in', '未知')}")
                        print(f"    退房时间: {policies.get('check_out', '未知')}")
                        print(f"    取消政策: {policies.get('cancellation', '未知')}")
                        print(f"    退款政策: {policies.get('refund', '未知')}")
            else:
                print("未能获取酒店信息，返回为空")
        except Exception as e:
            print(f"搜索酒店时出错: {str(e)}")


async def test_refund_request():
    """测试退款请求分析功能"""
    print("\n=== 测试高德MCP服务退款请求分析功能 ===\n")
    
    # 测试用的退款请求消息
    refund_messages = [
        "我要退款，订单号HT12345，入住日期是2025-05-01，客人是张三，酒店是北京希尔顿酒店",
        "我想取消预订，广州汉庭酒店，订单号GZ98765",
        "帮我退一下订单，上海浦东丽思卡尔顿酒店的，订单号是SH54321，预订人李四，入住时间5月10日"
    ]
    
    for message in refund_messages:
        print(f"\n分析退款请求: {message}")
        try:
            # 调用高德MCP服务分析退款请求
            result = await gaode_mcp_service.analyze_refund_request(message)
            
            # 打印分析结果
            if result:
                print(f"分析结果:")
                print(f"  是否完整: {result.get('is_complete', False)}")
                
                if 'extracted_info' in result:
                    info = result['extracted_info']
                    print("  提取的信息:")
                    print(f"    酒店名称: {info.get('hotel_name', '未提供')}")
                    print(f"    订单号: {info.get('order_id', '未提供')}")
                    print(f"    入住日期: {info.get('check_in_date', '未提供')}")
                    print(f"    客人姓名: {info.get('guest_name', '未提供')}")
                
                if 'missing_fields' in result and result['missing_fields']:
                    print("  缺失的字段:")
                    for field in result['missing_fields']:
                        print(f"    - {field}")
                else:
                    print("  没有缺失的字段")
                    
                if 'hotel_info' in result and result['hotel_info']:
                    hotel_info = result['hotel_info']
                    print("  酒店信息:")
                    print(f"    名称: {hotel_info.get('name', '未知')}")
                    print(f"    地址: {hotel_info.get('formatted_address', '未知')}")
                    print(f"    电话: {hotel_info.get('tel', '未知')}")
            else:
                print("分析结果为空")
        except Exception as e:
            print(f"分析退款请求时出错: {str(e)}")


async def main():
    """主函数"""
    # 测试酒店搜索功能
    await test_hotel_search()
    
    # 测试退款请求分析功能
    await test_refund_request()


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
