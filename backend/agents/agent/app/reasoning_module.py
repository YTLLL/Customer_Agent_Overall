"""推理模块入口

这个模块提供了推理代理的入口点，将推理代理与其他模块解耦，便于后期项目合并。
"""

from typing import Dict, Any, Optional
import logging

from agent.app.agents.reasoning_graph import ReasoningGraph
from agent.app.models.conversation import Conversation, Message

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ReasoningModule:
    """推理模块类，作为推理代理的统一入口"""
    
    def __init__(self):
        """初始化推理模块"""
        logger.info("初始化推理模块")
        self.reasoning_graph = ReasoningGraph()
    
    async def process_message(self, conversation: Conversation, message: str) -> Dict[str, Any]:
        """处理用户消息
        
        Args:
            conversation: 对话对象
            message: 用户消息
            
        Returns:
            Dict[str, Any]: 包含处理结果的字典
        """
        try:
            logger.info(f"处理用户消息: {message[:50]}...")
            
            # 使用推理图处理请求
            response = await self.reasoning_graph.process_request(conversation, message)
            
            # 返回处理结果
            return {
                "status": "success",
                "response": response,
                "conversation_id": conversation.id
            }
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "conversation_id": conversation.id
            }
    
    async def check_goal_achieved(self, conversation: Conversation) -> bool:
        """检查对话目标是否达成
        
        Args:
            conversation: 对话对象
            
        Returns:
            bool: 目标是否达成
        """
        # 初始化状态
        initial_state = {
            "conversation": conversation,
            "user_message": "",  # 不需要用户消息
            "hotel_name": None,
            "hotel_info": None,
            "response": None,
            "goal_achieved": False,
            "error": None
        }
        
        try:
            # 运行推理图的目标检查节点
            final_state = await self.reasoning_graph.graph.ainvoke(
                initial_state,
                {'node_type': 'check_goal'}
            )
            
            return final_state.get("goal_achieved", False)
        except Exception as e:
            logger.error(f"检查目标时出错: {str(e)}")
            return False

# 创建模块实例
reasoning_module = ReasoningModule()

# 导出接口函数
async def process_user_message(conversation: Conversation, message: str) -> Dict[str, Any]:
    """处理用户消息的接口函数
    
    这个函数作为模块的公共API，供其他模块调用
    
    Args:
        conversation: 对话对象
        message: 用户消息
        
    Returns:
        Dict[str, Any]: 包含处理结果的字典
    """
    return await reasoning_module.process_message(conversation, message)

async def is_goal_achieved(conversation: Conversation) -> bool:
    """检查目标是否达成的接口函数
    
    Args:
        conversation: 对话对象
        
    Returns:
        bool: 目标是否达成
    """
    return await reasoning_module.check_goal_achieved(conversation)