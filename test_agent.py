import sys
import os

# Ensure Teni directory is in path
sys.path.append("/Users/aanshgoel/Teni")

from planning.agent import Agent
from llm.client import LLMClient
from execution import ExecutionEngine
from utils.logger import TeniLogger
from security.permission_layer import PermissionLayer

def main():
    print("Initializing components for Agent Test...")
    llm_client = LLMClient()
    executor = ExecutionEngine()
    logger = TeniLogger()
    permission_layer = PermissionLayer()
    
    # Auto-approve for testing purposes to prevent hanging on input()
    permission_layer.requires_confirmation = lambda action, params: False

    agent = Agent(llm_client, executor, logger, permission_layer)
    
    goal = "Create a directory named 'agent_test_dir' inside /Users/aanshgoel/Teni"
    print(f"Starting test with goal: {goal}\n")
    
    agent.run(goal)

if __name__ == "__main__":
    main()
