from dotenv import load_dotenv

load_dotenv()

from .agents.supervisor_agent import supervisor_agent

root_agent = supervisor_agent