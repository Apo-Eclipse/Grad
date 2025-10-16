# main.py

import os
import base64
from dotenv import load_dotenv
from agent import FinancialAgent

def main():
    """
    Main execution block for the financial transaction agent.
    """
    load_dotenv()
    
    # Create a single, unified agent
    agent = FinancialAgent()

    print("Financial Transaction Agent (powered by Azure OpenAI) is ready!")
    print("You can provide a text description, a path to a receipt image, or a path to an audio file.")
    print("Type 'exit' to quit.\n")

    # --- Text Input ---
    print("\n--- Testing with TEXT input ---")
    text_input = "I just paid $25.99 for a pizza at Domino's"
    response = agent.invoke({"text": text_input})
    print("\nAgent's final response:", response)

    # --- Image Input ---
    print("\n--- Testing with IMAGE input ---")
    image_path = "receipt.png" 
    if os.path.exists(image_path):
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
        response = agent.invoke({"image_data": image_data})
        print("\nAgent's final response:", response)
    else:
        print(f"Skipping image test: Please create a file named '{image_path}' in your project folder.")

    # --- Audio Input ---
    print("\n--- Testing with AUDIO input ---")
    audio_path = "transaction.wav" 
    if os.path.exists(audio_path):
        response = agent.invoke({"audio_path": audio_path})
        print("\nAgent's final response:", response['output'])
    else:
        print(f"Skipping audio test: Please create a file named '{audio_path}' in your project folder.")

if __name__ == "__main__":
    main()
