from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, task, crew
from crewai_tools import FileReadTool, FileWriterTool
from dotenv import load_dotenv
import os

# Load environment variables (API keys, credentials, etc.)
_ = load_dotenv()

# Initialize the LLM
llm = LLM(
    model="gemini/gemini-2.5-flash",
    temperature=0.5,
)

# Ensure output directory exists
OUTPUT_DIR = "output_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# summarized file name 
file_name = input('enter the file name : ')
file_name = f'{file_name}.txt'

# file path 
file_path = input("enter the file path : ")
# -------------------------------------------------------------------
# Define CrewBase
# -------------------------------------------------------------------
@CrewBase
class KnowledgeBaseCrew:
    """
    Crew that reads a text file, summarizes it, and rewrites it in Markdown format.
    """

    # Config files for agents and tasks
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # -------------------------------------------------------------------
    # Agent Definition
    # -------------------------------------------------------------------
    @agent
    def knowledge_base_creator(self) -> Agent:
        """
        Agent that reads the file and summarizes content into markdown.
        """
        file_read_tool = FileReadTool(file_path=file_path)
        file_writer_tool = FileWriterTool()

        return Agent(
            config=self.agents_config["knowledge_base_creator"],  # type: ignore[index]
            tools=[file_read_tool, file_writer_tool],
            llm=llm,
            verbose=True,
        )
    # -------------------------------------------------------------------
    # Task Definition
    # -------------------------------------------------------------------
    @task
    def summarize_content(self) -> Task:
        """
        Task to summarize the file content into a markdown knowledge entry.
        """
        return Task(
            config=self.tasks_config["generate_knowledge_entry"],  # type: ignore[index]
            agent=self.knowledge_base_creator(),
            markdown=True,              # Ensures output is treated as markdown
            output_file=os.path.join(OUTPUT_DIR, file_name)  # Save directly
        )

    # -------------------------------------------------------------------
    # Crew Definition
    # -------------------------------------------------------------------
    @crew
    def knowledgecrew(self) -> Crew:
        """
        Creates the Knowledge Base Crew that executes the summarization task.
        """
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            planning_llm=llm,  # Optional: can help plan task execution
        )


# -------------------------------------------------------------------
# Run the Crew
# -------------------------------------------------------------------
if __name__ == "__main__":
    crew = KnowledgeBaseCrew()
    result = crew.knowledgecrew().kickoff()

    print("\n✅ Knowledge Base Markdown Summary Created Successfully!")
    print(f"📄 File saved at: {os.path.join(OUTPUT_DIR)}, {file_name}")

